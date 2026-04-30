"""
统一错误处理模块

安全原则：
- 不向客户端暴露内部错误详情
- 记录完整错误信息到日志
- 返回用户友好的通用错误消息
"""
import logging
from fastapi import HTTPException, status
from typing import Optional

logger = logging.getLogger(__name__)


class AppException(Exception):
    """应用异常基类"""

    def __init__(
        self,
        message: str,
        detail: Optional[str] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        self.message = message
        self.detail = detail
        self.status_code = status_code
        super().__init__(self.message)


def handle_exception(
    e: Exception,
    operation: str = "操作",
    log_details: bool = True
) -> HTTPException:
    """
    统一处理异常，返回安全的HTTP响应

    Args:
        e: 异常对象
        operation: 操作名称（用于日志和用户消息）
        log_details: 是否记录详细错误日志

    Returns:
        HTTPException: 安全的HTTP异常响应
    """
    # 记录完整错误到日志
    if log_details:
        logger.error(f"{operation}失败: {type(e).__name__}: {str(e)}", exc_info=True)

    # 根据异常类型返回不同的响应
    if isinstance(e, HTTPException):
        # 已经是HTTP异常，直接返回
        return e

    if isinstance(e, AppException):
        return HTTPException(
            status_code=e.status_code,
            detail=e.message
        )

    if isinstance(e, FileNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="请求的资源不存在"
        )

    if isinstance(e, PermissionError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限执行此操作"
        )

    if isinstance(e, ValueError):
        # 输入验证错误，可以安全地返回给用户
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # 其他异常，返回通用错误消息
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"{operation}失败，请稍后重试或联系管理员"
    )


def safe_error_message(operation: str, error: Exception) -> str:
    """
    生成安全的错误消息

    Args:
        operation: 操作名称
        error: 异常对象

    Returns:
        str: 用户友好的错误消息
    """
    logger.error(f"{operation}失败: {str(error)}", exc_info=True)

    if isinstance(error, ValueError):
        return str(error)

    return f"{operation}失败，请稍后重试"


# 预定义的错误消息
ERROR_MESSAGES = {
    "file_read": "文件读取失败",
    "file_write": "文件保存失败",
    "file_delete": "文件删除失败",
    "import": "数据导入失败",
    "export": "数据导出失败",
    "ai_analysis": "AI分析失败",
    "ai_recognition": "AI识别失败",
    "ocr": "OCR识别失败",
    "database": "数据库操作失败",
    "validation": "数据验证失败",
    "not_found": "请求的资源不存在",
    "permission": "没有权限执行此操作",
}
