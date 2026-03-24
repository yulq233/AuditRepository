"""
文件存储服务
支持本地存储和阿里云OSS
"""
import os
import uuid
import hashlib
import aiofiles
from pathlib import Path
from typing import Optional, BinaryIO, Tuple
from datetime import datetime

from app.core.config import settings


class StorageBackend:
    """存储后端基类"""

    def save(self, file_data: bytes, path: str) -> str:
        raise NotImplementedError

    def read(self, path: str) -> bytes:
        raise NotImplementedError

    def delete(self, path: str) -> bool:
        raise NotImplementedError

    def exists(self, path: str) -> bool:
        raise NotImplementedError

    def get_url(self, path: str) -> str:
        raise NotImplementedError


class LocalStorage(StorageBackend):
    """本地文件存储"""

    def __init__(self, base_path: str = None):
        self.base_path = base_path or settings.ATTACHMENT_PATH
        os.makedirs(self.base_path, exist_ok=True)

    def _get_full_path(self, path: str) -> str:
        """获取完整路径"""
        return os.path.join(self.base_path, path)

    def save(self, file_data: bytes, path: str) -> str:
        """保存文件"""
        full_path = self._get_full_path(path)

        # 确保目录存在
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, 'wb') as f:
            f.write(file_data)

        return path

    async def save_async(self, file_data: bytes, path: str) -> str:
        """异步保存文件"""
        full_path = self._get_full_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        async with aiofiles.open(full_path, 'wb') as f:
            await f.write(file_data)

        return path

    def read(self, path: str) -> bytes:
        """读取文件"""
        full_path = self._get_full_path(path)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"文件不存在: {path}")

        with open(full_path, 'rb') as f:
            return f.read()

    async def read_async(self, path: str) -> bytes:
        """异步读取文件"""
        full_path = self._get_full_path(path)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"文件不存在: {path}")

        async with aiofiles.open(full_path, 'rb') as f:
            return await f.read()

    def delete(self, path: str) -> bool:
        """删除文件"""
        full_path = self._get_full_path(path)

        if os.path.exists(full_path):
            os.remove(full_path)
            return True

        return False

    def exists(self, path: str) -> bool:
        """检查文件是否存在"""
        return os.path.exists(self._get_full_path(path))

    def get_url(self, path: str) -> str:
        """获取文件访问URL（本地存储返回相对路径）"""
        return f"/api/files/{path}"

    def get_full_path(self, path: str) -> str:
        """获取文件完整路径"""
        return self._get_full_path(path)

    def list_files(self, prefix: str = "") -> list:
        """列出指定前缀的所有文件"""
        full_prefix = self._get_full_path(prefix)

        if not os.path.exists(full_prefix):
            return []

        files = []
        for root, _, filenames in os.walk(full_prefix):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, self.base_path)
                files.append(rel_path)

        return files

    def get_file_info(self, path: str) -> dict:
        """获取文件信息"""
        full_path = self._get_full_path(path)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"文件不存在: {path}")

        stat = os.stat(full_path)

        return {
            "path": path,
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime),
            "modified_at": datetime.fromtimestamp(stat.st_mtime),
            "extension": os.path.splitext(path)[1].lower()
        }


class OSSStorage(StorageBackend):
    """阿里云OSS存储"""

    def __init__(
        self,
        access_key_id: str,
        access_key_secret: str,
        endpoint: str,
        bucket_name: str
    ):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.endpoint = endpoint
        self.bucket_name = bucket_name
        self._bucket = None

    @property
    def bucket(self):
        """懒加载OSS Bucket"""
        if self._bucket is None:
            try:
                import oss2
                auth = oss2.Auth(self.access_key_id, self.access_key_secret)
                self._bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
            except ImportError:
                raise RuntimeError("请安装oss2: pip install oss2")

        return self._bucket

    def save(self, file_data: bytes, path: str) -> str:
        """保存文件到OSS"""
        self.bucket.put_object(path, file_data)
        return path

    def read(self, path: str) -> bytes:
        """从OSS读取文件"""
        result = self.bucket.get_object(path)
        return result.read()

    def delete(self, path: str) -> bool:
        """从OSS删除文件"""
        self.bucket.delete_object(path)
        return True

    def exists(self, path: str) -> bool:
        """检查文件是否存在"""
        return self.bucket.object_exists(path)

    def get_url(self, path: str, expires: int = 3600) -> str:
        """获取签名URL"""
        return self.bucket.sign_url('GET', path, expires)


class FileStorageService:
    """文件存储服务统一接口"""

    def __init__(self, backend: str = "local", **kwargs):
        if backend == "local":
            self.backend = LocalStorage(**kwargs)
        elif backend == "oss":
            self.backend = OSSStorage(**kwargs)
        else:
            raise ValueError(f"不支持的存储后端: {backend}")

    def generate_filename(self, original_name: str, prefix: str = "") -> str:
        """生成唯一文件名"""
        ext = os.path.splitext(original_name)[1]
        unique_id = uuid.uuid4().hex[:8]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{unique_id}{ext}"

        if prefix:
            return f"{prefix}/{filename}"

        return filename

    def compute_hash(self, file_data: bytes) -> str:
        """计算文件哈希"""
        return hashlib.sha256(file_data).hexdigest()

    def validate_file(self, filename: str, file_data: bytes) -> Tuple[bool, str]:
        """
        验证文件
        返回: (是否有效, 错误信息)
        """
        # 检查扩展名
        ext = os.path.splitext(filename)[1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            return False, f"不支持的文件类型: {ext}"

        # 检查文件大小
        if len(file_data) > settings.MAX_UPLOAD_SIZE:
            size_mb = len(file_data) / (1024 * 1024)
            max_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
            return False, f"文件大小({size_mb:.1f}MB)超过限制({max_mb}MB)"

        return True, ""

    def save(self, file_data: bytes, path: str) -> str:
        """保存文件"""
        return self.backend.save(file_data, path)

    async def save_async(self, file_data: bytes, path: str) -> str:
        """异步保存文件"""
        if hasattr(self.backend, 'save_async'):
            return await self.backend.save_async(file_data, path)
        return self.save(file_data, path)

    def read(self, path: str) -> bytes:
        """读取文件"""
        return self.backend.read(path)

    def delete(self, path: str) -> bool:
        """删除文件"""
        return self.backend.delete(path)

    def exists(self, path: str) -> bool:
        """检查文件是否存在"""
        return self.backend.exists(path)

    def get_url(self, path: str) -> str:
        """获取文件URL"""
        return self.backend.get_url(path)


# 默认存储服务实例
storage_service = FileStorageService(backend="local")