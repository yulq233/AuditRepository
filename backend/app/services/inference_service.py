"""
统计推断服务

根据样本结果推断总体特征
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import math

from app.core.database import get_db_cursor, get_db


class SamplingMethod(str, Enum):
    """抽样方法"""
    MUS = "monetary_unit"
    SYSTEMATIC = "systematic"
    RANDOM = "random"
    STRATIFIED = "stratified"


@dataclass
class InferenceResult:
    """推断结果"""
    method: SamplingMethod
    sample_size: int
    population_size: int
    population_amount: float
    misstatement_count: int
    misstatement_amount: float
    projected_misstatement: float
    upper_limit: float
    lower_limit: float
    confidence_level: float
    precision: float
    is_acceptable: bool
    conclusion: str
    recommendations: List[str]


class InferenceService:
    """推断服务"""

    def infer(
        self,
        project_id: str,
        record_id: str,
        confidence_level: float = 0.95,
        tolerable_error: float = 0.05
    ) -> InferenceResult:
        """
        执行总体推断

        Args:
            project_id: 项目ID
            record_id: 抽样记录ID
            confidence_level: 置信水平
            tolerable_error: 可容忍误差率

        Returns:
            InferenceResult: 推断结果
        """
        # 获取抽样记录信息
        record_data = self._get_sampling_record(record_id)
        if not record_data:
            raise ValueError("抽样记录不存在")

        method = SamplingMethod(record_data['rule_type'])

        # 获取样本错报
        misstatements = self._get_sample_misstatements(record_id)

        # 获取总体信息
        population_data = self._get_population_data(project_id)

        # 根据方法执行推断
        if method == SamplingMethod.MUS:
            result = self._mus_inference(
                record_data, misstatements, population_data,
                confidence_level, tolerable_error
            )
        elif method == SamplingMethod.SYSTEMATIC:
            result = self._systematic_inference(
                record_data, misstatements, population_data,
                confidence_level, tolerable_error
            )
        else:
            result = self._random_inference(
                record_data, misstatements, population_data,
                confidence_level, tolerable_error
            )

        # 保存推断结果
        self._save_inference_result(project_id, record_id, result)

        return result

    def _get_sampling_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """获取抽样记录"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT r.id, r.rule_type, r.sample_size, r.population_count, r.population_amount,
                       sr.sampling_interval, sr.random_start, sr.confidence_level
                FROM sampling_records r
                LEFT JOIN sampling_rules sr ON r.rule_id = sr.id
                WHERE r.id = ?
                """,
                [record_id]
            )
            row = cursor.fetchone()
            if not row:
                return None

            return {
                "id": row[0],
                "rule_type": row[1],
                "sample_size": row[2] or 0,
                "population_count": row[3] or 0,
                "population_amount": float(row[4]) if row[4] else 0,
                "sampling_interval": float(row[5]) if row[5] else None,
                "random_start": float(row[6]) if row[6] else None,
                "confidence_level": float(row[7]) if row[7] else 0.95
            }

    def _get_sample_misstatements(self, record_id: str) -> List[Dict[str, Any]]:
        """获取样本错报"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT sm.id, sm.sample_id, sm.misstatement_type, sm.misstatement_amount,
                       sm.original_amount, sm.correct_amount, sm.description, sm.is_confirmed
                FROM sample_misstatements sm
                JOIN samples s ON sm.sample_id = s.id
                WHERE s.record_id = ? AND sm.is_confirmed = TRUE
                """,
                [record_id]
            )

            return [
                {
                    "id": row[0],
                    "sample_id": row[1],
                    "misstatement_type": row[2],
                    "misstatement_amount": float(row[3]) if row[3] else 0,
                    "original_amount": float(row[4]) if row[4] else 0,
                    "correct_amount": float(row[5]) if row[5] else 0,
                    "description": row[6],
                    "is_confirmed": bool(row[7])
                }
                for row in cursor.fetchall()
            ]

    def _get_population_data(self, project_id: str) -> Dict[str, Any]:
        """获取总体数据"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(amount), 0)
                FROM vouchers WHERE project_id = ?
                """,
                [project_id]
            )
            row = cursor.fetchone()

            return {
                "count": row[0] or 0,
                "amount": float(row[1]) if row[1] else 0
            }

    def _mus_inference(
        self,
        record_data: Dict[str, Any],
        misstatements: List[Dict[str, Any]],
        population_data: Dict[str, Any],
        confidence_level: float,
        tolerable_error: float
    ) -> InferenceResult:
        """MUS推断"""
        interval = record_data.get('sampling_interval', 1)
        population_amount = population_data['amount']

        # 样本错报统计
        total_misstatement = sum(m['misstatement_amount'] for m in misstatements)
        misstatement_count = len(misstatements)

        # 获取保证系数
        reliability_factors = {
            0.90: {0: 2.31, 1: 3.89, 2: 5.33, 3: 6.69},
            0.95: {0: 3.00, 1: 4.75, 2: 6.30, 3: 7.76},
            0.99: {0: 4.61, 1: 6.64, 2: 8.41, 3: 10.05}
        }
        rf_table = reliability_factors.get(confidence_level, reliability_factors[0.95])
        rf = rf_table.get(min(misstatement_count, max(rf_table.keys())), rf_table.get(0, 3.00))

        # 计算错报上限
        upper_limit = rf * interval
        projected_misstatement = total_misstatement
        precision = upper_limit - projected_misstatement

        # 可容忍错报
        tolerable_amount = population_amount * tolerable_error
        is_acceptable = upper_limit <= tolerable_amount

        # 生成结论
        conclusion = self._generate_conclusion(is_acceptable, projected_misstatement, upper_limit, tolerable_amount)
        recommendations = self._generate_recommendations(is_acceptable, misstatement_count, upper_limit, tolerable_amount)

        return InferenceResult(
            method=SamplingMethod.MUS,
            sample_size=record_data['sample_size'],
            population_size=record_data['population_count'],
            population_amount=population_amount,
            misstatement_count=misstatement_count,
            misstatement_amount=total_misstatement,
            projected_misstatement=projected_misstatement,
            upper_limit=upper_limit,
            lower_limit=0,
            confidence_level=confidence_level,
            precision=precision,
            is_acceptable=is_acceptable,
            conclusion=conclusion,
            recommendations=recommendations
        )

    def _systematic_inference(
        self,
        record_data: Dict[str, Any],
        misstatements: List[Dict[str, Any]],
        population_data: Dict[str, Any],
        confidence_level: float,
        tolerable_error: float
    ) -> InferenceResult:
        """系统抽样推断"""
        sample_size = record_data['sample_size']
        population_size = record_data['population_count']
        population_amount = population_data['amount']

        # 样本错报统计
        misstatement_count = len(misstatements)
        total_misstatement = sum(m['misstatement_amount'] for m in misstatements)

        # 样本误差率
        error_rate = misstatement_count / sample_size if sample_size > 0 else 0

        # Z值
        z_values = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        z = z_values.get(confidence_level, 1.96)

        # 标准误差
        se = math.sqrt(error_rate * (1 - error_rate) / sample_size) if sample_size > 0 and 0 < error_rate < 1 else 0

        # 有限总体校正因子
        fpc = math.sqrt((population_size - sample_size) / (population_size - 1)) if population_size > 1 else 1
        se_adjusted = se * fpc

        # 置信区间
        lower_rate = max(0, error_rate - z * se_adjusted)
        upper_rate = min(1, error_rate + z * se_adjusted)

        # 金额推断
        avg_amount = population_amount / population_size if population_size > 0 else 0
        projected_misstatement = error_rate * population_amount
        upper_limit = upper_rate * population_amount
        lower_limit = lower_rate * population_amount
        precision = upper_limit - projected_misstatement

        # 判断可接受性
        tolerable_amount = population_amount * tolerable_error
        is_acceptable = upper_limit <= tolerable_amount

        # 生成结论
        conclusion = self._generate_conclusion(is_acceptable, projected_misstatement, upper_limit, tolerable_amount)
        recommendations = self._generate_recommendations(is_acceptable, misstatement_count, upper_limit, tolerable_amount)

        return InferenceResult(
            method=SamplingMethod.SYSTEMATIC,
            sample_size=sample_size,
            population_size=population_size,
            population_amount=population_amount,
            misstatement_count=misstatement_count,
            misstatement_amount=total_misstatement,
            projected_misstatement=projected_misstatement,
            upper_limit=upper_limit,
            lower_limit=lower_limit,
            confidence_level=confidence_level,
            precision=precision,
            is_acceptable=is_acceptable,
            conclusion=conclusion,
            recommendations=recommendations
        )

    def _random_inference(
        self,
        record_data: Dict[str, Any],
        misstatements: List[Dict[str, Any]],
        population_data: Dict[str, Any],
        confidence_level: float,
        tolerable_error: float
    ) -> InferenceResult:
        """随机抽样推断"""
        sample_size = record_data['sample_size']
        population_size = record_data['population_count']
        population_amount = population_data['amount']

        # 样本错报统计
        misstatement_count = len(misstatements)
        total_misstatement = sum(m['misstatement_amount'] for m in misstatements)

        # 样本误差率
        error_rate = misstatement_count / sample_size if sample_size > 0 else 0
        amount_error_rate = total_misstatement / (population_amount * sample_size / population_size) if population_amount > 0 else 0

        # Z值
        z_values = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        z = z_values.get(confidence_level, 1.96)

        # 标准误差
        se = math.sqrt(error_rate * (1 - error_rate) / sample_size) if sample_size > 0 and 0 < error_rate < 1 else 0

        # 有限总体校正因子
        fpc = math.sqrt((population_size - sample_size) / (population_size - 1)) if population_size > 1 else 1
        se_adjusted = se * fpc

        # 置信区间
        lower_rate = max(0, error_rate - z * se_adjusted)
        upper_rate = min(1, error_rate + z * se_adjusted)

        # 金额推断
        projected_misstatement = error_rate * population_amount
        upper_limit = upper_rate * population_amount
        lower_limit = lower_rate * population_amount
        precision = upper_limit - projected_misstatement

        # 判断可接受性
        tolerable_amount = population_amount * tolerable_error
        is_acceptable = upper_limit <= tolerable_amount

        # 生成结论
        conclusion = self._generate_conclusion(is_acceptable, projected_misstatement, upper_limit, tolerable_amount)
        recommendations = self._generate_recommendations(is_acceptable, misstatement_count, upper_limit, tolerable_amount)

        return InferenceResult(
            method=SamplingMethod.RANDOM,
            sample_size=sample_size,
            population_size=population_size,
            population_amount=population_amount,
            misstatement_count=misstatement_count,
            misstatement_amount=total_misstatement,
            projected_misstatement=projected_misstatement,
            upper_limit=upper_limit,
            lower_limit=lower_limit,
            confidence_level=confidence_level,
            precision=precision,
            is_acceptable=is_acceptable,
            conclusion=conclusion,
            recommendations=recommendations
        )

    def _generate_conclusion(
        self,
        is_acceptable: bool,
        projected: float,
        upper_limit: float,
        tolerable: float
    ) -> str:
        """生成结论"""
        if is_acceptable:
            return f"总体错报未超过可容忍错报，推断错报上限为{upper_limit:,.2f}元，低于可容忍错报{tolerable:,.2f}元，可以接受。"
        else:
            return f"总体错报可能超过可容忍错报，推断错报上限为{upper_limit:,.2f}元，高于可容忍错报{tolerable:,.2f}元，需要关注。"

    def _generate_recommendations(
        self,
        is_acceptable: bool,
        misstatement_count: int,
        upper_limit: float,
        tolerable: float
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        if not is_acceptable:
            recommendations.append("建议扩大样本量，进一步验证总体错报情况")
            recommendations.append("对发现的错报进行原因分析，确定是否为系统性问题")

            if upper_limit > tolerable * 1.5:
                recommendations.append("建议提请管理层调整账目，并评估对财务报表的影响")
            elif upper_limit > tolerable * 1.2:
                recommendations.append("建议执行替代程序，对相关科目进行补充测试")

        if misstatement_count > 0:
            recommendations.append(f"发现{misstatement_count}笔样本错报，建议逐一分析错报原因")

        return recommendations

    def _save_inference_result(self, project_id: str, record_id: str, result: InferenceResult):
        """保存推断结果"""
        import uuid
        import json

        inference_id = str(uuid.uuid4())

        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO statistical_inferences
                (id, project_id, record_id, inference_type, confidence_level,
                 sample_misstatement_count, sample_misstatement_amount,
                 projected_misstatement, upper_limit, lower_limit, precision,
                 conclusion, is_acceptable, recommendations, calculated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    inference_id, project_id, record_id, result.method.value,
                    result.confidence_level, result.misstatement_count, result.misstatement_amount,
                    result.projected_misstatement, result.upper_limit, result.lower_limit,
                    result.precision, result.conclusion, result.is_acceptable,
                    json.dumps(result.recommendations), datetime.now()
                ]
            )

            # 更新抽样记录
            cursor.execute(
                """
                UPDATE sampling_records
                SET inference_completed = TRUE, inference_conclusion = ?
                WHERE id = ?
                """,
                [result.conclusion, record_id]
            )

            get_db().commit()

        return inference_id


from datetime import datetime