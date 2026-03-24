"""
共享枚举定义
"""
from enum import Enum


class RiskLevel(str, Enum):
    """风险等级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    OVERDUE = "overdue"


class SamplingMethod(str, Enum):
    """抽样方法"""
    RANDOM = "random"
    STRATIFIED = "stratified"
    SYSTEMATIC = "systematic"
    JUDGMENT = "judgment"
    MONETARY_UNIT = "monetary_unit"


class MatchStatus(str, Enum):
    """匹配状态"""
    FULLY_MATCHED = "fully_matched"
    PARTIALLY_MATCHED = "partially_matched"
    NOT_MATCHED = "not_matched"
    EXCEPTION = "exception"


class ComplianceSeverity(str, Enum):
    """合规严重程度"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"