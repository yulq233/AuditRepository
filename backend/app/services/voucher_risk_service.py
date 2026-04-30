"""
凭证风险服务
提供凭证级别的风险分析、标签生成、批量操作等功能
"""
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import asyncio

from app.core.database import get_db_cursor, get_db
from app.services.risk_profile_service import (
    STANDARD_RISK_TAGS, VoucherRiskTag, HIGH_RISK_SUBJECTS, ATTENTION_SUBJECTS
)

logger = logging.getLogger(__name__)


@dataclass
class VoucherRiskResult:
    """凭证风险分析结果"""
    voucher_id: str
    voucher_no: str
    risk_score: float
    risk_level: str
    risk_tags: List[VoucherRiskTag]
    risk_factors: List[str]
    explanation: str
    ai_risk_explanation: str = ""  # AI风险解释
    ai_audit_attention: List[str] = None  # AI审计关注点

    def __post_init__(self):
        if self.ai_audit_attention is None:
            self.ai_audit_attention = []


class VoucherRiskService:
    """凭证风险服务"""

    def __init__(self):
        self.risk_tags = STANDARD_RISK_TAGS

    def analyze_voucher(
        self,
        voucher: Dict[str, Any],
        ai_result: Any = None,  # AI分析结果
        subject_risk_level: str = None  # 科目风险等级
    ) -> VoucherRiskResult:
        """
        分析单个凭证风险

        Args:
            voucher: 凭证数据
            ai_result: AI分析结果（可选）
            subject_risk_level: 科目风险等级（可选，用于保持风险一致性）

        Returns:
            VoucherRiskResult: 风险分析结果
        """
        voucher_id = voucher.get('id', '')
        voucher_no = voucher.get('voucher_no', '')

        # 生成风险标签（规则引擎）
        risk_tags = self._generate_risk_tags(voucher)

        # 计算风险分数
        risk_score = self._calculate_risk_score(risk_tags, voucher)

        # 确定风险等级
        if risk_score >= 70:
            risk_level = "high"
        elif risk_score >= 40:
            risk_level = "medium"
        else:
            risk_level = "low"

        # 生成风险因素列表
        risk_factors = [tag.tag_name for tag in risk_tags]

        # 生成解释
        explanation = self._generate_explanation(voucher_no, risk_level, risk_score, risk_factors)

        # AI分析结果融合
        ai_risk_explanation = ""
        ai_audit_attention = []
        if ai_result:
            # 融合AI分析的风险分数（40% AI + 60% 规则）
            ai_score = getattr(ai_result, 'risk_score', 50)
            fused_score = risk_score * 0.6 + ai_score * 0.4
            risk_score = round(fused_score, 2)

            # 更新风险等级
            if risk_score >= 70:
                risk_level = "high"
            elif risk_score >= 40:
                risk_level = "medium"
            else:
                risk_level = "low"

            # 添加AI风险标签（无论是否有科目风险等级）
            ai_tags = getattr(ai_result, 'risk_tags', [])
            for tag_name in ai_tags:
                # 清理标签，移除中间位置的间隔号·
                tag_name = tag_name.strip().replace('·', '').rstrip('.。,，')
                if tag_name and tag_name not in risk_factors:
                    risk_tags.append(VoucherRiskTag(
                        tag_code="AI_ANALYSIS",
                        tag_name=tag_name,
                        tag_category="ai",
                        severity="medium",
                        details={"source": "AI分析"}
                    ))
                    risk_factors.append(tag_name)

            # 获取AI风险解释和审计关注点
            ai_risk_explanation = getattr(ai_result, 'risk_explanation', '')
            ai_audit_attention = getattr(ai_result, 'audit_attention', [])

        # 融合科目风险等级（确保与科目维度一致性）
        if subject_risk_level:
            # 科目风险等级作为保底约束
            # 如果科目是高风险，凭证最低也是中风险
            if subject_risk_level == "high" and risk_level == "low":
                risk_level = "medium"
                risk_score = max(risk_score, 40)
                risk_factors.append("科目高风险关联")
            elif subject_risk_level == "medium" and risk_level == "low":
                # 中风险科目下的凭证保持原判，但记录关联
                pass

            # 如果科目是高风险，凭证风险等级提升
            if subject_risk_level == "high":
                # 高风险科目下的凭证，风险分数增加10分
                risk_score = min(100, risk_score + 10)

        return VoucherRiskResult(
            voucher_id=voucher_id,
            voucher_no=voucher_no,
            risk_score=round(risk_score, 2),
            risk_level=risk_level,
            risk_tags=risk_tags,
            risk_factors=risk_factors,
            explanation=explanation,
            ai_risk_explanation=ai_risk_explanation,
            ai_audit_attention=ai_audit_attention
        )

    async def batch_analyze_vouchers(
        self,
        project_id: str,
        filters: Dict[str, Any] = None,
        use_ai: bool = True,
        save_results: bool = True
    ) -> List[VoucherRiskResult]:
        """
        批量分析凭证风险（支持AI增强，与第二步总体风险分析方案一致）

        Args:
            project_id: 项目ID
            filters: 筛选条件
            use_ai: 是否使用AI分析
            save_results: 是否保存结果到数据库（第二步总体风险分析可设为False）

        Returns:
            List[VoucherRiskResult]: 风险分析结果列表
        """
        vouchers = self._get_vouchers(project_id, filters)
        if not vouchers:
            logger.warning(f"[凭证风险] 项目 {project_id} 没有凭证数据")
            return []

        results = []

        # 获取科目风险画像，用于保持风险一致性
        subject_risks = self._get_subject_risk_levels(project_id)
        logger.info(f"[凭证风险] 已加载 {len(subject_risks)} 个科目风险等级")

        # 如果使用AI，先进行附件识别预处理，然后AI批量分析
        ai_results = {}
        if use_ai:
            try:
                from app.services.ai_risk_service import ai_risk_analyzer
                from app.api.ai import recognize_voucher_attachments

                # 第一步：附件识别预处理（与第二步总体风险分析方案一致）
                voucher_ids = [v.get('id') for v in vouchers]
                logger.info(f"[凭证风险] 第一步：开始附件识别预处理，凭证数={len(voucher_ids)}")
                attachment_contents = await recognize_voucher_attachments(project_id, voucher_ids)
                logger.info(f"[凭证风险] 第一步完成：附件识别完成，识别内容数={len(attachment_contents)}")

                # 第二步：AI风险分析（传入附件识别结果）
                logger.info(f"[凭证风险] 第二步：开始AI分析 {len(vouchers)} 张凭证...")
                ai_results_list = await ai_risk_analyzer.batch_analyze_vouchers(
                    vouchers,
                    batch_size=10,
                    attachment_contents=attachment_contents
                )

                # 转换为字典方便查找
                for ai_result in ai_results_list:
                    ai_results[ai_result.voucher_id] = ai_result

                logger.info(f"[凭证风险] 第二步完成：AI分析完成，共 {len(ai_results)} 条结果")
            except Exception as e:
                logger.error(f"[凭证风险] AI分析失败: {e}")
                ai_results = {}

        # 逐个分析凭证（融合规则引擎、AI结果和科目风险）
        for voucher in vouchers:
            ai_result = ai_results.get(voucher.get('id'))
            # 获取凭证所属科目的风险等级
            subject_code = voucher.get('subject_code')
            subject_risk_level = subject_risks.get(subject_code)
            result = self.analyze_voucher(voucher, ai_result, subject_risk_level)
            results.append(result)

        # 保存结果（可选）
        if save_results:
            self._save_voucher_risks(project_id, results)

        return results

    def _get_subject_risk_levels(self, project_id: str) -> Dict[str, str]:
        """获取项目科目风险等级映射"""
        subject_risks = {}
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT subject_code, risk_level
                    FROM risk_profiles
                    WHERE project_id = ?
                    """,
                    [project_id]
                )
                for row in cursor.fetchall():
                    subject_risks[row[0]] = row[1]
        except Exception as e:
            logger.error(f"[凭证风险] 获取科目风险等级失败: {e}")
        return subject_risks

    def _get_vouchers(
        self,
        project_id: str,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """获取凭证列表"""
        with get_db_cursor() as cursor:
            sql = """
                SELECT id, voucher_no, voucher_date, amount,
                       subject_code, subject_name, description, counterparty
                FROM vouchers
                WHERE project_id = ?
            """
            params = [project_id]

            if filters:
                if filters.get('voucher_ids'):
                    # 按凭证ID列表筛选
                    voucher_ids = filters['voucher_ids']
                    if voucher_ids:
                        placeholders = ','.join(['?' for _ in voucher_ids])
                        sql += f" AND id IN ({placeholders})"
                        params.extend(voucher_ids)
                if filters.get('risk_level'):
                    # 需要先计算风险，这里暂不支持
                    pass
                if filters.get('min_amount'):
                    sql += " AND amount >= ?"
                    params.append(filters['min_amount'])
                if filters.get('max_amount'):
                    sql += " AND amount <= ?"
                    params.append(filters['max_amount'])
                if filters.get('start_date'):
                    sql += " AND voucher_date >= ?"
                    params.append(filters['start_date'])
                if filters.get('end_date'):
                    sql += " AND voucher_date <= ?"
                    params.append(filters['end_date'])
                if filters.get('counterparty'):
                    sql += " AND counterparty LIKE ?"
                    params.append(f"%{filters['counterparty']}%")

            sql += " ORDER BY amount DESC"

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "voucher_no": row[1],
                    "voucher_date": str(row[2]) if row[2] else None,
                    "amount": float(row[3]) if row[3] else 0,
                    "subject_code": row[4],
                    "subject_name": row[5],
                    "description": row[6],
                    "counterparty": row[7]
                }
                for row in rows
            ]

    def _generate_risk_tags(self, voucher: Dict[str, Any]) -> List[VoucherRiskTag]:
        """生成风险标签"""
        tags = []

        # 辅助函数：创建风险标签
        def make_tag(tag_code: str, details: Dict[str, Any] = None) -> VoucherRiskTag:
            tag_info = STANDARD_RISK_TAGS.get(tag_code, {})
            return VoucherRiskTag(
                tag_code=tag_code,
                tag_name=tag_info.get("name", tag_code),
                tag_category=tag_info.get("category", "unknown"),
                severity=tag_info.get("severity", "medium"),
                details=details or {}
            )

        # 金额检查
        amount = voucher.get('amount', 0) or 0
        if amount > 500000:
            tags.append(make_tag("SUPER_LARGE_AMOUNT", {"amount": amount}))
        elif amount > 100000:
            tags.append(make_tag("LARGE_AMOUNT", {"amount": amount}))

        if amount >= 10000 and amount % 10000 == 0:
            tags.append(make_tag("ROUND_AMOUNT", {"amount": amount}))

        # 时间检查
        voucher_date = voucher.get('voucher_date')
        if voucher_date:
            try:
                if isinstance(voucher_date, str):
                    date_obj = datetime.strptime(voucher_date[:10], '%Y-%m-%d')
                else:
                    date_obj = voucher_date

                if date_obj.weekday() >= 5:
                    tags.append(make_tag("WEEKEND_TRANSACTION", {"date": str(voucher_date)}))

                if date_obj.day >= 26:
                    tags.append(make_tag("MONTH_END_CONCENTRATION", {"date": str(voucher_date)}))

                if date_obj.month == 12 and date_obj.day >= 25:
                    tags.append(make_tag("YEAR_END_TRANSACTION", {"date": str(voucher_date)}))
            except:
                pass

        # 交易对手检查
        counterparty = voucher.get('counterparty', '')
        if counterparty:
            related_keywords = ['关联', '股东', '子公司', '母公司', '兄弟公司', '联营', '合营']
            if any(kw in counterparty for kw in related_keywords):
                tags.append(make_tag("RELATED_PARTY", {"counterparty": counterparty}))

            if len(counterparty) <= 3 or '个人' in counterparty:
                tags.append(make_tag("PERSONAL_TRANSACTION", {"counterparty": counterparty}))

        # 摘要检查
        description = voucher.get('description', '')
        if description:
            sensitive_words = ['调整', '冲销', '暂估', '补记', '更正', '结转', '待摊', '预提', '挂账', '清理']
            found_words = [w for w in sensitive_words if w in description]
            if found_words:
                tags.append(make_tag("SENSITIVE_KEYWORD", {"keywords": found_words}))

            if len(description) < 8:
                tags.append(make_tag("VAGUE_DESCRIPTION", {"description": description}))
        elif amount > 50000:
            tags.append(make_tag("VAGUE_DESCRIPTION", {"description": "缺失"}))

        # 科目检查
        subject_code = voucher.get('subject_code', '') or ''
        prefix = subject_code[:4]

        if prefix in HIGH_RISK_SUBJECTS:
            tags.append(make_tag("HIGH_RISK_SUBJECT", {"subject_code": subject_code}))
        elif prefix in ATTENTION_SUBJECTS:
            tags.append(make_tag("ATTENTION_SUBJECT", {"subject_code": subject_code}))

        return tags

    def _calculate_risk_score(
        self,
        tags: List[VoucherRiskTag],
        voucher: Dict[str, Any]
    ) -> float:
        """计算风险分数"""
        base_score = 30.0

        severity_scores = {
            "high": 25,
            "medium": 15,
            "low": 5
        }

        for tag in tags:
            base_score += severity_scores.get(tag.severity, 0)

        # 金额因素
        amount = voucher.get('amount', 0) or 0
        if amount > 500000:
            base_score += 15
        elif amount > 100000:
            base_score += 8

        return min(base_score, 100)

    def _generate_explanation(
        self,
        voucher_no: str,
        risk_level: str,
        risk_score: float,
        risk_factors: List[str]
    ) -> str:
        """生成风险解释"""
        level_text = {"high": "高风险", "medium": "中风险", "low": "低风险"}

        explanation = f"凭证{voucher_no}风险评分{risk_score:.0f}分，属于{level_text.get(risk_level, '未知')}凭证。"

        if risk_factors:
            explanation += f"主要风险点：{'；'.join(risk_factors[:4])}。"

        if risk_level == "high":
            explanation += "建议重点审查业务真实性和凭证完整性。"
        elif risk_level == "medium":
            explanation += "建议进一步核实相关业务背景。"
        else:
            explanation += "可按常规程序进行审计抽查。"

        return explanation

    def _save_voucher_risks(
        self,
        project_id: str,
        results: List[VoucherRiskResult]
    ):
        """保存凭证风险分析结果"""
        with get_db_cursor() as cursor:
            # 先删除该项目所有旧的凭证风险标签记录
            cursor.execute(
                "DELETE FROM voucher_risk_tags WHERE project_id = ?",
                [project_id]
            )

            # 更新凭证表的风险字段
            for r in results:
                # 构建风险标签JSON
                risk_tags_json = json.dumps([{
                    "code": t.tag_code,
                    "name": t.tag_name,
                    "category": t.tag_category,
                    "severity": t.severity
                } for t in r.risk_tags], ensure_ascii=False)

                # 构建AI分析JSON（包含风险解释和审计关注点）
                ai_analysis = {}
                if r.ai_risk_explanation:
                    ai_analysis["explanation"] = r.ai_risk_explanation
                if r.ai_audit_attention:
                    ai_analysis["audit_attention"] = r.ai_audit_attention

                cursor.execute(
                    """
                    UPDATE vouchers
                    SET risk_score = ?, risk_level = ?, risk_tags = ?, ai_analysis = ?
                    WHERE id = ?
                    """,
                    [
                        r.risk_score,
                        r.risk_level,
                        risk_tags_json,
                        json.dumps(ai_analysis, ensure_ascii=False) if ai_analysis else None,
                        r.voucher_id
                    ]
                )

                # 插入风险标签记录
                for tag in r.risk_tags:
                    cursor.execute(
                        """
                        INSERT INTO voucher_risk_tags
                        (id, project_id, voucher_id, tag_code, tag_name, tag_category, severity, details)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            str(uuid.uuid4()),
                            project_id,
                            r.voucher_id,
                            tag.tag_code,
                            tag.tag_name,
                            tag.tag_category,
                            tag.severity,
                            json.dumps(tag.details, ensure_ascii=False)
                        ]
                    )

            get_db().commit()
            logger.info(f"[凭证风险] 已保存 {len(results)} 条凭证风险分析结果")

    def get_vouchers_by_risk_level(
        self,
        project_id: str,
        risk_level: str,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        按风险等级获取凭证列表

        Args:
            project_id: 项目ID
            risk_level: 风险等级
            page: 页码
            page_size: 每页数量

        Returns:
            Dict: 分页结果
        """
        with get_db_cursor() as cursor:
            # 获取总数
            cursor.execute(
                """
                SELECT COUNT(*) FROM vouchers
                WHERE project_id = ? AND risk_level = ?
                """,
                [project_id, risk_level]
            )
            total = cursor.fetchone()[0] or 0

            # 获取分页数据
            offset = (page - 1) * page_size
            cursor.execute(
                """
                SELECT id, voucher_no, voucher_date, amount,
                       subject_code, subject_name, description, counterparty,
                       risk_score, risk_level, risk_tags
                FROM vouchers
                WHERE project_id = ? AND risk_level = ?
                ORDER BY risk_score DESC, amount DESC
                LIMIT ? OFFSET ?
                """,
                [project_id, risk_level, page_size, offset]
            )
            rows = cursor.fetchall()

            items = []
            for row in rows:
                risk_tags = json.loads(row[10]) if isinstance(row[10], str) else row[10] or []
                items.append({
                    "id": row[0],
                    "voucher_no": row[1],
                    "voucher_date": str(row[2]) if row[2] else None,
                    "amount": float(row[3]) if row[3] else 0,
                    "subject_code": row[4],
                    "subject_name": row[5],
                    "description": row[6],
                    "counterparty": row[7],
                    "risk_score": float(row[8]) if row[8] else 0,
                    "risk_level": row[9],
                    "risk_tags": risk_tags
                })

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }

    def get_vouchers_by_tags(
        self,
        project_id: str,
        tag_codes: List[str],
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        按风险标签获取凭证列表

        Args:
            project_id: 项目ID
            tag_codes: 标签代码列表
            page: 页码
            page_size: 每页数量

        Returns:
            Dict: 分页结果
        """
        with get_db_cursor() as cursor:
            placeholders = ",".join(["?" for _ in tag_codes])

            # 获取总数
            cursor.execute(
                f"""
                SELECT COUNT(DISTINCT v.id)
                FROM vouchers v
                JOIN voucher_risk_tags t ON v.id = t.voucher_id
                WHERE v.project_id = ? AND t.tag_code IN ({placeholders})
                """,
                [project_id] + tag_codes
            )
            total = cursor.fetchone()[0] or 0

            # 获取分页数据
            offset = (page - 1) * page_size
            cursor.execute(
                f"""
                SELECT DISTINCT v.id, v.voucher_no, v.voucher_date, v.amount,
                       v.subject_code, v.subject_name, v.description, v.counterparty,
                       v.risk_score, v.risk_level, v.risk_tags
                FROM vouchers v
                JOIN voucher_risk_tags t ON v.id = t.voucher_id
                WHERE v.project_id = ? AND t.tag_code IN ({placeholders})
                ORDER BY v.risk_score DESC, v.amount DESC
                LIMIT ? OFFSET ?
                """,
                [project_id] + tag_codes + [page_size, offset]
            )
            rows = cursor.fetchall()

            items = []
            for row in rows:
                risk_tags = json.loads(row[10]) if isinstance(row[10], str) else row[10] or []
                items.append({
                    "id": row[0],
                    "voucher_no": row[1],
                    "voucher_date": str(row[2]) if row[2] else None,
                    "amount": float(row[3]) if row[3] else 0,
                    "subject_code": row[4],
                    "subject_name": row[5],
                    "description": row[6],
                    "counterparty": row[7],
                    "risk_score": float(row[8]) if row[8] else 0,
                    "risk_level": row[9],
                    "risk_tags": risk_tags
                })

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }

    def get_risk_tag_statistics(self, project_id: str) -> List[Dict[str, Any]]:
        """
        获取风险标签统计

        Args:
            project_id: 项目ID

        Returns:
            List[Dict]: 标签统计列表
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT tag_code, tag_name, tag_category, severity, COUNT(*) as count
                FROM voucher_risk_tags
                WHERE project_id = ?
                GROUP BY tag_code, tag_name, tag_category, severity
                ORDER BY count DESC
                """,
                [project_id]
            )
            rows = cursor.fetchall()

            return [
                {
                    "tag_code": row[0],
                    "tag_name": row[1],
                    "tag_category": row[2],
                    "severity": row[3],
                    "count": row[4]
                }
                for row in rows
            ]

    def batch_add_to_sampling(
        self,
        project_id: str,
        voucher_ids: List[str],
        reason: str = "风险画像批量添加"
    ) -> Dict[str, Any]:
        """
        批量添加凭证到抽样清单

        Args:
            project_id: 项目ID
            voucher_ids: 凭证ID列表
            reason: 添加原因

        Returns:
            Dict: 操作结果
        """
        from app.services.sampling_strategy_service import SamplingStrategyRecommender

        with get_db_cursor() as cursor:
            # 创建抽样记录
            record_id = str(uuid.uuid4())
            now = datetime.now()

            cursor.execute(
                """
                INSERT INTO sampling_records
                (id, project_id, rule_name, rule_type, sample_size, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [record_id, project_id, "风险画像抽样", "risk_profile", len(voucher_ids), "completed", now]
            )

            # 添加样本
            added_count = 0
            for vid in voucher_ids:
                # 获取凭证风险信息
                cursor.execute(
                    """
                    SELECT voucher_no, risk_score, risk_level
                    FROM vouchers WHERE id = ?
                    """,
                    [vid]
                )
                row = cursor.fetchone()
                if row:
                    sample_id = str(uuid.uuid4())
                    cursor.execute(
                        """
                        INSERT INTO samples
                        (id, project_id, record_id, voucher_id, risk_score, risk_level, reason, sampled_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [sample_id, project_id, record_id, vid, row[1], row[2], reason, now]
                    )
                    added_count += 1

            get_db().commit()

        return {
            "success": True,
            "record_id": record_id,
            "added_count": added_count,
            "message": f"成功添加{added_count}条凭证到抽样清单"
        }

    def get_transaction_list(
        self,
        project_id: str,
        filters: Dict[str, Any] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        获取交易风险清单（支持高级筛选）

        Args:
            project_id: 项目ID
            filters: 筛选条件
            page: 页码
            page_size: 每页数量

        Returns:
            Dict: 分页结果
        """
        with get_db_cursor() as cursor:
            sql = """
                SELECT id, voucher_no, voucher_date, amount,
                       subject_code, subject_name, description, counterparty,
                       risk_score, risk_level, risk_tags, ai_analysis
                FROM vouchers
                WHERE project_id = ?
            """
            params = [project_id]

            if filters:
                if filters.get('risk_level'):
                    sql += " AND risk_level = ?"
                    params.append(filters['risk_level'])
                if filters.get('min_amount'):
                    sql += " AND amount >= ?"
                    params.append(filters['min_amount'])
                if filters.get('max_amount'):
                    sql += " AND amount <= ?"
                    params.append(filters['max_amount'])
                if filters.get('start_date'):
                    sql += " AND voucher_date >= ?"
                    params.append(filters['start_date'])
                if filters.get('end_date'):
                    sql += " AND voucher_date <= ?"
                    params.append(filters['end_date'])
                if filters.get('counterparty'):
                    sql += " AND counterparty LIKE ?"
                    params.append(f"%{filters['counterparty']}%")
                if filters.get('subject_code'):
                    sql += " AND subject_code LIKE ?"
                    params.append(f"{filters['subject_code']}%")

            # 获取总数
            count_sql = f"SELECT COUNT(*) FROM ({sql})"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()[0] or 0

            # 排序和分页
            sql += " ORDER BY risk_score DESC, amount DESC"
            sql += f" LIMIT {page_size} OFFSET {(page - 1) * page_size}"

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            items = []
            for row in rows:
                risk_tags = json.loads(row[10]) if isinstance(row[10], str) else row[10] or []
                ai_analysis = json.loads(row[11]) if isinstance(row[11], str) else row[11] or {}

                # 构建风险因素说明
                risk_factors = []
                for tag in risk_tags:
                    if isinstance(tag, dict):
                        risk_factors.append(tag.get('name', ''))

                # 添加AI分析的风险因素
                if ai_analysis:
                    ai_explanation = ai_analysis.get('explanation', '')
                    ai_attention = ai_analysis.get('audit_attention', [])
                    if ai_explanation and ai_explanation not in risk_factors:
                        risk_factors.append(f"AI分析: {ai_explanation}")
                    for attention in ai_attention:
                        if attention and attention not in risk_factors:
                            risk_factors.append(f"AI建议: {attention}")

                items.append({
                    "id": row[0],
                    "voucher_no": row[1],
                    "voucher_date": str(row[2]) if row[2] else None,
                    "amount": float(row[3]) if row[3] else 0,
                    "subject_code": row[4],
                    "subject_name": row[5],
                    "description": row[6],
                    "counterparty": row[7],
                    "risk_score": float(row[8]) if row[8] else 0,
                    "risk_level": row[9] or "low",
                    "risk_tags": risk_tags,
                    "risk_factors": risk_factors,
                    "ai_analysis": ai_analysis
                })

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }


# 全局服务实例
voucher_risk_service = VoucherRiskService()