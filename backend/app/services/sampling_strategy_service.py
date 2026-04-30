"""
抽样策略推荐服务
根据风险等级推荐统计抽样或判断抽样方法、样本量及抽样依据
"""
import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from app.core.database import get_db_cursor
from app.services.risk_profile_service import RiskProfile, RiskLevel, risk_profile_generator


class SamplingMethod(str, Enum):
    """抽样方法"""
    RANDOM = "random"                    # 随机抽样
    STRATIFIED = "stratified"            # 分层抽样
    SYSTEMATIC = "systematic"            # 系统抽样
    JUDGMENT = "judgment"                # 判断抽样
    MONETARY_UNIT = "monetary_unit"      # 货币单位抽样


@dataclass
class SamplingStrategy:
    """抽样策略"""
    method: SamplingMethod
    sample_size: int
    confidence_level: float
    tolerable_error: float
    expected_error: float
    rationale: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StratificationLayer:
    """分层"""
    name: str
    min_amount: float
    max_amount: float
    count: int
    sample_size: int
    method: SamplingMethod


@dataclass
class SamplingRecommendation:
    """抽样推荐结果"""
    project_id: str
    subject_code: str
    subject_name: str
    risk_level: RiskLevel
    risk_score: float
    strategy: SamplingStrategy
    stratification: List[StratificationLayer] = field(default_factory=list)
    total_population: int = 0
    total_sample: int = 0
    sampling_rate: float = 0.0
    key_focus_areas: List[str] = field(default_factory=list)


# Z值表（置信水平对应）
Z_VALUES = {
    0.90: 1.645,
    0.95: 1.96,
    0.99: 2.576
}

# 预期偏差率表
EXPECTED_ERROR_RATES = {
    RiskLevel.HIGH: 0.05,
    RiskLevel.MEDIUM: 0.03,
    RiskLevel.LOW: 0.01
}

# 可容忍误差率表
TOLERABLE_ERROR_RATES = {
    RiskLevel.HIGH: 0.05,
    RiskLevel.MEDIUM: 0.08,
    RiskLevel.LOW: 0.10
}


