"""
AI调用日志记录服务
自动记录每次LLM调用，支持用量统计和日志查询
"""
import uuid
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from app.core.database import get_db_cursor, get_db


class AIUsageTracker:
    """AI调用追踪器"""

    @staticmethod
    def log_call(
        purpose: str,
        provider: str,
        model: str,
        operation: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        status: str = "success",
        error_message: Optional[str] = None,
        request_content: Optional[str] = None,
        response_content: Optional[str] = None,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """记录单次AI调用"""
        log_id = str(uuid.uuid4())

        # 截断内容（只保留前500字符）
        request_preview = None
        response_preview = None
        if request_content:
            request_preview = request_content[:500] if len(request_content) > 500 else request_content
        if response_content:
            response_preview = response_content[:500] if len(response_content) > 500 else response_content

        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO ai_call_logs
                    (id, project_id, purpose, provider, model, operation,
                     input_tokens, output_tokens, total_tokens, latency_ms,
                     status, error_message, request_content, response_content,
                     user_id, session_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    [
                        log_id, project_id, purpose, provider, model, operation,
                        input_tokens, output_tokens, input_tokens + output_tokens,
                        latency_ms, status, error_message, request_preview, response_preview,
                        user_id, session_id
                    ]
                )
                get_db().commit()

            # 更新每日汇总
            AIUsageTracker._update_daily_summary(
                purpose, provider, model,
                input_tokens, output_tokens, latency_ms, status
            )
        except Exception as e:
            # 日志记录失败不应影响主流程
            print(f"AI usage tracking error: {e}")

        return log_id

    @staticmethod
    def _update_daily_summary(
        purpose: str, provider: str, model: str,
        input_tokens: int, output_tokens: int, latency_ms: float, status: str
    ):
        """更新每日用量汇总"""
        today = datetime.now().strftime("%Y-%m-%d")
        summary_id = f"{today}_{provider}_{purpose}_{model}"

        try:
            with get_db_cursor() as cursor:
                # 检查是否已有记录
                cursor.execute(
                    """
                    SELECT id, total_calls, success_count, error_count,
                           total_input_tokens, total_output_tokens, total_latency_ms
                    FROM ai_usage_summary
                    WHERE period_type = 'daily' AND period_value = ? AND provider = ? AND purpose = ? AND model = ?
                    """,
                    [today, provider, purpose, model]
                )
                row = cursor.fetchone()

                if row:
                    # 更新现有记录
                    new_calls = row[1] + 1
                    new_success = row[2] + (1 if status == "success" else 0)
                    new_error = row[3] + (1 if status == "error" else 0)
                    new_input = row[4] + input_tokens
                    new_output = row[5] + output_tokens
                    new_latency = row[6] + latency_ms
                    avg_latency = new_latency / new_calls

                    cursor.execute(
                        """
                        UPDATE ai_usage_summary
                        SET total_calls = ?, success_count = ?, error_count = ?,
                            total_input_tokens = ?, total_output_tokens = ?, total_tokens = ?,
                            total_latency_ms = ?, avg_latency_ms = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        [new_calls, new_success, new_error, new_input, new_output,
                         new_input + new_output, new_latency, avg_latency, row[0]]
                    )
                else:
                    # 创建新记录
                    cursor.execute(
                        """
                        INSERT INTO ai_usage_summary
                        (id, period_type, period_value, provider, purpose, model,
                         total_calls, success_count, error_count,
                         total_input_tokens, total_output_tokens, total_tokens,
                         total_latency_ms, avg_latency_ms)
                        VALUES (?, 'daily', ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            summary_id, today, provider, purpose, model,
                            1 if status == "success" else 0,
                            1 if status == "error" else 0,
                            input_tokens, output_tokens, input_tokens + output_tokens,
                            latency_ms, latency_ms
                        ]
                    )

                get_db().commit()
        except Exception as e:
            print(f"AI usage summary update error: {e}")


@contextmanager
def track_ai_call(
    purpose: str,
    provider: str,
    model: str,
    operation: str,
    request_content: Optional[str] = None,
    project_id: Optional[str] = None
):
    """
    AI调用追踪上下文管理器

    用法：
        with track_ai_call("general", "qwen", "qwen3.5-plus", "chat", prompt) as tracker:
            response = await llm_service.chat(messages)
            tracker.set_response(response.content)
            tracker.set_tokens(response.usage)
    """
    start_time = time.time()
    tracker_data = {
        'purpose': purpose,
        'provider': provider,
        'model': model,
        'operation': operation,
        'request': request_content,
        'response': None,
        'input_tokens': 0,
        'output_tokens': 0,
        'status': 'success',
        'error': None,
        'project_id': project_id
    }

    class TrackerHelper:
        def set_response(self, content: str):
            tracker_data['response'] = content

        def set_tokens(self, usage: Dict):
            tracker_data['input_tokens'] = usage.get('input_tokens', usage.get('prompt_tokens', 0))
            tracker_data['output_tokens'] = usage.get('output_tokens', usage.get('completion_tokens', 0))

        def set_error(self, error: str):
            tracker_data['status'] = 'error'
            tracker_data['error'] = error

    tracker = TrackerHelper()

    try:
        yield tracker
    except Exception as e:
        tracker_data['status'] = 'error'
        tracker_data['error'] = str(e)
        raise
    finally:
        latency_ms = (time.time() - start_time) * 1000
        AIUsageTracker.log_call(
            purpose=tracker_data['purpose'],
            provider=tracker_data['provider'],
            model=tracker_data['model'],
            operation=tracker_data['operation'],
            input_tokens=tracker_data['input_tokens'],
            output_tokens=tracker_data['output_tokens'],
            latency_ms=latency_ms,
            status=tracker_data['status'],
            error_message=tracker_data['error'],
            request_content=tracker_data['request'],
            response_content=tracker_data['response'],
            project_id=tracker_data['project_id']
        )


class AIUsageQueryService:
    """AI用量查询服务"""

    @staticmethod
    def get_summary(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        provider: Optional[str] = None,
        purpose: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取用量统计汇总"""
        with get_db_cursor() as cursor:
            # 构建查询条件
            conditions = []
            params = []

            if start_date:
                conditions.append("created_at >= ?")
                params.append(start_date)
            if end_date:
                conditions.append("created_at <= ?")
                params.append(end_date)
            if provider:
                conditions.append("provider = ?")
                params.append(provider)
            if purpose:
                conditions.append("purpose = ?")
                params.append(purpose)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 总体统计
            cursor.execute(
                f"""
                SELECT
                    COUNT(*) as total_calls,
                    SUM(input_tokens) as total_input,
                    SUM(output_tokens) as total_output,
                    SUM(total_tokens) as total_tokens,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count,
                    AVG(latency_ms) as avg_latency
                FROM ai_call_logs
                WHERE {where_clause}
                """,
                params
            )
            row = cursor.fetchone()

            # 按供应商统计
            cursor.execute(
                f"""
                SELECT provider, COUNT(*) as count, SUM(total_tokens) as tokens
                FROM ai_call_logs
                WHERE {where_clause}
                GROUP BY provider
                """,
                params
            )
            by_provider = {row[0]: {'calls': row[1], 'tokens': row[2] or 0} for row in cursor.fetchall()}

            # 按用途统计
            cursor.execute(
                f"""
                SELECT purpose, COUNT(*) as count, SUM(total_tokens) as tokens
                FROM ai_call_logs
                WHERE {where_clause}
                GROUP BY purpose
                """,
                params
            )
            by_purpose = {row[0]: {'calls': row[1], 'tokens': row[2] or 0} for row in cursor.fetchall()}

            # 按模型统计
            cursor.execute(
                f"""
                SELECT model, COUNT(*) as count, SUM(total_tokens) as tokens
                FROM ai_call_logs
                WHERE {where_clause}
                GROUP BY model
                ORDER BY count DESC
                LIMIT 10
                """,
                params
            )
            by_model = [{'model': row[0], 'calls': row[1], 'tokens': row[2] or 0} for row in cursor.fetchall()]

            return {
                'total_calls': row[0] or 0,
                'total_input_tokens': row[1] or 0,
                'total_output_tokens': row[2] or 0,
                'total_tokens': row[3] or 0,
                'success_count': row[4] or 0,
                'error_count': row[5] or 0,
                'avg_latency_ms': round(row[6] or 0, 2),
                'by_provider': by_provider,
                'by_purpose': by_purpose,
                'by_model': by_model
            }

    @staticmethod
    def get_daily_usage(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: int = 30
    ) -> List[Dict]:
        """获取每日用量"""
        with get_db_cursor() as cursor:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")

            cursor.execute(
                """
                SELECT
                    period_value as date,
                    SUM(total_calls) as calls,
                    SUM(total_tokens) as tokens,
                    SUM(success_count) as success_count,
                    SUM(error_count) as error_count,
                    AVG(avg_latency_ms) as avg_latency
                FROM ai_usage_summary
                WHERE period_type = 'daily'
                AND period_value >= ?
                AND period_value <= ?
                GROUP BY period_value
                ORDER BY period_value
                """,
                [start_date, end_date]
            )

            return [
                {
                    'date': row[0],
                    'calls': row[1] or 0,
                    'tokens': row[2] or 0,
                    'success_count': row[3] or 0,
                    'error_count': row[4] or 0,
                    'avg_latency_ms': round(row[5] or 0, 2)
                }
                for row in cursor.fetchall()
            ]

    @staticmethod
    def get_logs(
        page: int = 1,
        page_size: int = 20,
        provider: Optional[str] = None,
        purpose: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict:
        """获取调用日志列表"""
        with get_db_cursor() as cursor:
            conditions = []
            params = []

            if provider:
                conditions.append("provider = ?")
                params.append(provider)
            if purpose:
                conditions.append("purpose = ?")
                params.append(purpose)
            if status:
                conditions.append("status = ?")
                params.append(status)
            if start_date:
                conditions.append("created_at >= ?")
                params.append(start_date)
            if end_date:
                conditions.append("created_at <= ?")
                params.append(end_date)
            if project_id:
                conditions.append("project_id = ?")
                params.append(project_id)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 获取总数
            cursor.execute(f"SELECT COUNT(*) FROM ai_call_logs WHERE {where_clause}", params)
            total = cursor.fetchone()[0]

            # 分页查询
            offset = (page - 1) * page_size
            cursor.execute(
                f"""
                SELECT id, project_id, purpose, provider, model, operation,
                       input_tokens, output_tokens, latency_ms, status,
                       error_message, request_content, response_content, created_at
                FROM ai_call_logs
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                params + [page_size, offset]
            )

            logs = [
                {
                    'id': row[0],
                    'project_id': row[1],
                    'purpose': row[2],
                    'provider': row[3],
                    'model': row[4],
                    'operation': row[5],
                    'input_tokens': row[6],
                    'output_tokens': row[7],
                    'latency_ms': round(row[8] or 0, 2),
                    'status': row[9],
                    'error_message': row[10],
                    'request_preview': row[11],
                    'response_preview': row[12],
                    'created_at': row[13]
                }
                for row in cursor.fetchall()
            ]

            return {
                'total': total,
                'page': page,
                'page_size': page_size,
                'logs': logs
            }

    @staticmethod
    def get_log_detail(log_id: str) -> Optional[Dict]:
        """获取单条日志详情"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, project_id, purpose, provider, model, operation,
                       input_tokens, output_tokens, total_tokens, latency_ms, status,
                       error_message, request_content, response_content, user_id, session_id, created_at
                FROM ai_call_logs
                WHERE id = ?
                """,
                [log_id]
            )
            row = cursor.fetchone()

            if row:
                return {
                    'id': row[0],
                    'project_id': row[1],
                    'purpose': row[2],
                    'provider': row[3],
                    'model': row[4],
                    'operation': row[5],
                    'input_tokens': row[6],
                    'output_tokens': row[7],
                    'total_tokens': row[8],
                    'latency_ms': round(row[9] or 0, 2),
                    'status': row[10],
                    'error_message': row[11],
                    'request_content': row[12],
                    'response_content': row[13],
                    'user_id': row[14],
                    'session_id': row[15],
                    'created_at': row[16]
                }
            return None


# 全局服务实例
ai_usage_tracker = AIUsageTracker()
ai_usage_query = AIUsageQueryService()