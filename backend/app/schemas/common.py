"""
共享数据模型
"""
from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应基类"""
    total: int = Field(..., description="总数")
    items: List[T] = Field(default_factory=list, description="数据列表")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(20, description="每页数量")


class CommonResponse(BaseModel):
    """通用响应"""
    message: str = Field(..., description="响应消息")