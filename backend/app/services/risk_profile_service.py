"""
风险画像生成服务
基于财报数据、科目属性、历史问题自动评估科目风险等级
"""
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from app.core.database import get_db_cursor, get_db


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
    """风险画像生成器"""

    def __init__(self):
        self.weights = RISK_WEIGHTS

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

            # 插入新记录
            cursor.execute(
                """
                INSERT INTO risk_profiles
                (id, project_id, subject_code, subject_name, risk_level,
                 risk_factors, material_amount, anomaly_score, recommendation, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    profile.id,
                    profile.project_id,
                    profile.subject_code,
                    profile.subject_name,
                    profile.risk_level.value,
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
                SELECT id, project_id, subject_code, subject_name, risk_level,
                       risk_factors, material_amount, anomaly_score, recommendation, created_at
                FROM risk_profiles
                WHERE project_id = ? AND subject_code = ?
                """,
                [project_id, subject_code]
            )
            row = cursor.fetchone()

            if not row:
                return None

            risk_factors_data = json.loads(row[5]) if isinstance(row[5], str) else row[5]
            risk_factors = [
                RiskFactor(
                    name=f["name"],
                    weight=f["weight"],
                    score=f["score"],
                    description=f["description"]
                )
                for f in risk_factors_data
            ]

            return RiskProfile(
                id=row[0],
                project_id=row[1],
                subject_code=row[2],
                subject_name=row[3],
                risk_level=RiskLevel(row[4]),
                risk_score=sum(f.score * f.weight for f in risk_factors),
                risk_factors=risk_factors,
                material_amount=float(row[6]) if row[6] else 0,
                anomaly_score=float(row[7]) if row[7] else 0,
                historical_issues=[],
                recommendation=row[8],
                created_at=row[9]
            )

    def get_project_profiles(self, project_id: str) -> List[RiskProfile]:
        """获取项目所有风险画像"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, project_id, subject_code, subject_name, risk_level,
                       risk_factors, material_amount, anomaly_score, recommendation, created_at
                FROM risk_profiles
                WHERE project_id = ?
                ORDER BY risk_level, subject_code
                """,
                [project_id]
            )
            rows = cursor.fetchall()

        profiles = []
        for row in rows:
            risk_factors_data = json.loads(row[5]) if isinstance(row[5], str) else row[5]
            risk_factors = [
                RiskFactor(
                    name=f["name"],
                    weight=f["weight"],
                    score=f["score"],
                    description=f["description"]
                )
                for f in risk_factors_data
            ]

            profiles.append(RiskProfile(
                id=row[0],
                project_id=row[1],
                subject_code=row[2],
                subject_name=row[3],
                risk_level=RiskLevel(row[4]),
                risk_score=sum(f.score * f.weight for f in risk_factors),
                risk_factors=risk_factors,
                material_amount=float(row[6]) if row[6] else 0,
                anomaly_score=float(row[7]) if row[7] else 0,
                historical_issues=[],
                recommendation=row[8],
                created_at=row[9]
            ))

        return profiles

    def generate_project_profiles(
        self,
        project_id: str,
        subject_codes: List[str] = None
    ) -> List[RiskProfile]:
        """生成项目所有科目的风险画像"""
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

        profiles = []
        for code, name in subjects:
            profile = self.generate(
                project_id=project_id,
                subject_code=code,
                subject_name=name
            )
            self.save_profile(profile)
            profiles.append(profile)

        return profiles


# 全局服务实例
risk_profile_generator = RiskProfileGenerator()