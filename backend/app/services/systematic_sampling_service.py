"""
系统抽样服务 (Systematic Sampling)

系统抽样是一种抽样方法，按固定间隔从总体中抽取样本。
适用于大规模总体，抽样效率高。

核心原理：
- 抽样间隔 = 总体规模 / 样本量
- 随机起点 = [1, 抽样间隔] 之间的随机整数
- 从随机起点开始，每隔interval个选取一个样本
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import math
import random


@dataclass
class SystematicConfig:
    """系统抽样配置"""
    population_size: int = 0           # 总体规模
    sample_size: int = 0               # 样本量
    interval: int = 1                  # 抽样间隔
    random_start: int = 1              # 随机起点


class SystematicSampler:
    """系统抽样器"""

    def calculate_parameters(
        self,
        population_size: int,
        sample_size: int
    ) -> Dict[str, Any]:
        """
        计算系统抽样参数

        公式:
            抽样间隔 = 总体规模 / 样本量
            随机起点 = [1, 抽样间隔] 之间的随机整数

        Args:
            population_size: 总体规模（凭证笔数）
            sample_size: 样本量

        Returns:
            Dict: 包含抽样间隔、随机起点等参数
        """
        if population_size <= 0:
            return {
                "interval": 0,
                "random_start": 0,
                "population_size": 0,
                "sample_size": 0,
                "error": "总体规模必须大于0"
            }

        if sample_size <= 0:
            return {
                "interval": 0,
                "random_start": 0,
                "population_size": population_size,
                "sample_size": 0,
                "error": "样本量必须大于0"
            }

        if sample_size >= population_size:
            return {
                "interval": 1,
                "random_start": 1,
                "population_size": population_size,
                "sample_size": population_size,
                "note": "样本量大于等于总体规模，将全量抽样"
            }

        # 计算抽样间隔
        interval = population_size // sample_size

        # 生成随机起点（1到interval之间）
        random_start = random.randint(1, max(1, interval))

        # 实际样本量（考虑边界）
        actual_sample_size = len(range(random_start - 1, population_size, interval))

        return {
            "interval": interval,
            "random_start": random_start,
            "population_size": population_size,
            "sample_size": sample_size,
            "actual_sample_size": actual_sample_size,
            "sampling_rate": round(sample_size / population_size * 100, 2)
        }

    def calculate_sample_size_from_rate(
        self,
        population_size: int,
        sampling_rate: float
    ) -> Dict[str, Any]:
        """
        根据抽样比例计算样本量和参数

        Args:
            population_size: 总体规模
            sampling_rate: 抽样比例 (0-1)

        Returns:
            Dict: 包含样本量、间隔等参数
        """
        sample_size = max(1, int(population_size * sampling_rate))
        return self.calculate_parameters(population_size, sample_size)

    def select_samples(
        self,
        vouchers: List[Dict[str, Any]],
        interval: int,
        random_start: int
    ) -> List[Dict[str, Any]]:
        """
        系统抽样选样

        从随机起点开始，每隔interval个选取一个样本

        Args:
            vouchers: 凭证列表
            interval: 抽样间隔
            random_start: 随机起点（从1开始）

        Returns:
            List: 选中的样本列表
        """
        if interval <= 0:
            return []

        samples = []
        n = len(vouchers)

        # 从随机起点开始，每隔interval选取一个
        # 注意：random_start是1-based，转换为0-based索引
        for i in range(random_start - 1, n, interval):
            if i < n:
                sample = {
                    **vouchers[i],
                    "selection_index": i + 1,
                    "selection_sequence": len(samples) + 1,
                    "selection_method": "Systematic"
                }
                samples.append(sample)

        return samples

    def project_error_rate(
        self,
        error_count: int,
        sample_size: int,
        population_size: int,
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        系统抽样误差率推断

        使用正态分布近似进行推断

        Args:
            error_count: 样本中的错报笔数
            sample_size: 样本量
            population_size: 总体规模
            confidence_level: 置信水平

        Returns:
            Dict: 推断结果
        """
        if sample_size <= 0:
            return {
                "sample_error_rate": 0,
                "confidence_interval": {"lower": 0, "upper": 0},
                "projected_errors": {"lower": 0, "upper": 0},
                "error": "样本量必须大于0"
            }

        # 样本误差率
        sample_error_rate = error_count / sample_size

        # Z值表
        z_values = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        z = z_values.get(confidence_level, 1.96)

        # 标准误差
        if sample_error_rate == 0:
            # 使用Wilson区间下界修正
            se = math.sqrt(3.841459 / (sample_size * 4))  # 近似
        elif sample_error_rate == 1:
            se = math.sqrt(3.841459 / (sample_size * 4))  # 近似
        else:
            se = math.sqrt(sample_error_rate * (1 - sample_error_rate) / sample_size)

        # 有限总体校正因子
        if population_size > sample_size:
            fpc = math.sqrt((population_size - sample_size) / (population_size - 1))
        else:
            fpc = 1

        se_adjusted = se * fpc

        # 置信区间
        lower_rate = max(0, sample_error_rate - z * se_adjusted)
        upper_rate = min(1, sample_error_rate + z * se_adjusted)

        # 推断误差笔数
        projected_errors_lower = int(lower_rate * population_size)
        projected_errors_upper = int(upper_rate * population_size)

        return {
            "sample_error_rate": round(sample_error_rate, 4),
            "confidence_interval": {
                "lower": round(lower_rate, 4),
                "upper": round(upper_rate, 4)
            },
            "projected_errors": {
                "lower": projected_errors_lower,
                "upper": projected_errors_upper
            },
            "standard_error": round(se_adjusted, 4),
            "confidence_level": confidence_level,
            "z_value": z,
            "fpc": round(fpc, 4)
        }

    def project_amount(
        self,
        error_amount: float,
        sample_amount: float,
        population_amount: float,
        sample_size: int,
        population_size: int,
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        金额推断

        根据样本错报金额推断总体错报金额

        Args:
            error_amount: 样本错报金额
            sample_amount: 样本总金额
            population_amount: 总体金额
            sample_size: 样本量
            population_size: 总体规模
            confidence_level: 置信水平

        Returns:
            Dict: 金额推断结果
        """
        if sample_amount <= 0:
            return {
                "projected_amount": 0,
                "confidence_interval": {"lower": 0, "upper": 0},
                "error": "样本金额必须大于0"
            }

        # 样本错报率
        error_rate = error_amount / sample_amount

        # 推断总体错报金额（点估计）
        projected_amount = error_rate * population_amount

        # Z值
        z_values = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        z = z_values.get(confidence_level, 1.96)

        # 标准误差（金额）
        se = math.sqrt(error_rate * (1 - error_rate) / sample_size) * population_amount / population_size * population_size

        # 有限总体校正
        if population_size > sample_size:
            fpc = math.sqrt((population_size - sample_size) / (population_size - 1))
            se_adjusted = se * fpc
        else:
            se_adjusted = se

        # 置信区间
        lower_amount = max(0, projected_amount - z * se_adjusted)
        upper_amount = projected_amount + z * se_adjusted

        return {
            "projected_amount": round(projected_amount, 2),
            "confidence_interval": {
                "lower": round(lower_amount, 2),
                "upper": round(upper_amount, 2)
            },
            "error_rate": round(error_rate, 4),
            "sample_amount": sample_amount,
            "population_amount": population_amount
        }


def preview_systematic_sampling(
    population_size: int,
    sample_size: int = None,
    sampling_rate: float = None
) -> Dict[str, Any]:
    """
    预览系统抽样参数（便捷函数）

    Args:
        population_size: 总体规模
        sample_size: 样本量（与sampling_rate二选一）
        sampling_rate: 抽样比例（与sample_size二选一）

    Returns:
        Dict: 预览结果
    """
    sampler = SystematicSampler()

    if sample_size is not None:
        return sampler.calculate_parameters(population_size, sample_size)
    elif sampling_rate is not None:
        return sampler.calculate_sample_size_from_rate(population_size, sampling_rate)
    else:
        # 默认10%抽样率
        return sampler.calculate_sample_size_from_rate(population_size, 0.1)