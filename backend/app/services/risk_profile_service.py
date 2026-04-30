"""
风险画像生成服务
基于财报数据、科目属性、历史问题自动评估科目风险等级
支持规则引擎 + AI智能分析双重评估
"""
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from app.core.database import get_db_cursor, get_db

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """风险等级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RiskFactor:
    """风险因素"""
    name: str
    weight: float
    score: float
    description: str


@dataclass
class RiskProfile:
    """风险画像"""
    id: str
    project_id: str
    subject_code: str
    subject_name: str
    risk_level: RiskLevel
    risk_score: float
    risk_factors: List[RiskFactor]
    material_amount: float
    anomaly_score: float
    historical_issues: List[Dict[str, Any]]
    recommendation: str
    created_at: datetime


@dataclass
class ProjectRiskOverview:
    """项目风险概览"""
    id: str
    project_id: str
    overall_risk_score: float
    overall_risk_level: str
    dimension_scores: Dict[str, float]
    high_risk_subjects: List[Dict[str, Any]]
    risk_trend: List[Dict[str, Any]]
    generated_at: datetime


@dataclass
class CounterpartyRisk:
    """交易对手风险"""
    id: str
    project_id: str
    counterparty_name: str
    total_amount: float
    transaction_count: int
    concentration_ratio: float
    is_related_party: bool
    is_new_customer: bool
    risk_score: float
    risk_level: str
    risk_factors: List[str]


@dataclass
class TimeRiskAnalysis:
    """时间维度风险分析"""
    id: str
    project_id: str
    period: str
    period_type: str
    total_amount: float
    transaction_count: int
    volatility_score: float
    period_end_concentration: float
    anomaly_indicators: List[str]


@dataclass
class VoucherRiskTag:
    """凭证风险标签"""
    tag_code: str
    tag_name: str
    tag_category: str
    severity: str
    details: Dict[str, Any]


# 标准风险标签定义
STANDARD_RISK_TAGS = {
    # 金额类风险标签
    "LARGE_AMOUNT": {"name": "大额交易", "category": "amount", "severity": "medium"},
    "SUPER_LARGE_AMOUNT": {"name": "超大额交易", "category": "amount", "severity": "high"},
    "ROUND_AMOUNT": {"name": "整数金额", "category": "amount", "severity": "low"},

    # 时间类风险标签
    "WEEKEND_TRANSACTION": {"name": "周末交易", "category": "time", "severity": "medium"},
    "HOLIDAY_TRANSACTION": {"name": "节假日交易", "category": "time", "severity": "medium"},
    "MONTH_END_CONCENTRATION": {"name": "月末集中交易", "category": "time", "severity": "medium"},
    "YEAR_END_TRANSACTION": {"name": "年末交易", "category": "time", "severity": "medium"},
    "PERIOD_START_TRANSACTION": {"name": "月初交易", "category": "time", "severity": "low"},

    # 交易对手类风险标签
    "RELATED_PARTY": {"name": "关联方交易", "category": "counterparty", "severity": "high"},
    "NEW_CUSTOMER": {"name": "新客户交易", "category": "counterparty", "severity": "medium"},
    "NEW_SUPPLIER": {"name": "新供应商交易", "category": "counterparty", "severity": "medium"},
    "HIGH_CONCENTRATION": {"name": "高集中度交易对手", "category": "counterparty", "severity": "medium"},
    "PERSONAL_TRANSACTION": {"name": "个人交易", "category": "counterparty", "severity": "medium"},

    # 摘要/业务类风险标签
    "SENSITIVE_KEYWORD": {"name": "摘要含敏感词", "category": "business", "severity": "medium"},
    "VAGUE_DESCRIPTION": {"name": "摘要模糊", "category": "business", "severity": "low"},
    "ADJUSTMENT_ENTRY": {"name": "调整分录", "category": "business", "severity": "medium"},
    "REVERSAL_ENTRY": {"name": "冲销分录", "category": "business", "severity": "medium"},

    # 科目类风险标签
    "HIGH_RISK_SUBJECT": {"name": "高风险科目", "category": "subject", "severity": "high"},
    "ATTENTION_SUBJECT": {"name": "关注科目", "category": "subject", "severity": "medium"},

    # 文档类风险标签
    "MISSING_INVOICE": {"name": "缺少发票", "category": "document", "severity": "high"},
    "MISSING_CONTRACT": {"name": "缺少合同", "category": "document", "severity": "medium"},
    "MISSING_LOGISTICS": {"name": "缺少物流单", "category": "document", "severity": "medium"},
}


@dataclass
class RiskAssessmentInput:
    """风险评估输入"""
    project_id: str
    financial_statements: Dict[str, Any]
    subject_balances: List[Dict[str, Any]]
    historical_problems: List[Dict[str, Any]]
    industry_risks: List[str]


# 风险评估权重配置
RISK_WEIGHTS = {
    "amount_significance": 0.25,      # 金额重要性
    "business_complexity": 0.20,      # 业务复杂性
    "historical_issues": 0.20,        # 历史问题
    "industry_risk": 0.15,            # 行业风险
    "anomaly_indicators": 0.20        # 异常指标
}

# 高风险科目
HIGH_RISK_SUBJECTS = [
    "1122",  # 应收账款
    "2202",  # 应付账款
    "6001",  # 主营业务收入
    "6601",  # 销售费用
    "6602",  # 管理费用
    "6603",  # 财务费用
]

# 需特别关注的科目
ATTENTION_SUBJECTS = [
    "1405",  # 库存商品
    "1601",  # 固定资产
    "2221",  # 应交税费
    "2501",  # 长期借款
]


class RiskProfileGenerator:
    """风险画像生成器（规则引擎 + AI分析）"""

    def __init__(self):
        self.weights = RISK_WEIGHTS
        self._ai_analyzer = None  # 懒加载AI分析器

    @property
    def ai_analyzer(self):
        """获取AI分析器（懒加载）"""
        if self._ai_analyzer is None:
            try:
                from app.services.ai_risk_service import ai_risk_analyzer
                self._ai_analyzer = ai_risk_analyzer
            except ImportError:
                logger.warning("AI风险分析服务不可用")
        return self._ai_analyzer

    def generate(
        self,
        project_id: str,
        subject_code: str,
        subject_name: str = None,
        subject_balances: List[Dict[str, Any]] = None,
        historical_issues: List[Dict[str, Any]] = None,
        industry_risks: List[str] = None
    ) -> RiskProfile:
        """
        生成科目风险画像

        Args:
            project_id: 项目ID
            subject_code: 科目代码
            subject_name: 科目名称
            subject_balances: 科目余额数据
            historical_issues: 历史审计问题
            industry_risks: 行业特定风险

        Returns:
            RiskProfile: 风险画像
        """
        risk_factors = []

        # 1. 金额重要性评估
        amount_score, amount_factor = self._assess_amount_significance(
            project_id, subject_code, subject_balances
        )
        risk_factors.append(amount_factor)

        # 2. 业务复杂性评估
        complexity_score, complexity_factor = self._assess_business_complexity(
            project_id, subject_code
        )
        risk_factors.append(complexity_factor)

        # 3. 历史问题评估
        history_score, history_factor = self._assess_historical_issues(
            subject_code, historical_issues
        )
        risk_factors.append(history_factor)

        # 4. 行业风险评估
        industry_score, industry_factor = self._assess_industry_risk(
            subject_code, industry_risks
        )
        risk_factors.append(industry_factor)

        # 5. 异常指标评估
        anomaly_score, anomaly_factor = self._assess_anomaly_indicators(
            project_id, subject_code
        )
        risk_factors.append(anomaly_factor)

        # 计算综合风险分数
        total_score = (
            amount_score * self.weights["amount_significance"] +
            complexity_score * self.weights["business_complexity"] +
            history_score * self.weights["historical_issues"] +
            industry_score * self.weights["industry_risk"] +
            anomaly_score * self.weights["anomaly_indicators"]
        )

        # 确定风险等级
        risk_level = self._determine_risk_level(total_score)

        # 计算重要金额阈值
        material_amount = self._calculate_material_amount(project_id)

        # 生成建议
        recommendation = self._generate_recommendation(
            risk_level, total_score, risk_factors
        )

        # 创建风险画像
        profile = RiskProfile(
            id=str(uuid.uuid4()),
            project_id=project_id,
            subject_code=subject_code,
            subject_name=subject_name or self._get_subject_name(subject_code),
            risk_level=risk_level,
            risk_score=total_score,
            risk_factors=risk_factors,
            material_amount=material_amount,
            anomaly_score=anomaly_score,
            historical_issues=historical_issues or [],
            recommendation=recommendation,
            created_at=datetime.now()
        )

        return profile

    async def generate_with_ai(
        self,
        project_id: str,
        subject_code: str,
        subject_name: str = None
    ) -> RiskProfile:
        """
        使用规则引擎 + AI分析生成风险画像

        Args:
            project_id: 项目ID
            subject_code: 科目代码
            subject_name: 科目名称

        Returns:
            RiskProfile: 增强的风险画像（含AI分析）
        """
        # 1. 先用规则引擎生成基础画像
        profile = self.generate(project_id, subject_code, subject_name)

        # 2. 尝试AI增强分析
        if self.ai_analyzer:
            try:
                # 获取凭证统计信息
                voucher_stats = self._get_voucher_stats(project_id, subject_code)

                # 调用AI分析
                ai_result = await self.ai_analyzer.analyze_subject_risk(
                    project_id=project_id,
                    subject_code=subject_code,
                    subject_name=profile.subject_name,
                    voucher_stats=voucher_stats,
                    historical_issues=profile.historical_issues
                )

                # 融合AI分析结果
                profile = self._merge_ai_analysis(profile, ai_result)

                logger.info(f"[风险画像] AI增强完成: {subject_code}")

            except Exception as e:
                logger.error(f"[风险画像] AI增强失败: {subject_code}, 错误: {e}")

        return profile

    def _get_voucher_stats(self, project_id: str, subject_code: str) -> Dict[str, Any]:
        """获取凭证统计信息"""
        stats = {
            'voucher_count': 0,
            'debit_amount': 0,
            'credit_amount': 0,
            'max_amount': 0,
            'avg_amount': 0,
            'large_count': 0,
            'medium_count': 0,
            'small_count': 0,
            'counterparty_count': 0,
            'month_end_ratio': 0,
            'year_end_ratio': 0,
            'weekend_ratio': 0
        }

        try:
            with get_db_cursor() as cursor:
                # 基本统计
                cursor.execute(
                    """
                    SELECT
                        COUNT(*),
                        COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0),
                        COALESCE(MAX(ABS(amount)), 0),
                        COALESCE(AVG(ABS(amount)), 0),
                        COUNT(DISTINCT counterparty)
                    FROM vouchers
                    WHERE project_id = ? AND subject_code LIKE ?
                    """,
                    [project_id, f"{subject_code}%"]
                )
                row = cursor.fetchone()
                if row:
                    stats['voucher_count'] = row[0] or 0
                    stats['debit_amount'] = float(row[1]) if row[1] else 0
                    stats['credit_amount'] = float(row[2]) if row[2] else 0
                    stats['max_amount'] = float(row[3]) if row[3] else 0
                    stats['avg_amount'] = float(row[4]) if row[4] else 0
                    stats['counterparty_count'] = row[5] or 0

                # 金额分布
                cursor.execute(
                    """
                    SELECT
                        SUM(CASE WHEN ABS(amount) >= 100000 THEN 1 ELSE 0 END),
                        SUM(CASE WHEN ABS(amount) >= 10000 AND ABS(amount) < 100000 THEN 1 ELSE 0 END),
                        SUM(CASE WHEN ABS(amount) < 10000 THEN 1 ELSE 0 END)
                    FROM vouchers
                    WHERE project_id = ? AND subject_code LIKE ?
                    """,
                    [project_id, f"{subject_code}%"]
                )
                row = cursor.fetchone()
                if row:
                    stats['large_count'] = row[0] or 0
                    stats['medium_count'] = row[1] or 0
                    stats['small_count'] = row[2] or 0

                # 时间分布
                total = stats['voucher_count'] or 1
                cursor.execute(
                    """
                    SELECT
                        SUM(CASE WHEN strftime('%d', voucher_date) IN ('28','29','30','31') THEN 1 ELSE 0 END),
                        SUM(CASE WHEN strftime('%m', voucher_date) = '12' THEN 1 ELSE 0 END),
                        SUM(CASE WHEN strftime('%w', voucher_date) IN ('0','6') THEN 1 ELSE 0 END)
                    FROM vouchers
                    WHERE project_id = ? AND subject_code LIKE ?
                    """,
                    [project_id, f"{subject_code}%"]
                )
                row = cursor.fetchone()
                if row:
                    stats['month_end_ratio'] = (row[0] or 0) / total
                    stats['year_end_ratio'] = (row[1] or 0) / total
                    stats['weekend_ratio'] = (row[2] or 0) / total

        except Exception as e:
            logger.error(f"[风险画像] 获取凭证统计失败: {e}")

        return stats

    def _merge_ai_analysis(self, profile: RiskProfile, ai_result) -> RiskProfile:
        """融合AI分析结果到风险画像"""
        # 加权融合风险分数（规则引擎60%，AI40%）
        merged_score = profile.risk_score * 0.6 + ai_result.risk_score * 0.4

        # 更新风险等级
        if merged_score >= 70:
            profile.risk_level = RiskLevel.HIGH
        elif merged_score >= 50:
            profile.risk_level = RiskLevel.MEDIUM
        else:
            profile.risk_level = RiskLevel.LOW

        profile.risk_score = round(merged_score, 2)

        # 添加AI识别的风险因素
        ai_factors = [
            RiskFactor(
                name=f"AI风险-{factor}",
                weight=0.15,
                score=ai_result.risk_score,
                description=f"AI识别风险: {factor}"
            )
            for factor in (ai_result.risk_factors or [])[:3]
        ]
        profile.risk_factors.extend(ai_factors)

        # 更新审计建议
        if ai_result.audit_suggestions:
            ai_suggestions = "\n".join([f"• {s}" for s in ai_result.audit_suggestions[:5]])
            profile.recommendation = f"{profile.recommendation}\n\n【AI审计建议】\n{ai_suggestions}"

        return profile

    def _assess_amount_significance(
        self,
        project_id: str,
        subject_code: str,
        subject_balances: List[Dict[str, Any]] = None
    ) -> tuple:
        """评估金额重要性"""
        score = 50.0
        description = ""

        with get_db_cursor() as cursor:
            # 获取科目总金额
            cursor.execute(
                """
                SELECT SUM(amount), COUNT(*)
                FROM vouchers
                WHERE project_id = ? AND subject_code LIKE ?
                """,
                [project_id, f"{subject_code}%"]
            )
            row = cursor.fetchone()

            subject_amount = float(row[0]) if row[0] else 0
            transaction_count = row[1] if row[1] else 0

            # 获取项目总金额
            cursor.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM vouchers WHERE project_id = ?",
                [project_id]
            )
            total_amount = float(cursor.fetchone()[0]) or 1

        # 计算占比
        percentage = (subject_amount / total_amount) * 100 if total_amount > 0 else 0

        if percentage > 20:
            score = 90.0
            description = f"金额占比{percentage:.1f}%，占比较大，需重点关注"
        elif percentage > 10:
            score = 70.0
            description = f"金额占比{percentage:.1f}%，具有一定重要性"
        elif percentage > 5:
            score = 50.0
            description = f"金额占比{percentage:.1f}%，重要性一般"
        else:
            score = 30.0
            description = f"金额占比{percentage:.1f}%，金额较小"

        # 交易笔数因素
        if transaction_count > 100:
            score = min(100, score + 10)
            description += f"，交易笔数{transaction_count}笔"

        factor = RiskFactor(
            name="金额重要性",
            weight=self.weights["amount_significance"],
            score=score,
            description=description
        )

        return score, factor

    def _assess_business_complexity(
        self,
        project_id: str,
        subject_code: str
    ) -> tuple:
        """评估业务复杂性"""
        score = 50.0
        description = ""

        with get_db_cursor() as cursor:
            # 统计交易对手数量
            cursor.execute(
                """
                SELECT COUNT(DISTINCT counterparty)
                FROM vouchers
                WHERE project_id = ? AND subject_code LIKE ? AND counterparty IS NOT NULL
                """,
                [project_id, f"{subject_code}%"]
            )
            counterparty_count = cursor.fetchone()[0] or 0

            # 统计金额分布
            cursor.execute(
                """
                SELECT MIN(amount), MAX(amount), AVG(amount), STDDEV(amount)
                FROM vouchers
                WHERE project_id = ? AND subject_code LIKE ? AND amount IS NOT NULL
                """,
                [project_id, f"{subject_code}%"]
            )
            row = cursor.fetchone()

            min_amount = float(row[0]) if row[0] else 0
            max_amount = float(row[1]) if row[1] else 0
            avg_amount = float(row[2]) if row[2] else 0

        # 交易对手数量评分
        if counterparty_count > 20:
            score = 80.0
            description = f"涉及{counterparty_count}个交易对手，业务复杂度高"
        elif counterparty_count > 10:
            score = 60.0
            description = f"涉及{counterparty_count}个交易对手，业务复杂度中等"
        elif counterparty_count > 5:
            score = 40.0
            description = f"涉及{counterparty_count}个交易对手，业务复杂度较低"
        else:
            score = 30.0
            description = f"涉及{counterparty_count}个交易对手，业务相对简单"

        # 金额波动性
        if max_amount > 0 and avg_amount > 0:
            volatility = max_amount / avg_amount
            if volatility > 100:
                score = min(100, score + 20)
                description += "，金额波动较大"

        factor = RiskFactor(
            name="业务复杂性",
            weight=self.weights["business_complexity"],
            score=score,
            description=description
        )

        return score, factor

    def _assess_historical_issues(
        self,
        subject_code: str,
        historical_issues: List[Dict[str, Any]] = None
    ) -> tuple:
        """评估历史问题"""
        score = 50.0
        description = "无历史问题记录"
        issues = historical_issues or []

        if issues:
            # 统计问题严重程度
            high_severity = len([i for i in issues if i.get("severity") == "high"])
            medium_severity = len([i for i in issues if i.get("severity") == "medium"])

            if high_severity > 0:
                score = 90.0
                description = f"存在{high_severity}个重大历史问题"
            elif medium_severity > 0:
                score = 70.0
                description = f"存在{medium_severity}个一般历史问题"
            else:
                score = 55.0
                description = f"存在{len(issues)}个轻微历史问题"

        # 科目固有风险
        prefix = subject_code[:4]
        if prefix in HIGH_RISK_SUBJECTS:
            score = min(100, score + 15)
            description += "，该科目属于高风险科目"
        elif prefix in ATTENTION_SUBJECTS:
            score = min(100, score + 8)
            description += "，该科目需特别关注"

        factor = RiskFactor(
            name="历史问题",
            weight=self.weights["historical_issues"],
            score=score,
            description=description
        )

        return score, factor

    def _assess_industry_risk(
        self,
        subject_code: str,
        industry_risks: List[str] = None
    ) -> tuple:
        """评估行业风险"""
        score = 50.0
        description = "行业风险一般"
        risks = industry_risks or []

        if risks:
            # 计算行业风险数量
            risk_count = len(risks)

            if risk_count > 3:
                score = 80.0
                description = f"行业存在{risk_count}项特定风险：{', '.join(risks[:3])}"
            elif risk_count > 1:
                score = 65.0
                description = f"行业存在{risk_count}项风险：{', '.join(risks)}"
            else:
                score = 55.0
                description = f"行业风险较低：{risks[0]}"

        factor = RiskFactor(
            name="行业风险",
            weight=self.weights["industry_risk"],
            score=score,
            description=description
        )

        return score, factor

    def _assess_anomaly_indicators(
        self,
        project_id: str,
        subject_code: str
    ) -> tuple:
        """评估异常指标"""
        score = 50.0
        description = "未发现明显异常"
        anomalies = []

        with get_db_cursor() as cursor:
            # 检查周末交易
            cursor.execute(
                """
                SELECT COUNT(*), SUM(amount)
                FROM vouchers
                WHERE project_id = ?
                  AND subject_code LIKE ?
                  AND strftime('%w', voucher_date) IN ('0', '6')
                  AND amount > 10000
                """,
                [project_id, f"{subject_code}%"]
            )
            weekend_row = cursor.fetchone()
            weekend_count = weekend_row[0] if weekend_row else 0

            if weekend_count > 0:
                anomalies.append(f"周末大额交易{weekend_count}笔")
                score = min(100, score + 15)

            # 检查月末集中交易
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM vouchers
                WHERE project_id = ?
                  AND subject_code LIKE ?
                  AND strftime('%d', voucher_date) >= '25'
                """,
                [project_id, f"{subject_code}%"]
            )
            month_end_count = cursor.fetchone()[0] or 0

            # 获取总交易笔数
            cursor.execute(
                """
                SELECT COUNT(*) FROM vouchers
                WHERE project_id = ? AND subject_code LIKE ?
                """,
                [project_id, f"{subject_code}%"]
            )
            total_count = cursor.fetchone()[0] or 1

            month_end_ratio = month_end_count / total_count if total_count > 0 else 0
            if month_end_ratio > 0.4:
                anomalies.append(f"月末交易集中度{month_end_ratio*100:.1f}%")
                score = min(100, score + 10)

            # 检查大额整数交易
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM vouchers
                WHERE project_id = ?
                  AND subject_code LIKE ?
                  AND amount > 10000
                  AND amount % 10000 = 0
                """,
                [project_id, f"{subject_code}%"]
            )
            round_amount_count = cursor.fetchone()[0] or 0

            if round_amount_count > 0:
                anomalies.append(f"大额整数交易{round_amount_count}笔")
                score = min(100, score + 8)

        if anomalies:
            description = "、".join(anomalies)

        factor = RiskFactor(
            name="异常指标",
            weight=self.weights["anomaly_indicators"],
            score=score,
            description=description
        )

        return score, factor

    def _determine_risk_level(self, score: float) -> RiskLevel:
        """确定风险等级"""
        if score >= 70:
            return RiskLevel.HIGH
        elif score >= 50:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _calculate_material_amount(self, project_id: str) -> float:
        """计算重要性水平"""
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM vouchers WHERE project_id = ?",
                [project_id]
            )
            total_amount = float(cursor.fetchone()[0]) or 0

        # 重要性水平通常为总资产的0.5%-1%
        return total_amount * 0.005

    def _generate_recommendation(
        self,
        risk_level: RiskLevel,
        score: float,
        risk_factors: List[RiskFactor]
    ) -> str:
        """生成抽样建议"""
        if risk_level == RiskLevel.HIGH:
            return f"该科目风险等级为【高】，风险评分{score:.1f}分。建议采用判断抽样，重点审查金额较大、时间异常的交易，抽样比例建议30%以上。"
        elif risk_level == RiskLevel.MEDIUM:
            return f"该科目风险等级为【中】，风险评分{score:.1f}分。建议采用分层抽样，按金额大小分层后分别抽样，抽样比例建议15%-30%。"
        else:
            return f"该科目风险等级为【低】，风险评分{score:.1f}分。建议采用随机抽样，抽样比例建议10%-15%。"

    def _get_subject_name(self, subject_code: str) -> str:
        """获取科目名称"""
        from app.services.classification_service import SUBJECT_CATEGORY_MAP
        prefix = subject_code[:4]
        return SUBJECT_CATEGORY_MAP.get(prefix, "未知科目")

    def save_profile(self, profile: RiskProfile) -> str:
        """保存风险画像到数据库"""
        with get_db_cursor() as cursor:
            # 删除旧记录
            cursor.execute(
                "DELETE FROM risk_profiles WHERE project_id = ? AND subject_code = ?",
                [profile.project_id, profile.subject_code]
            )

            # 插入新记录（包含risk_score）
            cursor.execute(
                """
                INSERT INTO risk_profiles
                (id, project_id, subject_code, subject_name, risk_level, risk_score,
                 risk_factors, material_amount, anomaly_score, recommendation, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    profile.id,
                    profile.project_id,
                    profile.subject_code,
                    profile.subject_name,
                    profile.risk_level.value,
                    profile.risk_score,  # 保存AI融合后的分数
                    json.dumps([{
                        "name": f.name,
                        "weight": f.weight,
                        "score": f.score,
                        "description": f.description
                    } for f in profile.risk_factors], ensure_ascii=False),
                    profile.material_amount,
                    profile.anomaly_score,
                    profile.recommendation,
                    profile.created_at
                ]
            )
            get_db().commit()

        return profile.id

    def get_profile(self, project_id: str, subject_code: str) -> Optional[RiskProfile]:
        """获取风险画像"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, project_id, subject_code, subject_name, risk_level, risk_score,
                       risk_factors, material_amount, anomaly_score, recommendation, created_at
                FROM risk_profiles
                WHERE project_id = ? AND subject_code = ?
                """,
                [project_id, subject_code]
            )
            row = cursor.fetchone()

            if not row:
                return None

            risk_factors_data = json.loads(row[6]) if isinstance(row[6], str) else row[6]
            risk_factors = [
                RiskFactor(
                    name=f["name"],
                    weight=f["weight"],
                    score=f["score"],
                    description=f["description"]
                )
                for f in risk_factors_data
            ]

            # 从数据库读取risk_score，如果没有则计算
            db_risk_score = float(row[5]) if row[5] is not None else None
            if db_risk_score is None:
                db_risk_score = sum(f.score * f.weight for f in risk_factors)

            return RiskProfile(
                id=row[0],
                project_id=row[1],
                subject_code=row[2],
                subject_name=row[3],
                risk_level=RiskLevel(row[4]),
                risk_score=db_risk_score,  # 使用数据库保存的分数
                risk_factors=risk_factors,
                material_amount=float(row[7]) if row[7] else 0,
                anomaly_score=float(row[8]) if row[8] else 0,
                historical_issues=[],
                recommendation=row[9],
                created_at=row[10]
            )

    def get_project_profiles(self, project_id: str) -> List[RiskProfile]:
        """获取项目所有风险画像"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, project_id, subject_code, subject_name, risk_level, risk_score,
                       risk_factors, material_amount, anomaly_score, recommendation, created_at
                FROM risk_profiles
                WHERE project_id = ?
                ORDER BY risk_score DESC, subject_code
                """,
                [project_id]
            )
            rows = cursor.fetchall()

        profiles = []
        for row in rows:
            risk_factors_data = json.loads(row[6]) if isinstance(row[6], str) else row[6]
            risk_factors = [
                RiskFactor(
                    name=f["name"],
                    weight=f["weight"],
                    score=f["score"],
                    description=f["description"]
                )
                for f in risk_factors_data
            ]

            # 从数据库读取risk_score，如果没有则计算
            db_risk_score = float(row[5]) if row[5] is not None else None
            if db_risk_score is None:
                db_risk_score = sum(f.score * f.weight for f in risk_factors)

            profiles.append(RiskProfile(
                id=row[0],
                project_id=row[1],
                subject_code=row[2],
                subject_name=row[3],
                risk_level=RiskLevel(row[4]),
                risk_score=db_risk_score,  # 使用数据库保存的分数
                risk_factors=risk_factors,
                material_amount=float(row[7]) if row[7] else 0,
                anomaly_score=float(row[8]) if row[8] else 0,
                historical_issues=[],
                recommendation=row[9],
                created_at=row[10]
            ))

        return profiles

    def generate_project_profiles(
        self,
        project_id: str,
        subject_codes: List[str] = None,
        use_ai: bool = True
    ) -> List[RiskProfile]:
        """
        生成项目所有科目的风险画像

        Args:
            project_id: 项目ID
            subject_codes: 指定科目代码列表
            use_ai: 是否使用AI增强分析

        Returns:
            List[RiskProfile]: 风险画像列表
        """
        # 获取项目科目列表
        if not subject_codes:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT DISTINCT subject_code, subject_name
                    FROM vouchers
                    WHERE project_id = ? AND subject_code IS NOT NULL
                    """,
                    [project_id]
                )
                subjects = [(row[0], row[1]) for row in cursor.fetchall()]
        else:
            subjects = [(code, None) for code in subject_codes]

        if not subjects:
            logger.warning(f"[风险画像] 项目 {project_id} 没有找到科目")
            return []

        profiles = []

        # 如果启用AI且有AI分析器，使用异步AI分析
        if use_ai and self.ai_analyzer:
            logger.info(f"[风险画像] 开始AI增强分析，共 {len(subjects)} 个科目")
            profiles = asyncio.run(self._generate_profiles_with_ai(project_id, subjects))
        else:
            # 使用规则引擎
            logger.info(f"[风险画像] 使用规则引擎分析，共 {len(subjects)} 个科目")
            for code, name in subjects:
                profile = self.generate(
                    project_id=project_id,
                    subject_code=code,
                    subject_name=name
                )
                profiles.append(profile)

        # 保存所有画像
        for profile in profiles:
            self.save_profile(profile)

        # 同时分析凭证风险（为交易风险清单提供数据）
        try:
            from app.services.voucher_risk_service import voucher_risk_service
            logger.info(f"[风险画像] 开始分析凭证风险...")
            # 使用同步方法调用（快速模式不使用AI，可以直接同步执行）
            results = asyncio.run(voucher_risk_service.batch_analyze_vouchers(project_id, use_ai=use_ai))
            logger.info(f"[风险画像] 凭证风险分析完成，共 {len(results)} 条")
        except RuntimeError as e:
            # 如果已经在事件循环中，创建新线程执行
            logger.warning(f"[风险画像] 异步调用冲突，使用线程池执行: {e}")
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    voucher_risk_service.batch_analyze_vouchers(project_id, use_ai=use_ai)
                )
                results = future.result(timeout=300)
            logger.info(f"[风险画像] 凭证风险分析完成，共 {len(results)} 条")
        except Exception as e:
            logger.error(f"[风险画像] 凭证风险分析失败: {e}", exc_info=True)

        logger.info(f"[风险画像] 完成，生成 {len(profiles)} 个科目画像")
        return profiles

    async def _generate_profiles_with_ai(
        self,
        project_id: str,
        subjects: List[tuple]
    ) -> List[RiskProfile]:
        """异步生成带AI分析的风险画像"""
        profiles = []

        # 并发处理，每批5个科目
        batch_size = 5
        for i in range(0, len(subjects), batch_size):
            batch = subjects[i:i + batch_size]
            tasks = [
                self.generate_with_ai(project_id, code, name)
                for code, name in batch
            ]
            batch_profiles = await asyncio.gather(*tasks, return_exceptions=True)

            for j, result in enumerate(batch_profiles):
                if isinstance(result, Exception):
                    logger.error(f"[风险画像] 科目 {batch[j][0]} 分析失败: {result}")
                    # 使用规则引擎结果作为备选
                    profile = self.generate(project_id, batch[j][0], batch[j][1])
                    profiles.append(profile)
                else:
                    profiles.append(result)

            logger.info(f"[风险画像] AI分析进度: {min(i + batch_size, len(subjects))}/{len(subjects)}")

        return profiles

    async def _generate_profiles_with_ai_from_api(
        self,
        project_id: str
    ) -> List[RiskProfile]:
        """
        专门供API调用的异步生成方法

        Args:
            project_id: 项目ID

        Returns:
            List[RiskProfile]: 风险画像列表
        """
        # 获取项目科目列表
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT subject_code, subject_name
                FROM vouchers
                WHERE project_id = ? AND subject_code IS NOT NULL
                """,
                [project_id]
            )
            subjects = [(row[0], row[1]) for row in cursor.fetchall()]

        if not subjects:
            return []

        logger.info(f"[风险画像-API] 开始AI增强分析，共 {len(subjects)} 个科目")

        # 使用异步方法生成画像
        profiles = await self._generate_profiles_with_ai(project_id, subjects)

        # 保存所有画像
        for profile in profiles:
            self.save_profile(profile)

        logger.info(f"[风险画像-API] 完成，生成 {len(profiles)} 个科目画像")

        # 同时分析凭证风险（为交易风险清单提供数据）
        await self._analyze_voucher_risks(project_id, use_ai=True)

        return profiles

    async def _analyze_voucher_risks(self, project_id: str, use_ai: bool = True):
        """分析凭证风险，填充交易风险清单数据"""
        try:
            from app.services.voucher_risk_service import voucher_risk_service
            logger.info(f"[风险画像-API] 开始分析凭证风险，use_ai={use_ai}...")
            results = await voucher_risk_service.batch_analyze_vouchers(project_id, use_ai=use_ai)
            logger.info(f"[风险画像-API] 凭证风险分析完成，共 {len(results)} 条")
        except Exception as e:
            logger.error(f"[风险画像-API] 凭证风险分析失败: {e}", exc_info=True)

    def generate_project_overview(self, project_id: str) -> ProjectRiskOverview:
        """
        生成项目整体风险概览

        Args:
            project_id: 项目ID

        Returns:
            ProjectRiskOverview: 项目风险概览
        """
        # 获取所有科目风险画像
        profiles = self.get_project_profiles(project_id)

        if not profiles:
            return ProjectRiskOverview(
                id=str(uuid.uuid4()),
                project_id=project_id,
                overall_risk_score=0,
                overall_risk_level="low",
                dimension_scores={},
                high_risk_subjects=[],
                risk_trend=[],
                generated_at=datetime.now()
            )

        # 计算整体风险分数（加权平均）
        total_amount = sum(p.material_amount for p in profiles)
        if total_amount > 0:
            overall_score = sum(
                p.risk_score * (p.material_amount / total_amount)
                for p in profiles
            )
        else:
            overall_score = sum(p.risk_score for p in profiles) / len(profiles)

        # 确定整体风险等级
        if overall_score >= 70:
            overall_level = "high"
        elif overall_score >= 50:
            overall_level = "medium"
        else:
            overall_level = "low"

        # 计算各维度平均分数
        dimension_scores = {}
        dimension_names = ["金额重要性", "业务复杂性", "历史问题", "行业风险", "异常指标"]
        for dim_name in dimension_names:
            scores = []
            for p in profiles:
                for f in p.risk_factors:
                    if f.name == dim_name:
                        scores.append(f.score)
                        break
            dimension_scores[dim_name] = sum(scores) / len(scores) if scores else 50

        # 获取高风险科目TOP5
        sorted_profiles = sorted(profiles, key=lambda p: p.risk_score, reverse=True)
        high_risk_subjects = [
            {
                "subject_code": p.subject_code,
                "subject_name": p.subject_name,
                "risk_score": p.risk_score,
                "risk_level": p.risk_level.value
            }
            for p in sorted_profiles[:5]
        ]

        # 获取风险趋势（最近6个快照）
        risk_trend = self._get_risk_trend(project_id)

        overview = ProjectRiskOverview(
            id=str(uuid.uuid4()),
            project_id=project_id,
            overall_risk_score=round(overall_score, 2),
            overall_risk_level=overall_level,
            dimension_scores=dimension_scores,
            high_risk_subjects=high_risk_subjects,
            risk_trend=risk_trend,
            generated_at=datetime.now()
        )

        # 保存到数据库
        self._save_project_overview(overview)

        return overview

    def _save_project_overview(self, overview: ProjectRiskOverview):
        """保存项目风险概览"""
        with get_db_cursor() as cursor:
            # 删除旧记录
            cursor.execute(
                "DELETE FROM project_risk_overview WHERE project_id = ?",
                [overview.project_id]
            )
            # 插入新记录
            cursor.execute(
                """
                INSERT INTO project_risk_overview
                (id, project_id, overall_risk_score, overall_risk_level,
                 dimension_scores, high_risk_subjects, risk_trend, generated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    overview.id,
                    overview.project_id,
                    overview.overall_risk_score,
                    overview.overall_risk_level,
                    json.dumps(overview.dimension_scores, ensure_ascii=False),
                    json.dumps(overview.high_risk_subjects, ensure_ascii=False),
                    json.dumps(overview.risk_trend, ensure_ascii=False),
                    overview.generated_at
                ]
            )
            get_db().commit()

    def get_project_overview(self, project_id: str) -> Optional[ProjectRiskOverview]:
        """获取项目风险概览"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, project_id, overall_risk_score, overall_risk_level,
                       dimension_scores, high_risk_subjects, risk_trend, generated_at
                FROM project_risk_overview
                WHERE project_id = ?
                """,
                [project_id]
            )
            row = cursor.fetchone()

            if not row:
                return None

            return ProjectRiskOverview(
                id=row[0],
                project_id=row[1],
                overall_risk_score=float(row[2]) if row[2] else 0,
                overall_risk_level=row[3] or "low",
                dimension_scores=json.loads(row[4]) if isinstance(row[4], str) else row[4] or {},
                high_risk_subjects=json.loads(row[5]) if isinstance(row[5], str) else row[5] or [],
                risk_trend=json.loads(row[6]) if isinstance(row[6], str) else row[6] or [],
                generated_at=row[7]
            )

    def _get_risk_trend(self, project_id: str, periods: int = 6) -> List[Dict[str, Any]]:
        """获取风险趋势"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT snapshot_date, risk_score, risk_level
                FROM risk_history
                WHERE project_id = ?
                ORDER BY snapshot_date DESC
                LIMIT ?
                """,
                [project_id, periods]
            )
            rows = cursor.fetchall()

            return [
                {
                    "date": str(row[0]) if row[0] else None,
                    "score": float(row[1]) if row[1] else 0,
                    "level": row[2]
                }
                for row in reversed(rows)
            ]

    def assess_counterparty_risk(self, project_id: str) -> List[CounterpartyRisk]:
        """
        评估交易对手风险

        Args:
            project_id: 项目ID

        Returns:
            List[CounterpartyRisk]: 交易对手风险列表
        """
        with get_db_cursor() as cursor:
            # 获取项目总金额
            cursor.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM vouchers WHERE project_id = ?",
                [project_id]
            )
            total_amount = float(cursor.fetchone()[0]) or 1

            # 按交易对手统计
            cursor.execute(
                """
                SELECT counterparty,
                       SUM(amount) as total_amount,
                       COUNT(*) as transaction_count,
                       MIN(voucher_date) as first_date,
                       MAX(voucher_date) as last_date
                FROM vouchers
                WHERE project_id = ? AND counterparty IS NOT NULL AND counterparty != ''
                GROUP BY counterparty
                ORDER BY total_amount DESC
                """,
                [project_id]
            )
            rows = cursor.fetchall()

        results = []
        for row in rows:
            counterparty = row[0]
            amount = float(row[1]) if row[1] else 0
            count = row[2] or 0
            concentration = amount / total_amount if total_amount > 0 else 0

            # 判断是否关联方
            is_related_party = self._check_related_party(counterparty)

            # 判断是否新客户（首次交易在近3个月）
            is_new_customer = self._check_new_customer(row[3])

            # 计算风险分数
            risk_score, risk_factors = self._calculate_counterparty_risk_score(
                amount, concentration, count, is_related_party, is_new_customer
            )

            # 确定风险等级
            if risk_score >= 70:
                risk_level = "high"
            elif risk_score >= 50:
                risk_level = "medium"
            else:
                risk_level = "low"

            results.append(CounterpartyRisk(
                id=str(uuid.uuid4()),
                project_id=project_id,
                counterparty_name=counterparty,
                total_amount=amount,
                transaction_count=count,
                concentration_ratio=round(concentration, 4),
                is_related_party=is_related_party,
                is_new_customer=is_new_customer,
                risk_score=round(risk_score, 2),
                risk_level=risk_level,
                risk_factors=risk_factors
            ))

        # 保存结果
        self._save_counterparty_risks(project_id, results)

        return results

    def _check_related_party(self, counterparty: str) -> bool:
        """检查是否关联方"""
        if not counterparty:
            return False
        related_keywords = ['关联', '股东', '子公司', '母公司', '兄弟公司', '联营', '合营', '同一控制']
        return any(kw in counterparty for kw in related_keywords)

    def _check_new_customer(self, first_date) -> bool:
        """检查是否新客户"""
        if not first_date:
            return False
        from datetime import timedelta
        try:
            if isinstance(first_date, str):
                first_date = datetime.strptime(first_date[:10], '%Y-%m-%d').date()
            three_months_ago = datetime.now().date() - timedelta(days=90)
            return first_date >= three_months_ago
        except:
            return False

    def _calculate_counterparty_risk_score(
        self,
        amount: float,
        concentration: float,
        count: int,
        is_related_party: bool,
        is_new_customer: bool
    ) -> tuple:
        """计算交易对手风险分数"""
        score = 30.0
        factors = []

        if is_related_party:
            score += 35
            factors.append("关联方交易")

        if is_new_customer:
            score += 15
            factors.append("新客户/供应商")

        if concentration > 0.2:
            score += 25
            factors.append(f"高集中度({concentration*100:.1f}%)")
        elif concentration > 0.1:
            score += 15
            factors.append(f"中等集中度({concentration*100:.1f}%)")

        if amount > 500000:
            score += 20
            factors.append("超大额交易")
        elif amount > 100000:
            score += 10
            factors.append("大额交易")

        if count > 50:
            score += 10
            factors.append("频繁交易")

        if not factors:
            factors.append("常规交易对手")

        return min(score, 100), factors

    def _save_counterparty_risks(self, project_id: str, risks: List[CounterpartyRisk]):
        """保存交易对手风险分析结果"""
        with get_db_cursor() as cursor:
            # 删除旧记录
            cursor.execute(
                "DELETE FROM counterparty_risk WHERE project_id = ?",
                [project_id]
            )
            # 插入新记录
            for r in risks:
                cursor.execute(
                    """
                    INSERT INTO counterparty_risk
                    (id, project_id, counterparty_name, total_amount, transaction_count,
                     concentration_ratio, is_related_party, is_new_customer, risk_score,
                     risk_level, risk_factors)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        r.id, r.project_id, r.counterparty_name, r.total_amount,
                        r.transaction_count, r.concentration_ratio, r.is_related_party,
                        r.is_new_customer, r.risk_score, r.risk_level,
                        json.dumps(r.risk_factors, ensure_ascii=False)
                    ]
                )
            get_db().commit()

    def get_counterparty_risks(self, project_id: str) -> List[CounterpartyRisk]:
        """获取交易对手风险分析结果"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, project_id, counterparty_name, total_amount, transaction_count,
                       concentration_ratio, is_related_party, is_new_customer, risk_score,
                       risk_level, risk_factors
                FROM counterparty_risk
                WHERE project_id = ?
                ORDER BY risk_score DESC
                """,
                [project_id]
            )
            rows = cursor.fetchall()

            return [
                CounterpartyRisk(
                    id=row[0],
                    project_id=row[1],
                    counterparty_name=row[2],
                    total_amount=float(row[3]) if row[3] else 0,
                    transaction_count=row[4] or 0,
                    concentration_ratio=float(row[5]) if row[5] else 0,
                    is_related_party=bool(row[6]),
                    is_new_customer=bool(row[7]),
                    risk_score=float(row[8]) if row[8] else 0,
                    risk_level=row[9] or "low",
                    risk_factors=json.loads(row[10]) if isinstance(row[10], str) else row[10] or []
                )
                for row in rows
            ]

    def assess_time_risk(self, project_id: str, period_type: str = "monthly") -> List[TimeRiskAnalysis]:
        """
        评估时间维度风险

        Args:
            project_id: 项目ID
            period_type: 周期类型 monthly/quarterly

        Returns:
            List[TimeRiskAnalysis]: 时间维度风险分析结果
        """
        with get_db_cursor() as cursor:
            if period_type == "quarterly":
                period_expr = "strftime('%Y-Q', voucher_date || '-' || cast((cast(strftime('%m', voucher_date) as integer) - 1) / 3 + 1 as varchar))"
            else:
                period_expr = "strftime('%Y-%m', voucher_date)"

            cursor.execute(
                f"""
                SELECT {period_expr} as period,
                       SUM(amount) as total_amount,
                       COUNT(*) as transaction_count
                FROM vouchers
                WHERE project_id = ? AND voucher_date IS NOT NULL
                GROUP BY {period_expr}
                ORDER BY period
                """,
                [project_id]
            )
            rows = cursor.fetchall()

        results = []
        amounts = [float(row[1]) if row[1] else 0 for row in rows]

        # 计算波动性
        avg_amount = sum(amounts) / len(amounts) if amounts else 1
        for i, row in enumerate(rows):
            period = row[0]
            amount = float(row[1]) if row[1] else 0
            count = row[2] or 0

            # 计算波动分数
            if avg_amount > 0:
                volatility = abs(amount - avg_amount) / avg_amount * 100
            else:
                volatility = 0
            volatility_score = min(volatility, 100)

            # 计算期末集中度
            period_end_concentration = self._calculate_period_end_concentration(
                project_id, period
            )

            # 识别异常指标
            anomaly_indicators = []
            if volatility_score > 50:
                anomaly_indicators.append(f"金额波动较大({volatility_score:.1f}%)")
            if period_end_concentration > 0.4:
                anomaly_indicators.append(f"期末集中度高({period_end_concentration*100:.1f}%)")

            results.append(TimeRiskAnalysis(
                id=str(uuid.uuid4()),
                project_id=project_id,
                period=period,
                period_type=period_type,
                total_amount=amount,
                transaction_count=count,
                volatility_score=round(volatility_score, 2),
                period_end_concentration=round(period_end_concentration, 4),
                anomaly_indicators=anomaly_indicators
            ))

        # 保存结果
        self._save_time_risk_analysis(project_id, results)

        return results

    def _calculate_period_end_concentration(self, project_id: str, period: str) -> float:
        """计算期末交易集中度"""
        with get_db_cursor() as cursor:
            # 获取该期总交易数
            cursor.execute(
                """
                SELECT COUNT(*) FROM vouchers
                WHERE project_id = ? AND strftime('%Y-%m', voucher_date) = ?
                """,
                [project_id, period]
            )
            total_count = cursor.fetchone()[0] or 1

            # 获取期末（最后5天）交易数
            cursor.execute(
                """
                SELECT COUNT(*) FROM vouchers
                WHERE project_id = ?
                  AND strftime('%Y-%m', voucher_date) = ?
                  AND cast(strftime('%d', voucher_date) as integer) >= 26
                """,
                [project_id, period]
            )
            period_end_count = cursor.fetchone()[0] or 0

        return period_end_count / total_count if total_count > 0 else 0

    def _save_time_risk_analysis(self, project_id: str, analyses: List[TimeRiskAnalysis]):
        """保存时间维度风险分析"""
        with get_db_cursor() as cursor:
            cursor.execute(
                "DELETE FROM time_risk_analysis WHERE project_id = ?",
                [project_id]
            )
            for a in analyses:
                cursor.execute(
                    """
                    INSERT INTO time_risk_analysis
                    (id, project_id, period, period_type, total_amount, transaction_count,
                     volatility_score, period_end_concentration, anomaly_indicators)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        a.id, a.project_id, a.period, a.period_type, a.total_amount,
                        a.transaction_count, a.volatility_score, a.period_end_concentration,
                        json.dumps(a.anomaly_indicators, ensure_ascii=False)
                    ]
                )
            get_db().commit()

    def get_time_risk_analysis(self, project_id: str) -> List[TimeRiskAnalysis]:
        """获取时间维度风险分析结果"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, project_id, period, period_type, total_amount, transaction_count,
                       volatility_score, period_end_concentration, anomaly_indicators
                FROM time_risk_analysis
                WHERE project_id = ?
                ORDER BY period
                """,
                [project_id]
            )
            rows = cursor.fetchall()

            return [
                TimeRiskAnalysis(
                    id=row[0],
                    project_id=row[1],
                    period=row[2],
                    period_type=row[3],
                    total_amount=float(row[4]) if row[4] else 0,
                    transaction_count=row[5] or 0,
                    volatility_score=float(row[6]) if row[6] else 0,
                    period_end_concentration=float(row[7]) if row[7] else 0,
                    anomaly_indicators=json.loads(row[8]) if isinstance(row[8], str) else row[8] or []
                )
                for row in rows
            ]

    def generate_voucher_risk_tags(
        self,
        voucher: Dict[str, Any]
    ) -> List[VoucherRiskTag]:
        """
        生成凭证风险标签

        Args:
            voucher: 凭证数据

        Returns:
            List[VoucherRiskTag]: 风险标签列表
        """
        tags = []

        # 金额类检查
        amount = voucher.get('amount', 0) or 0
        if amount > 500000:
            tags.append(VoucherRiskTag(
                tag_code="SUPER_LARGE_AMOUNT",
                **STANDARD_RISK_TAGS["SUPER_LARGE_AMOUNT"],
                details={"amount": amount}
            ))
        elif amount > 100000:
            tags.append(VoucherRiskTag(
                tag_code="LARGE_AMOUNT",
                **STANDARD_RISK_TAGS["LARGE_AMOUNT"],
                details={"amount": amount}
            ))

        if amount >= 10000 and amount % 10000 == 0:
            tags.append(VoucherRiskTag(
                tag_code="ROUND_AMOUNT",
                **STANDARD_RISK_TAGS["ROUND_AMOUNT"],
                details={"amount": amount}
            ))

        # 时间类检查
        voucher_date = voucher.get('voucher_date')
        if voucher_date:
            try:
                if isinstance(voucher_date, str):
                    from datetime import datetime as dt
                    date_obj = dt.strptime(voucher_date[:10], '%Y-%m-%d')
                else:
                    date_obj = voucher_date

                if date_obj.weekday() >= 5:  # 周末
                    tags.append(VoucherRiskTag(
                        tag_code="WEEKEND_TRANSACTION",
                        **STANDARD_RISK_TAGS["WEEKEND_TRANSACTION"],
                        details={"date": str(voucher_date)}
                    ))

                if date_obj.day >= 26:  # 月末
                    tags.append(VoucherRiskTag(
                        tag_code="MONTH_END_CONCENTRATION",
                        **STANDARD_RISK_TAGS["MONTH_END_CONCENTRATION"],
                        details={"date": str(voucher_date)}
                    ))

                if date_obj.month == 12 and date_obj.day >= 25:  # 年末
                    tags.append(VoucherRiskTag(
                        tag_code="YEAR_END_TRANSACTION",
                        **STANDARD_RISK_TAGS["YEAR_END_TRANSACTION"],
                        details={"date": str(voucher_date)}
                    ))

                if date_obj.day <= 3:  # 月初
                    tags.append(VoucherRiskTag(
                        tag_code="PERIOD_START_TRANSACTION",
                        **STANDARD_RISK_TAGS["PERIOD_START_TRANSACTION"],
                        details={"date": str(voucher_date)}
                    ))
            except:
                pass

        # 交易对手类检查
        counterparty = voucher.get('counterparty', '')
        if counterparty:
            if self._check_related_party(counterparty):
                tags.append(VoucherRiskTag(
                    tag_code="RELATED_PARTY",
                    **STANDARD_RISK_TAGS["RELATED_PARTY"],
                    details={"counterparty": counterparty}
                ))

            if len(counterparty) <= 3 or '个人' in counterparty:
                tags.append(VoucherRiskTag(
                    tag_code="PERSONAL_TRANSACTION",
                    **STANDARD_RISK_TAGS["PERSONAL_TRANSACTION"],
                    details={"counterparty": counterparty}
                ))

        # 摘要类检查
        description = voucher.get('description', '')
        if description:
            sensitive_words = ['调整', '冲销', '暂估', '补记', '更正', '结转', '待摊', '预提', '挂账', '清理']
            found_words = [w for w in sensitive_words if w in description]
            if found_words:
                tags.append(VoucherRiskTag(
                    tag_code="SENSITIVE_KEYWORD",
                    **STANDARD_RISK_TAGS["SENSITIVE_KEYWORD"],
                    details={"keywords": found_words}
                ))

            if len(description) < 8:
                tags.append(VoucherRiskTag(
                    tag_code="VAGUE_DESCRIPTION",
                    **STANDARD_RISK_TAGS["VAGUE_DESCRIPTION"],
                    details={"description": description}
                ))
        elif amount > 50000:
            tags.append(VoucherRiskTag(
                tag_code="VAGUE_DESCRIPTION",
                **STANDARD_RISK_TAGS["VAGUE_DESCRIPTION"],
                details={"description": "缺失"}
            ))

        # 科目类检查
        subject_name = voucher.get('subject_name', '')
        subject_code = voucher.get('subject_code', '') or ''
        prefix = subject_code[:4]

        if prefix in HIGH_RISK_SUBJECTS:
            tags.append(VoucherRiskTag(
                tag_code="HIGH_RISK_SUBJECT",
                **STANDARD_RISK_TAGS["HIGH_RISK_SUBJECT"],
                details={"subject_code": subject_code, "subject_name": subject_name}
            ))
        elif prefix in ATTENTION_SUBJECTS:
            tags.append(VoucherRiskTag(
                tag_code="ATTENTION_SUBJECT",
                **STANDARD_RISK_TAGS["ATTENTION_SUBJECT"],
                details={"subject_code": subject_code, "subject_name": subject_name}
            ))

        return tags

    def calculate_layered_sample_size(
        self,
        project_id: str,
        high_ratio: float = 1.0,
        medium_ratio: float = 0.3,
        low_ratio: float = 0.05
    ) -> Dict[str, Any]:
        """
        计算分层抽样样本量

        基于凭证自身的风险等级进行统计，与交易风险清单保持一致。

        Args:
            project_id: 项目ID
            high_ratio: 高风险抽样比例（默认100%）
            medium_ratio: 中风险抽样比例（默认30%）
            low_ratio: 低风险抽样比例（默认5%）

        Returns:
            Dict: 分层抽样建议
        """
        layers = {
            "high": {"count": 0, "amount": 0, "sample_size": 0, "ratio": high_ratio},
            "medium": {"count": 0, "amount": 0, "sample_size": 0, "ratio": medium_ratio},
            "low": {"count": 0, "amount": 0, "sample_size": 0, "ratio": low_ratio}
        }

        # 直接从凭证表按风险等级统计（与交易风险清单一致）
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT risk_level, COUNT(*), COALESCE(SUM(amount), 0)
                FROM vouchers
                WHERE project_id = ?
                GROUP BY risk_level
                """,
                [project_id]
            )
            rows = cursor.fetchall()

            for row in rows:
                level = row[0] or "low"
                if level in layers:
                    layers[level]["count"] = row[1] or 0
                    layers[level]["amount"] = float(row[2]) if row[2] else 0

        # 计算各层样本量
        total_sample_size = 0
        for level in layers:
            count = layers[level]["count"]
            ratio = layers[level]["ratio"]
            if count > 0:
                # 至少抽取1笔，但不超过该层总数
                sample_size = max(1, int(count * ratio))
                sample_size = min(sample_size, count)
            else:
                sample_size = 0
            layers[level]["sample_size"] = sample_size
            total_sample_size += sample_size

        # 将layers对象转换为数组格式（前端期望的格式）
        layers_list = [
            {"level": "high", **layers["high"]},
            {"level": "medium", **layers["medium"]},
            {"level": "low", **layers["low"]}
        ]

        return {
            "layers": layers_list,
            "total_sample_size": total_sample_size,
            "recommendation": self._generate_layered_recommendation(layers)
        }

    def _generate_layered_recommendation(self, layers: Dict) -> str:
        """生成分层抽样建议"""
        rec = []
        if layers["high"]["count"] > 0:
            rec.append(f"高风险凭证{layers['high']['count']}笔，建议100%检查")
        if layers["medium"]["count"] > 0:
            rec.append(f"中风险凭证{layers['medium']['count']}笔，建议抽取{layers['medium']['sample_size']}笔（30%）")
        if layers["low"]["count"] > 0:
            rec.append(f"低风险凭证{layers['low']['count']}笔，建议抽取{layers['low']['sample_size']}笔（5%）")
        rec.append(f"合计抽样{layers['high']['sample_size'] + layers['medium']['sample_size'] + layers['low']['sample_size']}笔")
        return "；".join(rec)


# 全局服务实例
risk_profile_generator = RiskProfileGenerator()