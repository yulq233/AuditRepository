"""
核心配置模块

敏感配置说明：
- SECRET_KEY: JWT签名密钥，生产环境必须通过环境变量设置
- API Key: 各AI供应商的API密钥，通过环境变量配置
- 所有敏感信息不应在代码中硬编码，应使用 .env 文件或环境变量
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache
import os
import warnings


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    APP_NAME: str = "AI审计抽凭助手"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False  # 生产环境默认关闭调试

    # 数据库配置
    DATABASE_PATH: str = "data/db/audit.db"

    # 文件存储配置
    ATTACHMENT_PATH: str = "data/attachments"
    OCR_CACHE_PATH: str = "data/ocr"
    PAPER_PATH: str = "data/papers"

    # CORS配置 - 生产环境应通过环境变量配置
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    # ==================== JWT认证配置 ====================
    # 安全警告: SECRET_KEY 必须通过环境变量设置，不应硬编码
    # 生产环境必须设置强密钥（至少32字符）
    SECRET_KEY: str = ""  # 默认为空，强制从环境变量读取
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1小时，降低安全风险

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
    AI_AVAILABLE_MODELS: str = "qwen3.5-plus,qwen3.5-plus-2026-02-15,kimi-k2.5,MiniMax-M2.5,qwen3-max-2026-01-23"

    # ==================== AI供应商配置 ====================
    # 安全警告: 所有API Key必须通过环境变量配置，不在此硬编码

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
    ZHIPU_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"

    # OCR配置
    OCR_PROVIDER: str = "paddleocr"
    OCR_LANGUAGE: str = "ch"

    # ==================== AI模型场景化配置 ====================
    # 图片/PDF识别专用配置（可选，不配置则使用供应商全局配置）
    AI_RECOGNITION_PROVIDER: Optional[str] = None
    AI_RECOGNITION_MODEL: Optional[str] = None
    AI_RECOGNITION_API_KEY: Optional[str] = None
    AI_RECOGNITION_BASE_URL: Optional[str] = None
    AI_RECOGNITION_TEMPERATURE: float = 0.3

    # 风险分析专用配置（可选，不配置则使用供应商全局配置）
    AI_RISK_ANALYSIS_PROVIDER: Optional[str] = None
    AI_RISK_ANALYSIS_MODEL: Optional[str] = None
    AI_RISK_ANALYSIS_API_KEY: Optional[str] = None
    AI_RISK_ANALYSIS_BASE_URL: Optional[str] = None
    AI_RISK_ANALYSIS_TEMPERATURE: float = 0.3

    # 通用AI服务专用配置（可选，不配置则使用供应商全局配置）
    AI_GENERAL_PROVIDER: Optional[str] = None
    AI_GENERAL_MODEL: Optional[str] = None
    AI_GENERAL_API_KEY: Optional[str] = None
    AI_GENERAL_BASE_URL: Optional[str] = None
    AI_GENERAL_TEMPERATURE: float = 0.7

    # ==================== 模型定义（按用途分类） ====================
    # 通用对话/分析模型列表
    AI_GENERAL_MODELS: str = "qwen3.5-plus,qwen3.5-plus-2026-02-15,qwen3.5-flash,qwen3.5-122b-a10b,qwen3.5-35b-a3b"

    # 视觉/识别模型列表（用于图片PDF识别）
    AI_VISION_MODELS: str = "qwen3.5-omni-plus,qwen3.5-omni-plus-realtime,qwen3.5-omni-plus-2026-03-15,qwen3.5-omni-flash-2026-03-15"

    # 风险分析模型列表
    AI_RISK_MODELS: str = "qwen3.5-plus,qwen3.5-plus-2026-02-15,qwen3-max,kimi-k2.5,MiniMax-M2.5,glm-4-flash"

    # 文件上传配置
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".jpg", ".jpeg", ".png", ".xlsx", ".xls", ".csv", ".html"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略额外的环境变量

    def get_available_models(self) -> List[str]:
        """获取可用模型列表（通用）"""
        if self.AI_AVAILABLE_MODELS:
            return [m.strip() for m in self.AI_AVAILABLE_MODELS.split(",") if m.strip()]
        return ["qwen3.5-plus"]

    def get_models_for_purpose(self, purpose: str = "general") -> List[str]:
        """
        根据用途获取可用模型列表

        Args:
            purpose: 用途类型 (general/recognition/risk_analysis)

        Returns:
            List[str]: 该用途可用的模型列表
        """
        if purpose == "recognition":
            models_str = self.AI_VISION_MODELS or "qwen-vl-max,glm-4v"
        elif purpose == "risk_analysis":
            models_str = self.AI_RISK_MODELS or self.AI_GENERAL_MODELS or "qwen3.5-plus"
        else:  # general
            models_str = self.AI_GENERAL_MODELS or self.AI_AVAILABLE_MODELS or "qwen3.5-plus"

        return [m.strip() for m in models_str.split(",") if m.strip()]

    def get_model_info(self, model: str) -> dict:
        """获取模型详细信息"""
        # 通用对话模型
        general_models = {
            "qwen3.5-plus": {
                "name": "Qwen3.5 Plus",
                "description": "通义千问3.5 Plus版本，性价比高，适合日常审计分析",
                "max_tokens": 32768,
                "supports_stream": True,
                "category": "general",
            },
            "qwen3.5-plus-2026-02-15": {
                "name": "Qwen3.5 Plus (2026-02-15)",
                "description": "通义千问3.5 Plus最新版本，增强推理能力",
                "max_tokens": 32768,
                "supports_stream": True,
                "category": "general",
            },
            "qwen3-max": {
                "name": "Qwen3 Max",
                "description": "通义千问3 Max版本，最强推理能力",
                "max_tokens": 32768,
                "supports_stream": True,
                "category": "general",
            },
            "kimi-k2.5": {
                "name": "Kimi K2.5",
                "description": "Moonshot Kimi K2.5模型，长文本理解能力强",
                "max_tokens": 128000,
                "supports_stream": True,
                "category": "general",
            },
            "MiniMax-M2.5": {
                "name": "MiniMax M2.5",
                "description": "MiniMax M2.5模型，推理能力强",
                "max_tokens": 65536,
                "supports_stream": True,
                "category": "general",
            },
            "glm-4-flash": {
                "name": "GLM-4 Flash",
                "description": "智谱GLM-4 Flash，快速响应，性价比高",
                "max_tokens": 4096,
                "supports_stream": True,
                "category": "general",
            },
            "glm-4": {
                "name": "GLM-4",
                "description": "智谱GLM-4，强大的推理和对话能力",
                "max_tokens": 8192,
                "supports_stream": True,
                "category": "general",
            },
        }

        # 视觉/识别模型
        vision_models = {
            "qwen-vl-max": {
                "name": "Qwen-VL Max",
                "description": "通义千问视觉模型Max版，强大的图片识别能力",
                "max_tokens": 8192,
                "supports_stream": True,
                "category": "vision",
                "supports_image": True,
            },
            "qwen-vl-plus": {
                "name": "Qwen-VL Plus",
                "description": "通义千问视觉模型Plus版，性价比高",
                "max_tokens": 8192,
                "supports_stream": True,
                "category": "vision",
                "supports_image": True,
            },
            "glm-4v": {
                "name": "GLM-4V",
                "description": "智谱GLM-4V视觉模型，支持OCR和图片理解",
                "max_tokens": 8192,
                "supports_stream": True,
                "category": "vision",
                "supports_image": True,
            },
            "glm-4v-flash": {
                "name": "GLM-4V Flash",
                "description": "智谱GLM-4V Flash，快速图片识别，适合OCR场景",
                "max_tokens": 4096,
                "supports_stream": True,
                "category": "vision",
                "supports_image": True,
            },
            "qwen2.5-ocr": {
                "name": "Qwen OCR",
                "description": "通义千问OCR专用模型，文档识别能力强",
                "max_tokens": 4096,
                "supports_stream": False,
                "category": "vision",
                "supports_image": True,
            },
        }

        # 合并所有模型配置
        all_models = {**general_models, **vision_models}

        return all_models.get(model, {
            "name": model,
            "description": "自定义模型",
            "max_tokens": 2048,
            "supports_stream": True,
            "category": "general",
        })

    def get_ai_config_for_purpose(self, purpose: str = "general") -> dict:
        """
        根据用途获取AI配置

        配置优先级（从高到低）：
        1. 用途专用配置（如 AI_RECOGNITION_API_KEY）
        2. 供应商全局配置（如 QWEN_API_KEY）
        3. 默认配置

        Args:
            purpose: 用途类型 (general/recognition/risk_analysis)

        Returns:
            Dict: AI配置字典，包含provider, model, temperature, api_key, base_url等
        """
        if purpose == "recognition":
            provider = self.AI_RECOGNITION_PROVIDER or self.AI_PROVIDER
            model = self.AI_RECOGNITION_MODEL or self.AI_DEFAULT_MODEL
            temperature = self.AI_RECOGNITION_TEMPERATURE
            # 优先使用用途专用API Key，其次使用供应商全局API Key
            api_key = self.AI_RECOGNITION_API_KEY or self._get_api_key_for_provider(provider)
            base_url = self.AI_RECOGNITION_BASE_URL or self._get_base_url_for_provider(provider)
        elif purpose == "risk_analysis":
            provider = self.AI_RISK_ANALYSIS_PROVIDER or self.AI_PROVIDER
            model = self.AI_RISK_ANALYSIS_MODEL or self.AI_DEFAULT_MODEL
            temperature = self.AI_RISK_ANALYSIS_TEMPERATURE
            api_key = self.AI_RISK_ANALYSIS_API_KEY or self._get_api_key_for_provider(provider)
            base_url = self.AI_RISK_ANALYSIS_BASE_URL or self._get_base_url_for_provider(provider)
        else:  # general
            provider = self.AI_GENERAL_PROVIDER or self.AI_PROVIDER
            model = self.AI_GENERAL_MODEL or self.AI_DEFAULT_MODEL
            temperature = self.AI_GENERAL_TEMPERATURE
            api_key = self.AI_GENERAL_API_KEY or self._get_api_key_for_provider(provider)
            base_url = self.AI_GENERAL_BASE_URL or self._get_base_url_for_provider(provider)

        return {
            "provider": provider,
            "model": model,
            "temperature": temperature,
            "max_tokens": self.AI_MAX_TOKENS,
            "api_key": api_key,
            "base_url": base_url
        }

    def _get_api_key_for_provider(self, provider: str) -> Optional[str]:
        """根据提供商获取API Key"""
        key_mapping = {
            "qwen": self.QWEN_API_KEY,
            "ernie": self.ERNIE_API_KEY,
            "zhipu": self.ZHIPU_API_KEY,
        }
        return key_mapping.get(provider.lower())

    def _get_base_url_for_provider(self, provider: str) -> Optional[str]:
        """根据提供商获取Base URL"""
        url_mapping = {
            "qwen": self.QWEN_BASE_URL,
            "ernie": "https://qianfan.baidubce.com/cms/compatible-mode/v1",
            "zhipu": self.ZHIPU_BASE_URL,
            "ollama": self.OLLAMA_BASE_URL,
        }
        return url_mapping.get(provider.lower())

    def validate_security_config(self) -> List[str]:
        """
        验证安全相关配置

        Returns:
            List[str]: 配置问题列表，空列表表示验证通过
        """
        issues = []

        # 检查 SECRET_KEY
        if not self.SECRET_KEY:
            issues.append("SECRET_KEY 未配置，JWT认证将无法使用")
        elif len(self.SECRET_KEY) < 32:
            issues.append(f"SECRET_KEY 长度过短({len(self.SECRET_KEY)}字符)，建议至少32字符")
        elif self.SECRET_KEY in ["your-secret-key-change-in-production", "secret", "test"]:
            issues.append(f"SECRET_KEY 使用了不安全的默认值")

        # 检查 DEBUG 模式
        if self.DEBUG:
            issues.append("DEBUG 模式已开启，生产环境应关闭")

        # 检查 AI 配置
        if self.AI_PROVIDER != "ollama":
            api_key = self._get_api_key_for_provider(self.AI_PROVIDER)
            if not api_key:
                issues.append(f"AI提供商 {self.AI_PROVIDER} 的 API_KEY 未配置")

        return issues

    def get_redacted_config(self) -> dict:
        """
        获取脱敏后的配置信息（用于日志输出）

        Returns:
            dict: 脱敏后的配置字典
        """
        def redact(value: Optional[str], show_length: bool = True) -> str:
            if not value:
                return "未配置"
            if len(value) <= 8:
                return "***"
            return f"{value[:4]}...{value[-4:]} ({len(value)}字符)"

        return {
            "SECRET_KEY": redact(self.SECRET_KEY),
            "QWEN_API_KEY": redact(self.QWEN_API_KEY),
            "ERNIE_API_KEY": redact(self.ERNIE_API_KEY),
            "ZHIPU_API_KEY": redact(self.ZHIPU_API_KEY),
            "AI_RECOGNITION_API_KEY": redact(self.AI_RECOGNITION_API_KEY),
            "AI_RISK_ANALYSIS_API_KEY": redact(self.AI_RISK_ANALYSIS_API_KEY),
            "AI_GENERAL_API_KEY": redact(self.AI_GENERAL_API_KEY),
        }


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()