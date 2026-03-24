"""
审计轨迹服务
完整记录每一笔样本的"为什么抽、如何抽、结果如何"
"""
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from app.core.database import get_db_cursor, get_db


class AuditAction(str, Enum):
    """审计动作类型"""
    # 项目相关
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_DELETED = "project.deleted"

    # 凭证相关
    VOUCHER_IMPORTED = "voucher.imported"
    VOUCHER_VIEWED = "voucher.viewed"
    VOUCHER_UPDATED = "voucher.updated"
    VOUCHER_OCR = "voucher.ocr"

    # 抽样相关
    SAMPLE_CREATED = "sample.created"
    SAMPLE_REVIEWED = "sample.reviewed"
    SAMPLE_EXPORTED = "sample.exported"

    # 规则相关
    RULE_CREATED = "rule.created"
    RULE_EXECUTED = "rule.executed"

    # AI相关
    AI_ANALYZED = "ai.analyzed"
    AI_SAMPLING = "ai.sampling"

    # 任务相关
    TASK_ASSIGNED = "task.assigned"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_REASSIGNED = "task.reassigned"

    # 底稿相关
    PAPER_GENERATED = "paper.generated"
    PAPER_EXPORTED = "paper.exported"

    # 验证相关
    VALIDATION_PERFORMED = "validation.performed"
    COMPLIANCE_CHECKED = "compliance.checked"

    # 匹配相关
    MATCHING_PERFORMED = "matching.performed"


@dataclass
class AuditEvent:
    """审计事件"""
    action: AuditAction
    target_type: str
    target_id: str
    user_id: str
    user_name: str
    reason: str              # 为什么
    method: str              # 如何做
    result: str              # 结果如何
    details: Dict[str, Any]  # 详细信息
    ip_address: str = ""
    session_id: str = ""


@dataclass
class AuditRecord:
    """审计记录"""
    id: str
    project_id: str
    action: str
    target_type: str
    target_id: str
    user_id: str
    user_name: str
    reason: str
    method: str
    result: str
    details: Dict[str, Any]
    ip_address: str
    session_id: str
    created_at: datetime


