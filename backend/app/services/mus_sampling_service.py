"""
货币单位抽样服务 (Monetary Unit Sampling)

MUS是一种统计抽样方法，每个货币单位都有同等被选中的概率。
适用于实质性测试，特别适合测试账户余额的高估。

核心原理：
- 抽样间隔 = 可容忍错报 / 保证系数
- 样本量 = 总体金额 / 抽样间隔
- 随机起点 = [0, 抽样间隔) 之间的随机数
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import math
import random


@dataclass
class MUSConfig:
    """MUS配置"""
    confidence_level: float = 0.95        # 置信水平
    tolerable_misstatement: float = 0.05  # 可容忍错报率
    expected_misstatement: float = 0.01   # 预期错报率
    population_amount: float = 0          # 总体金额

    # 保证系数表（基于泊松分布）
    # 键: 置信水平, 值: {预期错报数: 保证系数}
    RELIABILITY_FACTORS = {
        0.90: {0: 2.31, 1: 3.89, 2: 5.33, 3: 6.69, 4: 8.00, 5: 9.28},
        0.95: {0: 3.00, 1: 4.75, 2: 6.30, 3: 7.76, 4: 9.16, 5: 10.52},
        0.99: {0: 4.61, 1: 6.64, 2: 8.41, 3: 10.05, 4: 11.61, 5: 13.11}
    }


class MUSSampler:
    """货币单位抽样器"""

    def __init__(self, config: Optional[MUSConfig] = None):
        self.config = config or MUSConfig()

    def calculate_sample_size(
        self,
        population_amount: float,
        confidence_level: float,
        tolerable_misstatement: float,
        expected_misstatement: float = 0
    ) -> Dict[str, Any]:
        """
        计算MUS样本量

        公式:
            抽样间隔 = 可容忍错报 / 保证系数
            样本量 = 总体金额 / 抽样间隔

        Args:
            population_amount: 总体金额
            confidence_level: 置信水平 (0.90, 0.95, 0.99)
            tolerable_misstatement: 可容忍错报率 (如0.05表示5%)
            expected_misstatement: 预期错报率

        Returns:
            Dict: 包含样本量、抽样间隔、随机起点等参数
        """
        if population_amount <= 0:
            return {
                "sample_size": 0,
                "sampling_interval": 0,
                "random_start": 0,
                "reliability_factor": 0,
                "tolerable_amount": 0,
                "error": "总体金额必须大于0"
            }

        # 标准化置信水平
        confidence_level = self._normalize_confidence_level(confidence_level)

        # 获取保证系数
        rf_table = MUSConfig.RELIABILITY_FACTORS.get(confidence_level, {})
        # 根据预期错报率估计预期错报数
        expected_errors = int(expected_misstatement * 100)  # 简化处理
        reliability_factor = rf_table.get(min(expected_errors, max(rf_table.keys())), rf_table.get(0, 3.00))

        # 计算可容忍错报金额
        tolerable_amount = population_amount * tolerable_misstatement

        # 计算抽样间隔
        sampling_interval = tolerable_amount / reliability_factor

        # 计算样本量
        sample_size = max(1, math.ceil(population_amount / sampling_interval))

        # 生成随机起点
        random_start = random.uniform(0, sampling_interval)

        return {
            "sample_size": sample_size,
            "sampling_interval": round(sampling_interval, 2),
            "random_start": round(random_start, 2),
            "reliability_factor": reliability_factor,
            "tolerable_amount": round(tolerable_amount, 2),
            "confidence_level": confidence_level,
            "population_amount": population_amount
        }

    def _normalize_confidence_level(self, confidence_level: float) -> float:
        """标准化置信水平"""
        if confidence_level > 1:
            confidence_level = confidence_level / 100

        # 找最接近的标准值
        standard_levels = [0.90, 0.95, 0.99]
        return min(standard_levels, key=lambda x: abs(x - confidence_level))

    def select_samples(
        self,
        vouchers: List[Dict[str, Any]],
        interval: float,
        random_start: float
    ) -> List[Dict[str, Any]]:
        """
        MUS选样

        使用累计金额法：从随机起点开始，每间隔一定金额选取一个样本
        大额凭证有更高的被选中概率

        Args:
            vouchers: 凭证列表，每个凭证需包含amount字段
            interval: 抽样间隔
            random_start: 随机起点

        Returns:
            List: 选中的样本列表
        """
        if interval <= 0:
            return []

        samples = []
        cumulative = 0
        next_selection = random_start

        # 过滤无效凭证并按金额降序排序（确保大额优先处理）
        valid_vouchers = [
            v for v in vouchers
            if v.get('amount') and float(v.get('amount', 0)) > 0
        ]
        sorted_vouchers = sorted(valid_vouchers, key=lambda x: float(x.get('amount', 0)), reverse=True)

        for voucher in sorted_vouchers:
            amount = float(voucher.get('amount', 0))
            cumulative += amount

            # 累计金额超过选择点时选取该凭证
            while cumulative >= next_selection:
                sample = {
                    **voucher,
                    "selection_point": round(next_selection, 2),
                    "cumulative_before": round(cumulative - amount, 2),
                    "cumulative_after": round(cumulative, 2),
                    "selection_method": "MUS"
                }
                samples.append(sample)
                next_selection += interval

        return samples

    def project_misstatement(
        self,
        misstatements: List[Dict[str, Any]],
        interval: float,
        population_amount: float,
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        MUS错报推断

        使用泊松分布进行总体错报推断

        Args:
            misstatements: 错报列表，每个错报需包含misstatement_amount字段
            interval: 抽样间隔
            population_amount: 总体金额
            confidence_level: 置信水平

        Returns:
            Dict: 推断结果
        """
        # 标准化置信水平
        confidence_level = self._normalize_confidence_level(confidence_level)

        # 计算样本错报统计
        total_misstatement = sum(
            float(m.get('misstatement_amount', 0))
            for m in misstatements
        )
        misstatement_count = len(misstatements)

        # 计算推断错报（点估计）
        projected_misstatement = total_misstatement

        # 获取上界保证系数
        rf_table = MUSConfig.RELIABILITY_FACTORS.get(confidence_level, {})
        max_rf_key = max(rf_table.keys()) if rf_table else 0
        upper_rf = rf_table.get(min(misstatement_count, max_rf_key), rf_table.get(0, 3.00))

        # 计算错报上限
        upper_limit = upper_rf * interval

        # 计算精度
        precision = upper_limit - projected_misstatement

        # 可容忍错报（默认为总体金额的5%）
        tolerable = population_amount * 0.05

        # 判断是否可接受
        is_acceptable = upper_limit <= tolerable

        # 生成结论
        if is_acceptable:
            conclusion = "总体错报未超过可容忍错报，可以接受"
        else:
            conclusion = f"总体错报上限({upper_limit:.2f})超过可容忍错报({tolerable:.2f})，需要关注"

        # 生成建议
        recommendations = self._generate_recommendations(
            is_acceptable,
            upper_limit,
            tolerable,
            misstatement_count,
            projected_misstatement
        )

        return {
            "projected_misstatement": round(projected_misstatement, 2),
            "upper_limit": round(upper_limit, 2),
            "lower_limit": 0,
            "precision": round(precision, 2),
            "is_acceptable": is_acceptable,
            "conclusion": conclusion,
            "recommendations": recommendations,
            "confidence_level": confidence_level,
            "reliability_factor_used": upper_rf,
            "sampling_interval": interval
        }

    def _generate_recommendations(
        self,
        is_acceptable: bool,
        upper_limit: float,
        tolerable: float,
        misstatement_count: int,
        projected_misstatement: float
    ) -> List[str]:
        """生成扩展测试建议"""
        recommendations = []

        if not is_acceptable:
            recommendations.append("建议扩大样本量，进一步验证总体错报情况")
            recommendations.append("对发现的错报进行原因分析，确定是否为系统性问题")

            # 根据错报严重程度提供建议
            if upper_limit > tolerable * 1.5:
                recommendations.append("建议提请管理层调整账目，并评估对财务报表的影响")
            elif upper_limit > tolerable * 1.2:
                recommendations.append("建议执行替代程序，对相关科目进行补充测试")

        if misstatement_count > 0:
            recommendations.append(f"发现{misstatement_count}笔样本错报，建议逐一分析错报原因")

        return recommendations

    def calculate_materiality(
        self,
        population_amount: float,
        percentage: float = 0.01
    ) -> Dict[str, Any]:
        """
        计算重要性水平

        Args:
            population_amount: 总体金额
            percentage: 重要性比例（默认1%）

        Returns:
            Dict: 重要性水平相关信息
        """
        materiality = population_amount * percentage
        performance_materiality = materiality * 0.5  # 执行重要性

        return {
            "materiality": round(materiality, 2),
            "performance_materiality": round(performance_materiality, 2),
            "percentage": percentage
        }


def preview_mus_sampling(
    population_amount: float,
    confidence_level: float = 0.95,
    tolerable_misstatement: float = 0.05,
    expected_misstatement: float = 0.01
) -> Dict[str, Any]:
    """
    预览MUS抽样参数（便捷函数）

    Args:
        population_amount: 总体金额
        confidence_level: 置信水平
        tolerable_misstatement: 可容忍错报率
        expected_misstatement: 预期错报率

    Returns:
        Dict: 预览结果
    """
    sampler = MUSSampler()
    return sampler.calculate_sample_size(
        population_amount=population_amount,
        confidence_level=confidence_level,
        tolerable_misstatement=tolerable_misstatement,
        expected_misstatement=expected_misstatement
    )