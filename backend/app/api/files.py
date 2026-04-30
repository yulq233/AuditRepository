"""
文件服务API
"""
import os
import re
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse, Response
from typing import Optional

from app.services.storage_service import storage_service
from app.core.auth import get_current_user, get_current_user_optional, UserInDB
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def validate_path(path: str) -> str:
    """
    验证并规范化文件路径，防止路径遍历攻击

    Args:
        path: 用户提供的文件路径

    Returns:
        str: 规范化后的安全路径

    Raises:
        HTTPException: 路径不合法时抛出403错误
    """
    if not path:
        raise HTTPException(status_code=400, detail="文件路径不能为空")

    # 1. 检查危险字符
    dangerous_patterns = [
        r'\.\.',           # 父目录遍历
        r'^/',             # 绝对路径
        r'^\\',            # Windows绝对路径
        r'[\x00-\x1f]',    # 控制字符
        r'[<>:"|?*]',      # Windows保留字符
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, path):
            logger.warning(f"检测到非法路径访问尝试: {path}")
            raise HTTPException(status_code=403, detail="非法的文件路径")

    # 2. 规范化路径（移除多余的斜杠等）
    safe_path = os.path.normpath(path).lstrip('/\\')

    # 3. 再次检查规范化后的路径是否包含..
    if '..' in safe_path:
        raise HTTPException(status_code=403, detail="非法的文件路径")

    # 4. 验证最终路径在允许的目录内
    full_path = storage_service.backend.get_full_path(safe_path)
    base_path = os.path.abspath(settings.ATTACHMENT_PATH)

    # 确保解析后的路径仍在允许目录内
    if not os.path.abspath(full_path).startswith(base_path):
        logger.warning(f"路径遍历攻击尝试: {path} -> {full_path}")
        raise HTTPException(status_code=403, detail="访问被拒绝")

    return safe_path


@router.get("/{path:path}")
async def get_file(
    path: str,
    download: bool = Query(False, description="是否以附件形式下载"),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    获取文件

    Args:
        path: 文件相对路径
        download: 是否以附件形式下载
    """
    try:
        # 验证路径安全性
        safe_path = validate_path(path)

        if not storage_service.exists(safe_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        # 获取文件信息
        file_info = storage_service.backend.get_file_info(safe_path)

        # 读取文件
        file_data = storage_service.read(safe_path)

        # 根据扩展名设置Content-Type
        content_type = _get_content_type(file_info["extension"])

        headers = {}
        if download:
            filename = safe_path.split("/")[-1]
            headers["Content-Disposition"] = f'attachment; filename="{filename}"'

        return Response(
            content=file_data,
            media_type=content_type,
            headers=headers if headers else None
        )

    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="文件不存在")
    except Exception as e:
        logger.error(f"读取文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="文件读取失败")


@router.delete("/{path:path}")
async def delete_file(
    path: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """删除文件"""
    try:
        # 验证路径安全性
        safe_path = validate_path(path)

        if not storage_service.exists(safe_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        storage_service.delete(safe_path)
        return {"message": "文件删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="文件删除失败")


def _get_content_type(extension: str) -> str:
    """根据扩展名获取Content-Type"""
    content_types = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".csv": "text/csv",
        ".txt": "text/plain",
        ".html": "text/html",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    return content_types.get(extension.lower(), "application/octet-stream")