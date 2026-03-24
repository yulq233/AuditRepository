"""
核心配置模块
"""
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache
import os


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    APP_NAME: str = "AI审计抽凭助手"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 数据库配置
    DATABASE_PATH: str = "data/db/audit.db"

    # 文件存储配置
    ATTACHMENT_PATH: str = "data/attachments"
    OCR_CACHE_PATH: str = "data/ocr"
    PAPER_PATH: str = "data/papers"

    # CORS配置
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]

    # JWT认证配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时

    # AI模型配置
    AI_CONFIG_PATH: str = "config/ai_config.yaml"
    DEFAULT_AI_PROVIDER: str = "ollama"

    # OCR配置
    OCR_PROVIDER: str = "paddleocr"
    OCR_LANGUAGE: str = "ch"

    # 文件上传配置
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".jpg", ".jpeg", ".png", ".xlsx", ".xls", ".csv"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()