class AuditTrail:
    """审计轨迹服务"""

    def __init__(self):
        self._ensure_table()

    def _ensure_table(self):
        """确保审计轨迹表存在"""
        with get_db_cursor() as cursor:
            # 审计轨迹表已存在，检查是否需要添加缺失字段
            try:
                cursor.execute("SELECT reason FROM audit_trail LIMIT 1")
            except:
                # 添加缺失字段
                try:
                    cursor.execute("ALTER TABLE audit_trail ADD COLUMN reason TEXT")
                except:
                    pass
                try:
                    cursor.execute("ALTER TABLE audit_trail ADD COLUMN method TEXT")
                except:
                    pass
                try:
                    cursor.execute("ALTER TABLE audit_trail ADD COLUMN result TEXT")
                except:
                    pass
                get_db().commit()

    def record(
        self,
        project_id: str,
        event: AuditEvent
    ) -> str:
        """
        记录审计事件

        Args:
            project_id: 项目ID
            event: 审计事件

        Returns:
            str: 记录ID
        """
        record_id = str(uuid.uuid4())
        now = datetime.now()

        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO audit_trail
                (id, project_id, user_id, action, target_type, target_id,
                 details, reason, method, result, ip_address, session_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    record_id,
                    project_id,
                    event.user_id,
                    event.action.value,
                    event.target_type,
                    event.target_id,
                    json.dumps(event.details, ensure_ascii=False),
                    event.reason,
                    event.method,
                    event.result,
                    event.ip_address,
                    event.session_id,
                    now
                ]
            )
            get_db().commit()

        return record_id

    def record_sample_creation(
        self,
        project_id: str,
        sample_id: str,
        voucher_id: str,
        rule_name: str,
        user_id: str,
        user_name: str
    ):
        """
        记录抽样创建

        Args:
            project_id: 项目ID
            sample_id: 样本ID
            voucher_id: 凭证ID
            rule_name: 规则名称
            user_id: 用户ID
            user_name: 用户名
        """
        event = AuditEvent(
            action=AuditAction.SAMPLE_CREATED,
            target_type="sample",
            target_id=sample_id,
            user_id=user_id,
            user_name=user_name,
            reason=f"根据规则【{rule_name}】抽取",
            method="系统自动抽样",
            result="样本创建成功",
            details={
                "voucher_id": voucher_id,
                "rule_name": rule_name
            }
        )

        self.record(project_id, event)

    def record_sample_review(
        self,
        project_id: str,
        sample_id: str,
        review_result: str,
        user_id: str,
        user_name: str,
        notes: str = ""
    ):
        """
        记录样本复核

        Args:
            project_id: 项目ID
            sample_id: 样本ID
            review_result: 复核结果
            user_id: 用户ID
            user_name: 用户名
            notes: 复核说明
        """
        event = AuditEvent(
            action=AuditAction.SAMPLE_REVIEWED,
            target_type="sample",
            target_id=sample_id,
            user_id=user_id,
            user_name=user_name,
            reason="执行审计程序复核",
            method="人工复核",
            result=review_result,
            details={
                "notes": notes,
                "review_result": review_result
            }
        )

        self.record(project_id, event)

    def record_voucher_import(
        self,
        project_id: str,
        file_name: str,
        success_count: int,
        fail_count: int,
        user_id: str,
        user_name: str
    ):
        """
        记录凭证导入

        Args:
            project_id: 项目ID
            file_name: 文件名
            success_count: 成功数
            fail_count: 失败数
            user_id: 用户ID
            user_name: 用户名
        """
        event = AuditEvent(
            action=AuditAction.VOUCHER_IMPORTED,
            target_type="project",
            target_id=project_id,
            user_id=user_id,
            user_name=user_name,
            reason="导入凭证数据",
            method="文件上传导入",
            result=f"成功{success_count}条，失败{fail_count}条",
            details={
                "file_name": file_name,
                "success_count": success_count,
                "fail_count": fail_count
            }
        )

        self.record(project_id, event)

    def record_rule_execution(
        self,
        project_id: str,
        rule_id: str,
        rule_name: str,
        matched_count: int,
        total_count: int,
        user_id: str = "system",
        user_name: str = "系统"
    ):
        """
        记录规则执行

        Args:
            project_id: 项目ID
            rule_id: 规则ID
            rule_name: 规则名称
            matched_count: 匹配数
            total_count: 总数
            user_id: 用户ID
            user_name: 用户名
        """
        event = AuditEvent(
            action=AuditAction.RULE_EXECUTED,
            target_type="rule",
            target_id=rule_id,
            user_id=user_id,
            user_name=user_name,
            reason=f"执行抽样规则【{rule_name}】",
            method="规则引擎自动执行",
            result=f"从{total_count}条中匹配{matched_count}条",
            details={
                "rule_name": rule_name,
                "matched_count": matched_count,
                "total_count": total_count
            }
        )

        self.record(project_id, event)

    def record_ai_analysis(
        self,
        project_id: str,
        analysis_type: str,
        voucher_count: int,
        user_id: str = "system",
        user_name: str = "系统"
    ):
        """
        记录AI分析

        Args:
            project_id: 项目ID
            analysis_type: 分析类型
            voucher_count: 凭证数
            user_id: 用户ID
            user_name: 用户名
        """
        event = AuditEvent(
            action=AuditAction.AI_ANALYZED,
            target_type="analysis",
            target_id="",
            user_id=user_id,
            user_name=user_name,
            reason=f"执行AI{analysis_type}分析",
            method="AI模型分析",
            result=f"完成{voucher_count}条凭证分析",
            details={
                "analysis_type": analysis_type,
                "voucher_count": voucher_count
            }
        )

        self.record(project_id, event)

    def record_task_assignment(
        self,
        project_id: str,
        task_id: str,
        assignee_name: str,
        sample_count: int,
        user_id: str,
        user_name: str
    ):
        """
        记录任务分派

        Args:
            project_id: 项目ID
            task_id: 任务ID
            assignee_name: 被分派人
            sample_count: 样本数
            user_id: 用户ID
            user_name: 用户名
        """
        event = AuditEvent(
            action=AuditAction.TASK_ASSIGNED,
            target_type="task",
            target_id=task_id,
            user_id=user_id,
            user_name=user_name,
            reason="分派审计任务",
            method="任务分派系统",
            result=f"已分派给{assignee_name}，共{sample_count}个样本",
            details={
                "assignee_name": assignee_name,
                "sample_count": sample_count
            }
        )

        self.record(project_id, event)

    def record_paper_generation(
        self,
        project_id: str,
        paper_id: str,
        paper_type: str,
        user_id: str = "system",
        user_name: str = "系统"
    ):
        """
        记录底稿生成

        Args:
            project_id: 项目ID
            paper_id: 底稿ID
            paper_type: 底稿类型
            user_id: 用户ID
            user_name: 用户名
        """
        event = AuditEvent(
            action=AuditAction.PAPER_GENERATED,
            target_type="paper",
            target_id=paper_id,
            user_id=user_id,
            user_name=user_name,
            reason="生成审计工作底稿",
            method="系统自动生成",
            result=f"生成{paper_type}类型底稿",
            details={
                "paper_type": paper_type
            }
        )

        self.record(project_id, event)

    def record_compliance_check(
        self,
        project_id: str,
        rule_codes: List[str],
        alert_count: int,
        user_id: str = "system",
        user_name: str = "系统"
    ):
        """
        记录合规检查

        Args:
            project_id: 项目ID
            rule_codes: 规则代码列表
            alert_count: 预警数
            user_id: 用户ID
            user_name: 用户名
        """
        event = AuditEvent(
            action=AuditAction.COMPLIANCE_CHECKED,
            target_type="compliance",
            target_id="",
            user_id=user_id,
            user_name=user_name,
            reason="执行合规性检查",
            method="合规检查规则引擎",
            result=f"检查完成，发现{alert_count}项预警",
            details={
                "rule_codes": rule_codes,
                "alert_count": alert_count
            }
        )

        self.record(project_id, event)

    def query(
        self,
        project_id: str,
        start_date: datetime = None,
        end_date: datetime = None,
        user_id: str = None,
        action: AuditAction = None,
        target_type: str = None,
        page: int = 1,
        page_size: int = 50
    ) -> List[AuditRecord]:
        """
        查询审计轨迹

        Args:
            project_id: 项目ID
            start_date: 开始日期
            end_date: 结束日期
            user_id: 用户ID
            action: 动作类型
            target_type: 目标类型
            page: 页码
            page_size: 每页数量

        Returns:
            List[AuditRecord]: 审计记录列表
        """
        offset = (page - 1) * page_size

        with get_db_cursor() as cursor:
            conditions = ["project_id = ?"]
            params = [project_id]

            if start_date:
                conditions.append("created_at >= ?")
                params.append(start_date)

            if end_date:
                conditions.append("created_at <= ?")
                params.append(end_date)

            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)

            if action:
                conditions.append("action = ?")
                params.append(action.value)

            if target_type:
                conditions.append("target_type = ?")
                params.append(target_type)

            where_clause = " AND ".join(conditions)

            cursor.execute(
                f"""
                SELECT id, project_id, user_id, action, target_type, target_id,
                       details, reason, method, result, ip_address, session_id, created_at
                FROM audit_trail
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                params + [page_size, offset]
            )
            rows = cursor.fetchall()

            return [
                AuditRecord(
                    id=row[0],
                    project_id=row[1],
                    user_id=row[2],
                    action=row[3],
                    target_type=row[4],
                    target_id=row[5],
                    user_name="",  # 从details获取
                    reason=row[7] or "",
                    method=row[8] or "",
                    result=row[9] or "",
                    details=json.loads(row[6]) if isinstance(row[6], str) else row[6],
                    ip_address=row[10] or "",
                    session_id=row[11] or "",
                    created_at=row[12]
                )
                for row in rows
            ]

    def get_sample_trail(
        self,
        project_id: str,
        sample_id: str
    ) -> List[AuditRecord]:
        """
        获取样本的完整轨迹

        Args:
            project_id: 项目ID
            sample_id: 样本ID

        Returns:
            List[AuditRecord]: 审计记录列表
        """
        return self.query(
            project_id=project_id,
            target_type="sample",
            page_size=100
        )

    def get_user_activity(
        self,
        project_id: str,
        user_id: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[AuditRecord]:
        """
        获取用户活动记录

        Args:
            project_id: 项目ID
            user_id: 用户ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            List[AuditRecord]: 审计记录列表
        """
        return self.query(
            project_id=project_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            page_size=100
        )

    def get_statistics(
        self,
        project_id: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """
        获取审计轨迹统计

        Args:
            project_id: 项目ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            Dict: 统计数据
        """
        with get_db_cursor() as cursor:
            conditions = ["project_id = ?"]
            params = [project_id]

            if start_date:
                conditions.append("created_at >= ?")
                params.append(start_date)

            if end_date:
                conditions.append("created_at <= ?")
                params.append(end_date)

            where_clause = " AND ".join(conditions)

            # 总记录数
            cursor.execute(
                f"SELECT COUNT(*) FROM audit_trail WHERE {where_clause}",
                params
            )
            total_count = cursor.fetchone()[0]

            # 按动作统计
            cursor.execute(
                f"""
                SELECT action, COUNT(*) as cnt
                FROM audit_trail
                WHERE {where_clause}
                GROUP BY action
                ORDER BY cnt DESC
                """,
                params
            )
            by_action = {row[0]: row[1] for row in cursor.fetchall()}

            # 按用户统计
            cursor.execute(
                f"""
                SELECT user_id, COUNT(*) as cnt
                FROM audit_trail
                WHERE {where_clause}
                GROUP BY user_id
                ORDER BY cnt DESC
                LIMIT 10
                """,
                params
            )
            by_user = {row[0]: row[1] for row in cursor.fetchall()}

            # 按日期统计
            cursor.execute(
                f"""
                SELECT DATE(created_at) as date, COUNT(*) as cnt
                FROM audit_trail
                WHERE {where_clause}
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT 30
                """,
                params
            )
            by_date = {str(row[0]): row[1] for row in cursor.fetchall()}

            return {
                "total_count": total_count,
                "by_action": by_action,
                "by_user": by_user,
                "by_date": by_date
            }

    def export_trail(
        self,
        project_id: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[Dict[str, Any]]:
        """
        导出审计轨迹

        Args:
            project_id: 项目ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            List[Dict]: 导出数据
        """
        records = self.query(
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            page_size=10000
        )

        return [
            {
                "id": r.id,
                "project_id": r.project_id,
                "action": r.action,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "user_id": r.user_id,
                "reason": r.reason,
                "method": r.method,
                "result": r.result,
                "ip_address": r.ip_address,
                "created_at": str(r.created_at)
            }
            for r in records
        ]


# 全局服务实例
audit_trail = AuditTrail()