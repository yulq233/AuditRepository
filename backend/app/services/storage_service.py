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

    # 文件Magic Number签名（用于验证文件真实类型）
    MAGIC_SIGNATURES = {
        b'\xFF\xD8\xFF': 'jpeg',
        b'\x89PNG\r\n\x1a\n': 'png',
        b'GIF87a': 'gif',
        b'GIF89a': 'gif',
        b'BM': 'bmp',
        b'%PDF': 'pdf',
        b'PK\x03\x04': 'zip',  # xlsx, docx等实际上是zip格式
        b'\xD0\xCF\x11\xE0': 'ms_office',  # xls, doc等旧格式
    }

    # 扩展名与MIME类型映射
    EXTENSION_MIME = {
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.pdf': 'application/pdf',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.csv': 'text/csv',
        '.html': 'text/html',
        '.htm': 'text/html',
    }

    def _detect_file_type(self, file_data: bytes) -> str:
        """
        通过Magic Number检测文件真实类型

        Args:
            file_data: 文件数据（前几字节即可）

        Returns:
            str: 检测到的文件类型，未知返回 'unknown'
        """
        if len(file_data) < 8:
            return 'unknown'

        for signature, file_type in self.MAGIC_SIGNATURES.items():
            if file_data.startswith(signature):
                return file_type

        return 'unknown'

    def _validate_extension_match(self, ext: str, file_type: str) -> bool:
        """
        验证扩展名与文件类型是否匹配

        Args:
            ext: 文件扩展名
            file_type: 检测到的文件类型

        Returns:
            bool: 是否匹配
        """
        # Office文件（xlsx, xls）都是zip格式
        if file_type == 'zip':
            return ext in ['.xlsx', '.xls', '.zip']

        if file_type == 'ms_office':
            return ext in ['.xls', '.doc', '.ppt']

        # 图片类型映射
        image_map = {
            'jpeg': ['.jpg', '.jpeg'],
            'png': ['.png'],
            'gif': ['.gif'],
            'bmp': ['.bmp'],
        }

        if file_type in image_map:
            return ext in image_map[file_type]

        # PDF
        if file_type == 'pdf':
            return ext == '.pdf'

        # CSV和HTML无法通过Magic Number准确检测，允许通过
        if ext in ['.csv', '.html', '.htm']:
            return True

        return False

    def validate_file(self, filename: str, file_data: bytes) -> Tuple[bool, str]:
        """
        验证文件安全性

        检查项：
        1. 扩展名是否在允许列表
        2. 文件大小是否超限
        3. 文件内容是否与扩展名匹配（Magic Number检测）
        4. 文件名是否包含危险字符

        返回: (是否有效, 错误信息)
        """
        import re

        # 1. 检查文件名是否包含危险字符
        if re.search(r'[<>:"|?*\x00-\x1f]', filename):
            return False, "文件名包含非法字符"

        # 2. 检查扩展名
        ext = os.path.splitext(filename)[1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            return False, f"不支持的文件类型: {ext}"

        # 3. 检查文件大小
        if len(file_data) > settings.MAX_UPLOAD_SIZE:
            size_mb = len(file_data) / (1024 * 1024)
            max_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
            return False, f"文件大小({size_mb:.1f}MB)超过限制({max_mb}MB)"

        # 4. 检查文件内容是否与扩展名匹配
        file_type = self._detect_file_type(file_data)

        # 如果检测到文件类型，验证是否与扩展名匹配
        if file_type != 'unknown':
            if not self._validate_extension_match(ext, file_type):
                return False, f"文件内容({file_type})与扩展名({ext})不匹配"

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