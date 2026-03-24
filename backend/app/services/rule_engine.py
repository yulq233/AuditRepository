"""
抽凭规则引擎
支持规则组合、条件判断、执行日志
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import uuid

from app.core.database import get_db_cursor, get_db


class RuleType(str, Enum):
    """规则类型"""
    RANDOM = "random"          # 随机抽样
    AMOUNT = "amount"          # 金额抽样
    SUBJECT = "subject"        # 科目抽样
    DATE = "date"              # 日期抽样
    COMPOSITE = "composite"    # 组合规则
    AI = "ai"                  # AI智能抽样


class LogicalOperator(str, Enum):
    """逻辑运算符"""
    AND = "and"
    OR = "or"
    NOT = "not"


class ComparisonOperator(str, Enum):
    """比较运算符"""
    EQ = "=="          # 等于
    NE = "!="          # 不等于
    GT = ">"           # 大于
    GE = ">="          # 大于等于
    LT = "<"           # 小于
    LE = "<="          # 小于等于
    IN = "in"          # 包含
    NOT_IN = "not_in"  # 不包含
    LIKE = "like"      # 模糊匹配
    BETWEEN = "between"  # 区间


@dataclass
class RuleCondition:
    """规则条件"""
    field: str                    # 字段名
    operator: ComparisonOperator  # 比较运算符
    value: Any                    # 比较值

    def evaluate(self, data: Dict[str, Any]) -> bool:
        """评估条件"""
        field_value = data.get(self.field)

        if field_value is None:
            return False

        if self.operator == ComparisonOperator.EQ:
            return field_value == self.value

        elif self.operator == ComparisonOperator.NE:
            return field_value != self.value

        elif self.operator == ComparisonOperator.GT:
            return field_value > self.value

        elif self.operator == ComparisonOperator.GE:
            return field_value >= self.value

        elif self.operator == ComparisonOperator.LT:
            return field_value < self.value

        elif self.operator == ComparisonOperator.LE:
            return field_value <= self.value

        elif self.operator == ComparisonOperator.IN:
            return field_value in self.value

        elif self.operator == ComparisonOperator.NOT_IN:
            return field_value not in self.value

        elif self.operator == ComparisonOperator.LIKE:
            return self.value in str(field_value)

        elif self.operator == ComparisonOperator.BETWEEN:
            min_val, max_val = self.value
            return min_val <= field_value <= max_val

        return False


@dataclass
class RuleResult:
    """规则执行结果"""
    rule_id: str
    rule_name: str
    matched_count: int
    total_count: int
    sample_ids: List[str]
    execution_time: float
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class BaseRule(ABC):
    """规则基类"""

    def __init__(self, rule_id: str, name: str, rule_type: RuleType):
        self.rule_id = rule_id
        self.name = name
        self.rule_type = rule_type
        self.conditions: List[RuleCondition] = []
        self.is_active = True

    @abstractmethod
    def evaluate(self, vouchers: List[Dict[str, Any]]) -> List[str]:
        """评估规则，返回匹配的凭证ID列表"""
        pass

    def add_condition(self, condition: RuleCondition):
        """添加条件"""
        self.conditions.append(condition)

    def check_conditions(self, voucher: Dict[str, Any]) -> bool:
        """检查所有条件（AND逻辑）"""
        if not self.conditions:
            return True
        return all(cond.evaluate(voucher) for cond in self.conditions)


class RandomSamplingRule(BaseRule):
    """随机抽样规则"""

    def __init__(
        self,
        rule_id: str,
        name: str,
        percentage: float = 10,
        sample_size: Optional[int] = None
    ):
        super().__init__(rule_id, name, RuleType.RANDOM)
        self.percentage = percentage
        self.sample_size = sample_size

    def evaluate(self, vouchers: List[Dict[str, Any]]) -> List[str]:
        """随机抽取"""
        import random

        # 先应用条件筛选
        filtered = [v for v in vouchers if self.check_conditions(v)]

        # 计算样本量
        if self.sample_size:
            n = min(self.sample_size, len(filtered))
        else:
            n = max(1, int(len(filtered) * self.percentage / 100))

        # 随机抽取
        sampled = random.sample(filtered, min(n, len(filtered)))

        return [v["id"] for v in sampled]


class AmountSamplingRule(BaseRule):
    """金额抽样规则"""

    def __init__(
        self,
        rule_id: str,
        name: str,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        percentage: float = 100,
        top_n: Optional[int] = None
    ):
        super().__init__(rule_id, name, RuleType.AMOUNT)
        self.min_amount = min_amount
        self.max_amount = max_amount
        self.percentage = percentage
        self.top_n = top_n

    def evaluate(self, vouchers: List[Dict[str, Any]]) -> List[str]:
        """按金额抽取"""
        # 先应用条件筛选
        filtered = [v for v in vouchers if self.check_conditions(v)]

        # 按金额范围筛选
        if self.min_amount is not None:
            filtered = [v for v in filtered if v.get("amount") and v["amount"] >= self.min_amount]

        if self.max_amount is not None:
            filtered = [v for v in filtered if v.get("amount") and v["amount"] <= self.max_amount]

        # 按金额排序
        filtered.sort(key=lambda x: x.get("amount") or 0, reverse=True)

        # 取前N条或按比例
        if self.top_n:
            result = filtered[:self.top_n]
        else:
            n = max(1, int(len(filtered) * self.percentage / 100))
            result = filtered[:n]

        return [v["id"] for v in result]


class SubjectSamplingRule(BaseRule):
    """科目抽样规则"""

    def __init__(
        self,
        rule_id: str,
        name: str,
        subject_codes: List[str],
        percentage: float = 100
    ):
        super().__init__(rule_id, name, RuleType.SUBJECT)
        self.subject_codes = subject_codes
        self.percentage = percentage

    def evaluate(self, vouchers: List[Dict[str, Any]]) -> List[str]:
        """按科目抽取"""
        import random

        # 先应用条件筛选
        filtered = [v for v in vouchers if self.check_conditions(v)]

        # 按科目筛选
        filtered = [v for v in filtered if v.get("subject_code") in self.subject_codes]

        # 按比例抽取
        n = max(1, int(len(filtered) * self.percentage / 100))
        sampled = random.sample(filtered, min(n, len(filtered)))

        return [v["id"] for v in sampled]


class DateSamplingRule(BaseRule):
    """日期抽样规则"""

    def __init__(
        self,
        rule_id: str,
        name: str,
        start_date,
        end_date,
        percentage: float = 100
    ):
        super().__init__(rule_id, name, RuleType.DATE)
        self.start_date = start_date
        self.end_date = end_date
        self.percentage = percentage

    def evaluate(self, vouchers: List[Dict[str, Any]]) -> List[str]:
        """按日期范围抽取"""
        import random

        # 先应用条件筛选
        filtered = [v for v in vouchers if self.check_conditions(v)]

        # 按日期筛选
        filtered = [
            v for v in filtered
            if v.get("voucher_date")
            and self.start_date <= v["voucher_date"] <= self.end_date
        ]

        # 按比例抽取
        n = max(1, int(len(filtered) * self.percentage / 100))
        sampled = random.sample(filtered, min(n, len(filtered)))

        return [v["id"] for v in sampled]


class CompositeRule(BaseRule):
    """组合规则"""

    def __init__(
        self,
        rule_id: str,
        name: str,
        operator: LogicalOperator = LogicalOperator.AND
    ):
        super().__init__(rule_id, name, RuleType.COMPOSITE)
        self.operator = operator
        self.sub_rules: List[BaseRule] = []

    def add_rule(self, rule: BaseRule):
        """添加子规则"""
        self.sub_rules.append(rule)

    def evaluate(self, vouchers: List[Dict[str, Any]]) -> List[str]:
        """组合评估"""
        if not self.sub_rules:
            return [v["id"] for v in vouchers]

        # 获取每个子规则的结果
        results = [set(rule.evaluate(vouchers)) for rule in self.sub_rules]

        if self.operator == LogicalOperator.AND:
            matched = set.intersection(*results)
        elif self.operator == LogicalOperator.OR:
            matched = set.union(*results)
        elif self.operator == LogicalOperator.NOT:
            all_ids = {v["id"] for v in vouchers}
            matched = all_ids - results[0] if results else all_ids
        else:
            matched = results[0] if results else set()

        return list(matched)


class RuleEngine:
    """规则引擎"""

    # Maximum in-memory log entries to prevent memory bloat
    MAX_LOG_ENTRIES = 1000

    def __init__(self):
        self.rules: Dict[str, BaseRule] = {}
        self.execution_logs: List[Dict[str, Any]] = []

    def register_rule(self, rule: BaseRule):
        """注册规则"""
        self.rules[rule.rule_id] = rule

    def unregister_rule(self, rule_id: str):
        """注销规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]

    def execute(
        self,
        rule_id: str,
        vouchers: List[Dict[str, Any]],
        save_log: bool = True
    ) -> RuleResult:
        """执行规则"""
        import time

        start_time = time.time()

        if rule_id not in self.rules:
            return RuleResult(
                rule_id=rule_id,
                rule_name="Unknown",
                matched_count=0,
                total_count=len(vouchers),
                sample_ids=[],
                execution_time=0,
                error=f"规则不存在: {rule_id}"
            )

        rule = self.rules[rule_id]

        try:
            matched_ids = rule.evaluate(vouchers)
            execution_time = time.time() - start_time

            result = RuleResult(
                rule_id=rule_id,
                rule_name=rule.name,
                matched_count=len(matched_ids),
                total_count=len(vouchers),
                sample_ids=matched_ids,
                execution_time=execution_time
            )

            if save_log:
                self._log_execution(result)

            return result

        except Exception as e:
            execution_time = time.time() - start_time

            result = RuleResult(
                rule_id=rule_id,
                rule_name=rule.name,
                matched_count=0,
                total_count=len(vouchers),
                sample_ids=[],
                execution_time=execution_time,
                error=str(e)
            )

            if save_log:
                self._log_execution(result)

            return result

    def execute_batch(
        self,
        rule_ids: List[str],
        vouchers: List[Dict[str, Any]],
        operator: LogicalOperator = LogicalOperator.OR
    ) -> RuleResult:
        """批量执行规则并合并结果"""
        import time

        start_time = time.time()
        all_results = []

        for rule_id in rule_ids:
            result = self.execute(rule_id, vouchers, save_log=False)
            all_results.append(result)

        # 合并结果
        matched_sets = [set(r.sample_ids) for r in all_results if not r.error]

        if operator == LogicalOperator.AND:
            final_matched = set.intersection(*matched_sets) if matched_sets else set()
        else:  # OR
            final_matched = set.union(*matched_sets) if matched_sets else set()

        execution_time = time.time() - start_time

        return RuleResult(
            rule_id="batch",
            rule_name=f"批量执行({','.join(rule_ids)})",
            matched_count=len(final_matched),
            total_count=len(vouchers),
            sample_ids=list(final_matched),
            execution_time=execution_time,
            details={"rule_results": [r.__dict__ for r in all_results]}
        )

    def _log_execution(self, result: RuleResult):
        """记录执行日志"""
        log_entry = {
            "id": str(uuid.uuid4()),
            "rule_id": result.rule_id,
            "rule_name": result.rule_name,
            "matched_count": result.matched_count,
            "total_count": result.total_count,
            "execution_time": result.execution_time,
            "error": result.error,
            "timestamp": datetime.now().isoformat()
        }
        self.execution_logs.append(log_entry)

        # Evict old entries if exceeding max size (circular buffer behavior)
        if len(self.execution_logs) > self.MAX_LOG_ENTRIES:
            self.execution_logs = self.execution_logs[-self.MAX_LOG_ENTRIES:]

        # 同时保存到数据库
        self._save_log_to_db(log_entry)

    def _save_log_to_db(self, log: Dict[str, Any]):
        """保存日志到数据库"""
        try:
            with get_db_cursor() as cursor:
                # 确保日志表存在
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS rule_execution_logs (
                        id VARCHAR PRIMARY KEY,
                        rule_id VARCHAR,
                        rule_name VARCHAR,
                        matched_count INTEGER,
                        total_count INTEGER,
                        execution_time FLOAT,
                        error TEXT,
                        timestamp TIMESTAMP
                    )
                """)

                cursor.execute(
                    """
                    INSERT INTO rule_execution_logs
                    (id, rule_id, rule_name, matched_count, total_count, execution_time, error, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        log["id"],
                        log["rule_id"],
                        log["rule_name"],
                        log["matched_count"],
                        log["total_count"],
                        log["execution_time"],
                        log["error"],
                        log["timestamp"]
                    ]
                )
                get_db().commit()
        except Exception as e:
            print(f"保存日志失败: {e}")

    def get_logs(self, rule_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取执行日志"""
        try:
            with get_db_cursor() as cursor:
                if rule_id:
                    cursor.execute(
                        """
                        SELECT id, rule_id, rule_name, matched_count, total_count,
                               execution_time, error, timestamp
                        FROM rule_execution_logs
                        WHERE rule_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        [rule_id, limit]
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, rule_id, rule_name, matched_count, total_count,
                               execution_time, error, timestamp
                        FROM rule_execution_logs
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        [limit]
                    )

                rows = cursor.fetchall()

                return [
                    {
                        "id": row[0],
                        "rule_id": row[1],
                        "rule_name": row[2],
                        "matched_count": row[3],
                        "total_count": row[4],
                        "execution_time": row[5],
                        "error": row[6],
                        "timestamp": row[7]
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"获取日志失败: {e}")
            return []


# 规则工厂
class RuleFactory:
    """规则工厂"""

    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> BaseRule:
        """从配置创建规则"""
        rule_type = config.get("rule_type")
        rule_id = config.get("id", str(uuid.uuid4()))
        name = config.get("name", "Unnamed Rule")
        rule_config = config.get("rule_config", {})

        if rule_type == RuleType.RANDOM.value:
            return RandomSamplingRule(
                rule_id=rule_id,
                name=name,
                percentage=rule_config.get("percentage", 10),
                sample_size=rule_config.get("sample_size")
            )

        elif rule_type == RuleType.AMOUNT.value:
            return AmountSamplingRule(
                rule_id=rule_id,
                name=name,
                min_amount=rule_config.get("min_amount"),
                max_amount=rule_config.get("max_amount"),
                percentage=rule_config.get("percentage", 100),
                top_n=rule_config.get("top_n")
            )

        elif rule_type == RuleType.SUBJECT.value:
            return SubjectSamplingRule(
                rule_id=rule_id,
                name=name,
                subject_codes=rule_config.get("subject_codes", []),
                percentage=rule_config.get("percentage", 100)
            )

        elif rule_type == RuleType.DATE.value:
            return DateSamplingRule(
                rule_id=rule_id,
                name=name,
                start_date=rule_config.get("start_date"),
                end_date=rule_config.get("end_date"),
                percentage=rule_config.get("percentage", 100)
            )

        elif rule_type == RuleType.COMPOSITE.value:
            rule = CompositeRule(
                rule_id=rule_id,
                name=name,
                operator=LogicalOperator(rule_config.get("operator", "and"))
            )

            # 添加子规则
            for sub_config in rule_config.get("sub_rules", []):
                sub_rule = RuleFactory.create_from_config(sub_config)
                rule.add_rule(sub_rule)

            return rule

        else:
            raise ValueError(f"不支持的规则类型: {rule_type}")


# 全局规则引擎实例
rule_engine = RuleEngine()