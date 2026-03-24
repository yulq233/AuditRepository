"""
抽样数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class SamplingRuleBase(BaseModel):
    """抽凭规则基础模型"""
    name: str = Field(..., description="规则名称")
    rule_type: str = Field(..., description="规则类型")
    rule_config: Dict[str, Any] = Field(..., description="规则配置")


class SamplingRuleCreate(SamplingRuleBase):
    """创建抽凭规则"""
    pass


class SamplingRule(SamplingRuleBase):
    """抽凭规则完整模型"""
    id: str
    project_id: str
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class SampleBase(BaseModel):
    """抽样结果基础模型"""
    voucher_id: str
    risk_score: Optional[float] = Field(None, ge=0, le=100)
    reason: Optional[str] = None


class Sample(SampleBase):
    """抽样结果完整模型"""
    id: str
    project_id: str
    rule_id: str
    sampled_at: datetime

    class Config:
        from_attributes = True