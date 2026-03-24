"""
核心配置模块
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
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

    # ==================== AI模型配置 ====================
    # 默认AI提供商
    AI_PROVIDER: str = "qwen"

    # 默认模型名称
    AI_DEFAULT_MODEL: str = "qwen3.5-plus"

    # AI温度参数
    AI_TEMPERATURE: float = 0.7

    # AI最大输出token数
    AI_MAX_TOKENS: int = 2048

    # 可用模型列表(逗号分隔的字符串)
    AI_AVAILABLE_MODELS: str = "qwen3.5-plus,kimi-k2.5,MiniMax-M2.5,qwen3-max-2026-01-23"

    # 通义千问配置
    QWEN_API_KEY: Optional[str] = None
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # Ollama配置
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_DEFAULT_MODEL: str = "qwen2.5:14b"

    # 文心一言配置
    ERNIE_API_KEY: Optional[str] = None
    ERNIE_SECRET_KEY: Optional[str] = None

    # 智谱GLM配置
    ZHIPU_API_KEY: Optional[str] = None

    # OCR配置
    OCR_PROVIDER: str = "paddleocr"
    OCR_LANGUAGE: str = "ch"

    # 文件上传配置
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".jpg", ".jpeg", ".png", ".xlsx", ".xls", ".csv"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略额外的环境变量

    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        if self.AI_AVAILABLE_MODELS:
            return [m.strip() for m in self.AI_AVAILABLE_MODELS.split(",") if m.strip()]
        return ["qwen3.5-plus"]

    def get_model_info(self, model: str) -> dict:
        """获取模型详细信息"""
        model_configs = {
            "qwen3.5-plus": {
                "name": "Qwen3.5 Plus",
                "description": "通义千问3.5 Plus版本，性价比高，适合日常审计分析",
                "max_tokens": 32768,
                "supports_stream": True,
            },
            "kimi-k2.5": {
                "name": "Kimi K2.5",
                "description": "Moonshot Kimi K2.5模型，长文本理解能力强",
                "max_tokens": 128000,
                "supports_stream": True,
            },
            "MiniMax-M2.5": {
                "name": "MiniMax M2.5",
                "description": "MiniMax M2.5模型，推理能力强",
                "max_tokens": 65536,
                "supports_stream": True,
            },
            "qwen3-max-2026-01-23": {
                "name": "Qwen3 Max",
                "description": "通义千问3 Max版本，最强推理能力",
                "max_tokens": 32768,
                "supports_stream": True,
            },
        }
        return model_configs.get(model, {
            "name": model,
            "description": "自定义模型",
            "max_tokens": 2048,
            "supports_stream": True,
        })


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()