"""
API依赖项
共享的FastAPI依赖，减少代码重复
"""
from fastapi import Depends, HTTPException, status
from typing import Optional

from app.core.database import get_db_cursor


async def validate_project_exists(project_id: str) -> str:
    """
    验证项目是否存在的依赖

    Args:
        project_id: 项目ID

    Returns:
        str: 验证通过的项目ID

    Raises:
        HTTPException: 项目不存在时抛出404错误
    """
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM projects WHERE id = ?", [project_id])
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目不存在"
            )
    return project_id


class PaginationParams:
    """分页参数"""

    def __init__(self, page: int = 1, page_size: int = 20):
        self.page = max(1, page)
        self.page_size = min(max(1, page_size), 200)
        self.offset = (self.page - 1) * self.page_size


def get_pagination(
    page: int = 1,
    page_size: int = 20
) -> PaginationParams:
    """获取分页参数的依赖"""
    return PaginationParams(page=page, page_size=page_size)