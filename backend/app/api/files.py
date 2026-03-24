"""
文件服务API
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, Response
from typing import Optional

from app.services.storage_service import storage_service
from app.core.auth import get_current_user

router = APIRouter()


@router.get("/{path:path}")
async def get_file(
    path: str,
    download: bool = False,
    current_user = Depends(get_current_user)
):
    """
    获取文件

    Args:
        path: 文件相对路径
        download: 是否以附件形式下载
    """
    try:
        # 获取文件完整路径
        full_path = storage_service.backend.get_full_path(path)

        if not storage_service.exists(path):
            raise HTTPException(status_code=404, detail="文件不存在")

        # 获取文件信息
        file_info = storage_service.backend.get_file_info(path)

        # 读取文件
        file_data = storage_service.read(path)

        # 根据扩展名设置Content-Type
        content_type = _get_content_type(file_info["extension"])

        headers = {}
        if download:
            filename = path.split("/")[-1]
            headers["Content-Disposition"] = f'attachment; filename="{filename}"'

        return Response(
            content=file_data,
            media_type=content_type,
            headers=headers if headers else None
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="文件不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")


@router.delete("/{path:path}")
async def delete_file(path: str, current_user = Depends(get_current_user)):
    """删除文件"""
    if not storage_service.exists(path):
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        storage_service.delete(path)
        return {"message": "文件删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")


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
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    return content_types.get(extension.lower(), "application/octet-stream")