"""
凭证数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, date


class VoucherBase(BaseModel):
    """凭证基础模型"""
    voucher_no: str = Field(..., description="凭证编号")
    voucher_date: Optional[date] = Field(None, description="凭证日期")
    amount: Optional[float] = Field(None, ge=0, description="金额")
    subject_code: Optional[str] = Field(None, description="科目代码")
    subject_name: Optional[str] = Field(None, description="科目名称")
    description: Optional[str] = Field(None, description="摘要")
    counterparty: Optional[str] = Field(None, description="交易对手")


class VoucherCreate(VoucherBase):
    """创建凭证"""
    raw_data: Optional[Dict[str, Any]] = Field(None, description="原始数据")


class Voucher(VoucherBase):
    """凭证完整模型"""
    id: str
    project_id: str
    attachment_path: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True