class SamplingStrategyRecommender:
    """抽样策略推荐器"""

    def __init__(self):
        self.z_values = Z_VALUES
        self.expected_error_rates = EXPECTED_ERROR_RATES
        self.tolerable_error_rates = TOLERABLE_ERROR_RATES

    def recommend(
        self,
        risk_profile: RiskProfile,
        confidence_level: float = 0.95,
        tolerable_error: float = None,
        expected_error: float = None
    ) -> SamplingRecommendation:
        """
        根据风险画像推荐抽样策略

        Args:
            risk_profile: 风险画像
            confidence_level: 置信水平 (0.90, 0.95, 0.99)
            tolerable_error: 可容忍误差率
            expected_error: 预期偏差率

        Returns:
            SamplingRecommendation: 抽样推荐结果
        """
        # 获取总体信息
        population_info = self._get_population_info(
            risk_profile.project_id,
            risk_profile.subject_code
        )

        # 根据风险等级确定默认参数
        if tolerable_error is None:
            tolerable_error = self.tolerable_error_rates.get(risk_profile.risk_level, 0.08)

        if expected_error is None:
            expected_error = self.expected_error_rates.get(risk_profile.risk_level, 0.03)

        # 根据风险等级选择抽样方法
        if risk_profile.risk_level == RiskLevel.HIGH:
            strategy = self._recommend_judgment_sampling(
                risk_profile, population_info, confidence_level
            )
            stratification = []

        elif risk_profile.risk_level == RiskLevel.MEDIUM:
            strategy, stratification = self._recommend_stratified_sampling(
                risk_profile, population_info, confidence_level, tolerable_error, expected_error
            )

        else:  # LOW risk
            strategy = self._recommend_statistical_sampling(
                risk_profile, population_info, confidence_level, tolerable_error, expected_error
            )
            stratification = []

        # 计算抽样比例
        sampling_rate = strategy.sample_size / population_info["count"] if population_info["count"] > 0 else 0

        # 确定重点关注领域
        key_focus_areas = self._identify_focus_areas(risk_profile)

        return SamplingRecommendation(
            project_id=risk_profile.project_id,
            subject_code=risk_profile.subject_code,
            subject_name=risk_profile.subject_name,
            risk_level=risk_profile.risk_level,
            risk_score=risk_profile.risk_score,
            strategy=strategy,
            stratification=stratification,
            total_population=population_info["count"],
            total_sample=strategy.sample_size,
            sampling_rate=sampling_rate,
            key_focus_areas=key_focus_areas
        )

    def _get_population_info(self, project_id: str, subject_code: str) -> Dict[str, Any]:
        """获取总体信息"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) as count,
                    COALESCE(SUM(amount), 0) as total_amount,
                    COALESCE(AVG(amount), 0) as avg_amount,
                    COALESCE(MIN(amount), 0) as min_amount,
                    COALESCE(MAX(amount), 0) as max_amount
                FROM vouchers
                WHERE project_id = ? AND subject_code LIKE ?
                """,
                [project_id, f"{subject_code}%"]
            )
            row = cursor.fetchone()

            return {
                "count": row[0] or 0,
                "total_amount": float(row[1]) if row[1] else 0,
                "avg_amount": float(row[2]) if row[2] else 0,
                "min_amount": float(row[3]) if row[3] else 0,
                "max_amount": float(row[4]) if row[4] else 0
            }

    def _recommend_judgment_sampling(
        self,
        risk_profile: RiskProfile,
        population_info: Dict[str, Any],
        confidence_level: float
    ) -> SamplingStrategy:
        """推荐判断抽样策略"""
        population_count = population_info["count"]

        # 高风险科目，重点抽样
        # 金额大于重要性水平的全部检查
        # 其余按风险因素抽样

        with get_db_cursor() as cursor:
            # 金额大于重要性水平的凭证数量
            cursor.execute(
                """
                SELECT COUNT(*) FROM vouchers
                WHERE project_id = ?
                  AND subject_code LIKE ?
                  AND amount >= ?
                """,
                [risk_profile.project_id, f"{risk_profile.subject_code}%", risk_profile.material_amount]
            )
            material_count = cursor.fetchone()[0] or 0

        # 基础样本量：高风险科目抽样30%，但不低于总体规模的一定比例
        base_sample = int(population_count * 0.3)
        base_sample = max(1, min(base_sample, population_count))

        # 加上金额重要的凭证，但不超过总体规模
        total_sample = min(population_count, base_sample + material_count)

        return SamplingStrategy(
            method=SamplingMethod.JUDGMENT,
            sample_size=total_sample,
            confidence_level=confidence_level,
            tolerable_error=0.05,
            expected_error=0.05,
            rationale=f"该科目风险等级为【高】，建议采用判断抽样。"
                     f"重点检查金额超过{risk_profile.material_amount:,.2f}元的{material_count}笔凭证，"
                     f"并抽取其他凭证{base_sample}笔，总计{total_sample}笔。",
            parameters={
                "material_amount_threshold": risk_profile.material_amount,
                "material_voucher_count": material_count,
                "risk_factors": [f.description for f in risk_profile.risk_factors]
            }
        )

    def _recommend_stratified_sampling(
        self,
        risk_profile: RiskProfile,
        population_info: Dict[str, Any],
        confidence_level: float,
        tolerable_error: float,
        expected_error: float
    ) -> tuple:
        """推荐分层抽样策略"""
        # 金额分层
        layers = self._create_amount_strata(
            risk_profile.project_id,
            risk_profile.subject_code,
            population_info
        )

        # 对每层计算样本量
        total_sample = 0
        z = self.z_values.get(confidence_level, 1.96)
        p = expected_error
        e = tolerable_error

        for layer in layers:
            # 使用统计公式计算每层样本量
            n = self._calculate_sample_size(layer.count, z, p, e)

            # 中风险分层抽样比例调整
            if layer.name == "大额层":
                n = min(layer.count, max(n, int(layer.count * 0.5)))  # 大额层抽样50%
            elif layer.name == "中额层":
                n = min(layer.count, max(n, int(layer.count * 0.25)))  # 中额层抽样25%
            else:
                n = min(layer.count, max(n, int(layer.count * 0.1)))   # 小额层抽样10%

            layer.sample_size = n
            total_sample += n

        strategy = SamplingStrategy(
            method=SamplingMethod.STRATIFIED,
            sample_size=total_sample,
            confidence_level=confidence_level,
            tolerable_error=tolerable_error,
            expected_error=expected_error,
            rationale=f"该科目风险等级为【中】，建议采用分层抽样。"
                     f"按金额分为{len(layers)}层，大额层抽样50%，中额层抽样25%，小额层抽样10%，总计{total_sample}笔。",
            parameters={
                "strata_count": len(layers),
                "layer_details": [
                    {
                        "name": l.name,
                        "range": f"{l.min_amount:,.0f}-{l.max_amount:,.0f}",
                        "count": l.count,
                        "sample_size": l.sample_size
                    }
                    for l in layers
                ]
            }
        )

        return strategy, layers

    def _recommend_statistical_sampling(
        self,
        risk_profile: RiskProfile,
        population_info: Dict[str, Any],
        confidence_level: float,
        tolerable_error: float,
        expected_error: float
    ) -> SamplingStrategy:
        """推荐统计抽样策略"""
        population_count = population_info["count"]
        z = self.z_values.get(confidence_level, 1.96)
        p = expected_error
        e = tolerable_error

        # 使用标准统计公式计算样本量
        n = self._calculate_sample_size(population_count, z, p, e)

        # 低风险科目抽样比例限制在10%-15%，但不能超过总体规模
        min_sample = max(1, int(population_count * 0.10))
        max_sample = min(population_count, int(population_count * 0.15))
        max_sample = max(min_sample, max_sample)  # 确保max_sample >= min_sample
        n = min(population_count, max(min_sample, min(n, max_sample)))

        return SamplingStrategy(
            method=SamplingMethod.RANDOM,
            sample_size=n,
            confidence_level=confidence_level,
            tolerable_error=tolerable_error,
            expected_error=expected_error,
            rationale=f"该科目风险等级为【低】，建议采用随机抽样。"
                     f"置信水平{confidence_level*100:.0f}%，可容忍误差{tolerable_error*100:.1f}%，"
                     f"计算样本量为{n}笔。",
            parameters={
                "z_value": z,
                "formula": "n = (Z² × p × (1-p)) / e² × N / (N + n₀ - 1)"
            }
        )

    def _calculate_sample_size(
        self,
        population_size: int,
        z: float,
        p: float,
        e: float
    ) -> int:
        """
        计算样本量

        使用公式: n = (Z² × p × (1-p)) / e²
        有限总体校正: n_adj = n × N / (N + n - 1)
        """
        if population_size == 0:
            return 0

        # 初始样本量计算
        n = (z ** 2 * p * (1 - p)) / (e ** 2)

        # 有限总体校正
        n_adjusted = n * population_size / (population_size + n - 1)

        # 样本量限制：最小10笔，但不超过总体规模
        sample_size = int(round(n_adjusted))
        sample_size = min(sample_size, population_size)  # 不能超过总体规模
        sample_size = max(1, sample_size)  # 至少1笔

        return sample_size

    def _create_amount_strata(
        self,
        project_id: str,
        subject_code: str,
        population_info: Dict[str, Any]
    ) -> List[StratificationLayer]:
        """创建金额分层"""
        # 获取金额分布
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT amount FROM vouchers
                WHERE project_id = ? AND subject_code LIKE ? AND amount IS NOT NULL
                ORDER BY amount DESC
                """,
                [project_id, f"{subject_code}%"]
            )
            amounts = [float(row[0]) for row in cursor.fetchall()]

        if not amounts:
            return []

        # 分层阈值
        total_amount = sum(amounts)
        cumulative = 0
        threshold_80 = total_amount * 0.8  # 前80%金额的阈值
        threshold_95 = total_amount * 0.95  # 前95%金额的阈值

        large_threshold = 0
        medium_threshold = 0

        for amount in amounts:
            cumulative += amount
            if large_threshold == 0 and cumulative >= threshold_80:
                large_threshold = amount
            if medium_threshold == 0 and cumulative >= threshold_95:
                medium_threshold = amount
                break

        # 统计各层数量
        large_count = len([a for a in amounts if a >= large_threshold]) if large_threshold > 0 else 0
        medium_count = len([a for a in amounts if medium_threshold <= a < large_threshold]) if medium_threshold > 0 else 0
        small_count = len(amounts) - large_count - medium_count

        layers = [
            StratificationLayer(
                name="大额层",
                min_amount=large_threshold,
                max_amount=population_info["max_amount"],
                count=large_count,
                sample_size=0,  # 稍后计算
                method=SamplingMethod.JUDGMENT
            ),
            StratificationLayer(
                name="中额层",
                min_amount=medium_threshold if medium_threshold > 0 else large_threshold,
                max_amount=large_threshold if large_threshold > 0 else population_info["max_amount"],
                count=medium_count,
                sample_size=0,
                method=SamplingMethod.RANDOM
            ),
            StratificationLayer(
                name="小额层",
                min_amount=population_info["min_amount"],
                max_amount=medium_threshold if medium_threshold > 0 else large_threshold,
                count=small_count,
                sample_size=0,
                method=SamplingMethod.RANDOM
            )
        ]

        return [l for l in layers if l.count > 0]

    def _identify_focus_areas(self, risk_profile: RiskProfile) -> List[str]:
        """识别重点关注领域"""
        focus_areas = []

        for factor in risk_profile.risk_factors:
            if factor.score >= 70:
                focus_areas.append(factor.name)

        # 根据风险因素添加特定关注点
        factor_names = [f.name for f in risk_profile.risk_factors]

        if "金额重要性" in factor_names:
            focus_areas.append("大额交易核实")
            focus_areas.append("金额截止测试")

        if "业务复杂性" in factor_names:
            focus_areas.append("交易对手核查")
            focus_areas.append("关联方交易识别")

        if "异常指标" in factor_names:
            focus_areas.append("异常交易调查")
            focus_areas.append("时间性分析")

        return list(set(focus_areas))

    def calculate_sample_size_interactive(
        self,
        population_size: int,
        confidence_level: float = 0.95,
        tolerable_error: float = 0.05,
        expected_error: float = 0.03
    ) -> Dict[str, Any]:
        """
        交互式样本量计算

        Args:
            population_size: 总体规模
            confidence_level: 置信水平
            tolerable_error: 可容忍误差
            expected_error: 预期偏差率

        Returns:
            Dict: 计算结果和可视化数据
        """
        z = self.z_values.get(confidence_level, 1.96)
        sample_size = self._calculate_sample_size(population_size, z, expected_error, tolerable_error)

        # 扩展的Z值表（用于生成平滑曲线）
        extended_z_values = {
            0.80: 1.282,
            0.85: 1.440,
            0.90: 1.645,
            0.91: 1.695,
            0.92: 1.751,
            0.93: 1.812,
            0.94: 1.881,
            0.95: 1.960,
            0.96: 2.054,
            0.97: 2.170,
            0.98: 2.326,
            0.99: 2.576
        }

        # 生成样本量-置信度曲线数据（固定可容忍误差和预期偏差率）
        curve_data = []
        for cl in [0.80, 0.85, 0.90, 0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99]:
            z_val = extended_z_values.get(cl, 1.96)
            n = self._calculate_sample_size(population_size, z_val, expected_error, tolerable_error)
            curve_data.append({
                "confidence_level": cl,
                "sample_size": n
            })

        # 生成不同参数下的样本量对比表
        comparisons = []
        for cl in [0.90, 0.95, 0.99]:
            for te in [0.03, 0.05, 0.08, 0.10]:
                n = self._calculate_sample_size(
                    population_size,
                    self.z_values.get(cl, 1.96),
                    expected_error,
                    te
                )
                comparisons.append({
                    "confidence_level": cl,
                    "tolerable_error": te,
                    "sample_size": n
                })

        return {
            "sample_size": sample_size,
            "parameters": {
                "population_size": population_size,
                "confidence_level": confidence_level,
                "tolerable_error": tolerable_error,
                "expected_error": expected_error,
                "z_value": z
            },
            "sampling_rate": sample_size / population_size if population_size > 0 else 0,
            "curve_data": curve_data,
            "comparisons": comparisons
        }

    def recommend_layered_sampling(
        self,
        project_id: str,
        high_ratio: float = 1.0,
        medium_ratio: float = 0.3,
        low_ratio: float = 0.05
    ) -> Dict[str, Any]:
        """
        分层抽样推荐

        根据风险等级分层：
        - 高风险：100%检查
        - 中风险：30%抽样
        - 低风险：5%抽样

        Args:
            project_id: 项目ID
            high_ratio: 高风险抽样比例
            medium_ratio: 中风险抽样比例
            low_ratio: 低风险抽样比例

        Returns:
            Dict: 分层抽样建议
        """
        from app.services.voucher_risk_service import voucher_risk_service

        with get_db_cursor() as cursor:
            # 按风险等级统计凭证数量
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

        layers = {
            "high": {"level": "high", "count": 0, "amount": 0, "ratio": high_ratio, "sample_size": 0},
            "medium": {"level": "medium", "count": 0, "amount": 0, "ratio": medium_ratio, "sample_size": 0},
            "low": {"level": "low", "count": 0, "amount": 0, "ratio": low_ratio, "sample_size": 0}
        }

        for row in rows:
            level = row[0] or "low"
            if level in layers:
                layers[level]["count"] = row[1] or 0
                layers[level]["amount"] = float(row[2]) if row[2] else 0

        # 计算各层样本量
        total_sample = 0
        for level in layers:
            count = layers[level]["count"]
            ratio = layers[level]["ratio"]
            sample_size = max(1, int(count * ratio)) if count > 0 else 0
            if ratio >= 1.0:  # 100%检查
                sample_size = count
            layers[level]["sample_size"] = sample_size
            total_sample += sample_size

        # 获取总体统计
        total_count = sum(l["count"] for l in layers.values())
        total_amount = sum(l["amount"] for l in layers.values())

        # 生成建议说明
        recommendations = []
        if layers["high"]["count"] > 0:
            recommendations.append(f"高风险凭证{layers['high']['count']}笔，建议100%检查")
        if layers["medium"]["count"] > 0:
            recommendations.append(f"中风险凭证{layers['medium']['count']}笔，建议抽取{layers['medium']['sample_size']}笔（{medium_ratio*100:.0f}%）")
        if layers["low"]["count"] > 0:
            recommendations.append(f"低风险凭证{layers['low']['count']}笔，建议抽取{layers['low']['sample_size']}笔（{low_ratio*100:.0f}%）")

        return {
            "layers": list(layers.values()),
            "total_population": total_count,
            "total_amount": total_amount,
            "total_sample_size": total_sample,
            "overall_sampling_rate": round(total_sample / total_count * 100, 2) if total_count > 0 else 0,
            "recommendation": "；".join(recommendations) + f"。合计抽样{total_sample}笔。"
        }

    def recommend_key_focus_sampling(
        self,
        project_id: str,
        risk_tag_codes: List[str] = None
    ) -> Dict[str, Any]:
        """
        重点关注抽样推荐

        根据风险标签圈定样本：
        - 关联方交易
        - 节假日交易
        - 大额交易
        - 新客户交易
        等

        Args:
            project_id: 项目ID
            risk_tag_codes: 风险标签代码列表，为空则使用默认高风险标签

        Returns:
            Dict: 重点关注抽样建议
        """
        if not risk_tag_codes:
            # 默认高风险标签
            risk_tag_codes = [
                "SUPER_LARGE_AMOUNT",
                "RELATED_PARTY",
                "WEEKEND_TRANSACTION",
                "YEAR_END_TRANSACTION",
                "MISSING_INVOICE"
            ]

        with get_db_cursor() as cursor:
            placeholders = ",".join(["?" for _ in risk_tag_codes])

            # 获取有指定标签的凭证
            cursor.execute(
                f"""
                SELECT DISTINCT v.id, v.voucher_no, v.voucher_date, v.amount,
                       v.subject_code, v.subject_name, v.risk_score, v.risk_level
                FROM vouchers v
                JOIN voucher_risk_tags t ON v.id = t.voucher_id
                WHERE v.project_id = ? AND t.tag_code IN ({placeholders})
                ORDER BY v.risk_score DESC, v.amount DESC
                """,
                [project_id] + risk_tag_codes
            )
            rows = cursor.fetchall()

            # 统计各标签数量
            cursor.execute(
                f"""
                SELECT t.tag_code, t.tag_name, COUNT(DISTINCT t.voucher_id) as count
                FROM voucher_risk_tags t
                JOIN vouchers v ON t.voucher_id = v.id
                WHERE v.project_id = ? AND t.tag_code IN ({placeholders})
                GROUP BY t.tag_code, t.tag_name
                ORDER BY count DESC
                """,
                [project_id] + risk_tag_codes
            )
            tag_stats = [
                {"tag_code": row[0], "tag_name": row[1], "count": row[2]}
                for row in cursor.fetchall()
            ]

        samples = [
            {
                "voucher_id": row[0],
                "voucher_no": row[1],
                "voucher_date": str(row[2]) if row[2] else None,
                "amount": float(row[3]) if row[3] else 0,
                "subject_code": row[4],
                "subject_name": row[5],
                "risk_score": float(row[6]) if row[6] else 0,
                "risk_level": row[7] or "low"
            }
            for row in rows
        ]

        # 去重（同一凭证可能有多个标签）
        seen = set()
        unique_samples = []
        for s in samples:
            if s["voucher_id"] not in seen:
                seen.add(s["voucher_id"])
                unique_samples.append(s)

        return {
            "focus_tags": risk_tag_codes,
            "tag_statistics": tag_stats,
            "sample_count": len(unique_samples),
            "samples": unique_samples[:100],  # 最多返回100条
            "recommendation": f"根据风险标签筛选，共{len(unique_samples)}笔凭证需要重点关注。建议对这些凭证进行详细审计。"
        }

    def integrate_with_mus(
        self,
        project_id: str,
        subject_code: str = None,
        tolerable_misstatement: float = None,
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        与MUS抽样集成

        结合风险画像和货币单位抽样：
        - 高风险凭证：100%检查
        - 其余：MUS抽样

        Args:
            project_id: 项目ID
            subject_code: 科目代码（可选）
            tolerable_misstatement: 可容忍错报
            confidence_level: 置信水平

        Returns:
            Dict: 集成抽样建议
        """
        with get_db_cursor() as cursor:
            # 获取高风险凭证
            sql = """
                SELECT id, voucher_no, amount, risk_score, risk_level
                FROM vouchers
                WHERE project_id = ? AND risk_level = 'high'
            """
            params = [project_id]
            if subject_code:
                sql += " AND subject_code LIKE ?"
                params.append(f"{subject_code}%")

            cursor.execute(sql, params)
            high_risk_rows = cursor.fetchall()

            # 获取剩余凭证（用于MUS）
            sql = """
                SELECT id, voucher_no, amount, risk_score
                FROM vouchers
                WHERE project_id = ? AND (risk_level != 'high' OR risk_level IS NULL)
            """
            params = [project_id]
            if subject_code:
                sql += " AND subject_code LIKE ?"
                params.append(f"{subject_code}%")

            cursor.execute(sql, params)
            mus_rows = cursor.fetchall()

            # 获取总金额
            sql = "SELECT COALESCE(SUM(amount), 0) FROM vouchers WHERE project_id = ?"
            params = [project_id]
            if subject_code:
                sql += " AND subject_code LIKE ?"
                params.append(f"{subject_code}%")

            cursor.execute(sql, params)
            total_amount = float(cursor.fetchone()[0]) or 1

        # 高风险凭证列表
        high_risk_samples = [
            {
                "voucher_id": row[0],
                "voucher_no": row[1],
                "amount": float(row[2]) if row[2] else 0,
                "risk_score": float(row[3]) if row[3] else 0
            }
            for row in high_risk_rows
        ]

        # 计算MUS参数
        if tolerable_misstatement is None:
            tolerable_misstatement = total_amount * 0.01  # 默认1%作为可容忍错报

        # 可靠性因子
        reliability_factors = {
            0.90: 2.31,
            0.95: 3.00,
            0.99: 4.61
        }
        rf = reliability_factors.get(confidence_level, 3.00)

        # MUS抽样区间
        mus_total = sum(float(row[2]) if row[2] else 0 for row in mus_rows)
        sampling_interval = tolerable_misstatement / rf if rf > 0 else mus_total
        mus_sample_size = int(mus_total / sampling_interval) if sampling_interval > 0 else 0

        return {
            "high_risk_samples": high_risk_samples,
            "high_risk_count": len(high_risk_samples),
            "high_risk_amount": sum(s["amount"] for s in high_risk_samples),
            "mus_population": mus_total,
            "mus_sampling_interval": round(sampling_interval, 2),
            "mus_sample_size": max(1, mus_sample_size),
            "total_sample_size": len(high_risk_samples) + max(1, mus_sample_size),
            "tolerable_misstatement": tolerable_misstatement,
            "confidence_level": confidence_level,
            "recommendation": f"建议对{len(high_risk_samples)}笔高风险凭证进行100%检查，同时从剩余凭证中使用MUS方法抽取{max(1, mus_sample_size)}笔样本。"
        }


# 全局服务实例
sampling_strategy_recommender = SamplingStrategyRecommender()