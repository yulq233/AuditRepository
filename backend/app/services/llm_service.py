"""
LLM适配器框架
统一接口支持多种大语言模型：Ollama、通义千问、文心一言、智谱GLM等
模型配置从环境变量(.env)读取
自动记录AI调用日志，支持用量统计
"""
import os
import json
import httpx
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

from app.core.config import settings
from app.services.ai_usage_service import AIUsageTracker


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: str = "qwen"
    model: str = "qwen3.5-plus"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 180  # 增加到180秒，支持AI视觉识别等耗时操作


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str  # system, user, assistant
    content: str
    images: Optional[List[str]] = None  # base64编码的图片列表


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: str = "stop"
    raw_response: Dict[str, Any] = field(default_factory=dict)


class LLMAdapter(ABC):
    """LLM适配器基类"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=config.timeout)

    @abstractmethod
    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """聊天补全"""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """流式聊天补全"""
        pass

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """文本向量化"""
        pass

    async def chat_with_images(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """带图片的聊天补全（默认调用chat，子类可重写）"""
        return await self.chat(messages, temperature, max_tokens)
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """检查服务是否可用"""
        pass

    def _build_messages(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """构建消息列表"""
        return [{"role": m.role, "content": m.content} for m in messages]

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


class OllamaAdapter(LLMAdapter):
    """Ollama适配器"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or settings.OLLAMA_BASE_URL

    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """Ollama聊天补全"""
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": self.config.model,
            "messages": self._build_messages(messages),
            "stream": False,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens
            }
        }

        response = await self.client.post(url, json=payload)
        response.raise_for_status()

        data = response.json()

        return LLMResponse(
            content=data.get("message", {}).get("content", ""),
            model=self.config.model,
            provider="ollama",
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
            },
            raw_response=data
        )

    async def chat_stream(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """Ollama流式聊天"""
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": self.config.model,
            "messages": self._build_messages(messages),
            "stream": True,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens
            }
        }

        async with self.client.stream("POST", url, json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if "message" in data:
                        content = data["message"].get("content", "")
                        if content:
                            yield content

    async def embed(self, text: str) -> List[float]:
        """Ollama文本向量化"""
        url = f"{self.base_url}/api/embeddings"

        payload = {
            "model": self.config.model,
            "prompt": text
        }

        response = await self.client.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        return data.get("embedding", [])

    async def is_available(self) -> bool:
        """检查Ollama服务是否可用"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False


class QwenAdapter(LLMAdapter):
    """阿里云通义千问适配器
    支持模型: qwen3.5-plus, kimi-k2.5, MiniMax-M2.5, qwen3-max-2026-01-23
    支持百炼Coding Plan的Anthropic兼容模式
    """

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or settings.QWEN_BASE_URL
        self.api_key = config.api_key or settings.QWEN_API_KEY
        # 检测是否使用Anthropic兼容模式（百炼Coding Plan）
        self._is_anthropic_mode = "anthropic" in self.base_url.lower()

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        if self._is_anthropic_mode:
            # 百炼Coding Plan Anthropic兼容模式
            return {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
        else:
            # 标准OpenAI兼容模式
            return {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

    def _build_anthropic_messages(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """构建Anthropic格式消息（不包含system角色）"""
        result = []
        for m in messages:
            if m.role != "system":
                result.append({"role": m.role, "content": m.content})
        return result

    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """聊天补全"""
        if self._is_anthropic_mode:
            return await self._chat_anthropic(messages, temperature, max_tokens)
        else:
            return await self._chat_openai(messages, temperature, max_tokens)

    async def _chat_anthropic(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """Anthropic兼容模式聊天"""
        url = f"{self.base_url}/v1/messages"

        # 提取system消息
        system_content = None
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system_content = m.content
            else:
                chat_messages.append({"role": m.role, "content": m.content})

        payload = {
            "model": self.config.model,
            "max_tokens": max_tokens or self.config.max_tokens,
            "messages": chat_messages
        }
        if system_content:
            payload["system"] = system_content

        response = await self.client.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()

        data = response.json()

        # 解析Anthropic格式响应
        content_parts = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                content_parts.append(block.get("text", ""))

        content = "".join(content_parts)

        return LLMResponse(
            content=content,
            model=self.config.model,
            provider="qwen",
            usage={
                "input_tokens": data.get("usage", {}).get("input_tokens", 0),
                "output_tokens": data.get("usage", {}).get("output_tokens", 0),
            },
            finish_reason=data.get("stop_reason", "stop"),
            raw_response=data
        )

    async def _chat_openai(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """OpenAI兼容模式聊天"""
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.config.model,
            "messages": self._build_messages(messages),
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens
        }

        response = await self.client.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()

        data = response.json()
        choice = data.get("choices", [{}])[0]

        return LLMResponse(
            content=choice.get("message", {}).get("content", ""),
            model=self.config.model,
            provider="qwen",
            usage=data.get("usage", {}),
            finish_reason=choice.get("finish_reason", "stop"),
            raw_response=data
        )

    async def chat_stream(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """流式聊天补全"""
        if self._is_anthropic_mode:
            async for chunk in self._chat_stream_anthropic(messages, temperature, max_tokens):
                yield chunk
        else:
            async for chunk in self._chat_stream_openai(messages, temperature, max_tokens):
                yield chunk

    async def _chat_stream_anthropic(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """Anthropic兼容模式流式聊天"""
        url = f"{self.base_url}/v1/messages"

        chat_messages = []
        for m in messages:
            if m.role != "system":
                chat_messages.append({"role": m.role, "content": m.content})

        payload = {
            "model": self.config.model,
            "max_tokens": max_tokens or self.config.max_tokens,
            "messages": chat_messages,
            "stream": True
        }

        async with self.client.stream("POST", url, json=payload, headers=self._get_headers()) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text = delta.get("text", "")
                                if text:
                                    yield text
                    except json.JSONDecodeError:
                        continue

    async def _chat_stream_openai(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """OpenAI兼容模式流式聊天"""
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.config.model,
            "messages": self._build_messages(messages),
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": True
        }

        async with self.client.stream("POST", url, json=payload, headers=self._get_headers()) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    async def chat_with_images(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """带图片的聊天补全 - 使用视觉模型识别图片"""
        if self._is_anthropic_mode:
            return await self._chat_with_images_anthropic(messages, temperature, max_tokens)
        else:
            return await self._chat_with_images_openai(messages, temperature, max_tokens)

    async def _chat_with_images_anthropic(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """Anthropic兼容模式带图片的聊天"""
        url = f"{self.base_url}/v1/messages"

        # 构建消息，支持图片
        chat_messages = []
        for m in messages:
            if m.role == "system":
                continue
            content_parts = []
            # 添加文本
            if m.content:
                content_parts.append({"type": "text", "text": m.content})
            # 添加图片
            if m.images:
                for img_base64 in m.images:
                    content_parts.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": img_base64
                        }
                    })
            chat_messages.append({"role": m.role, "content": content_parts})

        # 提取system消息
        system_content = None
        for m in messages:
            if m.role == "system":
                system_content = m.content
                break

        payload = {
            "model": self.config.model,
            "max_tokens": max_tokens or self.config.max_tokens,
            "messages": chat_messages
        }
        if system_content:
            payload["system"] = system_content

        response = await self.client.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()

        data = response.json()

        # 解析响应
        content_parts = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                content_parts.append(block.get("text", ""))

        content = "".join(content_parts)

        return LLMResponse(
            content=content,
            model=self.config.model,
            provider="qwen",
            usage={
                "input_tokens": data.get("usage", {}).get("input_tokens", 0),
                "output_tokens": data.get("usage", {}).get("output_tokens", 0),
            },
            finish_reason=data.get("stop_reason", "stop"),
            raw_response=data
        )

    async def _chat_with_images_openai(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """OpenAI兼容模式带图片的聊天"""
        url = f"{self.base_url}/chat/completions"

        # 构建消息，支持图片
        chat_messages = []
        for m in messages:
            content_parts = []
            # 添加文本
            if m.content:
                content_parts.append({"type": "text", "text": m.content})
            # 添加图片
            if m.images:
                for img_base64 in m.images:
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_base64}"
                        }
                    })
            chat_messages.append({"role": m.role, "content": content_parts})

        # 添加system消息
        for m in messages:
            if m.role == "system":
                chat_messages.insert(0, {"role": "system", "content": m.content})
                break

        payload = {
            "model": self.config.model,
            "messages": chat_messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens
        }

        response = await self.client.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()

        data = response.json()
        choice = data.get("choices", [{}])[0]

        return LLMResponse(
            content=choice.get("message", {}).get("content", ""),
            model=self.config.model,
            provider="qwen",
            usage=data.get("usage", {}),
            finish_reason=choice.get("finish_reason", "stop"),
            raw_response=data
        )

    async def embed(self, text: str) -> List[float]:
        """文本向量化"""
        # Anthropic模式不支持embedding，返回空列表
        if self._is_anthropic_mode:
            return []

        url = f"{self.base_url}/embeddings"

        payload = {
            "model": "text-embedding-v2",
            "input": text
        }

        response = await self.client.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()

        data = response.json()
        return data.get("data", [{}])[0].get("embedding", [])

    async def is_available(self) -> bool:
        """检查API是否可用"""
        return self.api_key is not None


class ERNIEAdapter(LLMAdapter):
    """百度文心一言适配器"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_key = config.api_key or settings.ERNIE_API_KEY
        self.secret_key = settings.ERNIE_SECRET_KEY
        self._access_token = None
        self._token_expire_time = 0

    async def _get_access_token(self) -> str:
        """获取Access Token"""
        if self._access_token and datetime.now().timestamp() < self._token_expire_time:
            return self._access_token

        url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={self.api_key}&client_secret={self.secret_key}"

        response = await self.client.post(url)
        response.raise_for_status()

        data = response.json()
        self._access_token = data.get("access_token")
        self._token_expire_time = datetime.now().timestamp() + data.get("expires_in", 86400) - 300

        return self._access_token

    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """文心一言聊天补全"""
        access_token = await self._get_access_token()
        url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token={access_token}"

        payload = {
            "model": self.config.model,
            "messages": self._build_messages(messages),
            "temperature": temperature or self.config.temperature,
            "max_output_tokens": max_tokens or self.config.max_tokens
        }

        response = await self.client.post(url, json=payload)
        response.raise_for_status()

        data = response.json()

        return LLMResponse(
            content=data.get("result", ""),
            model=self.config.model,
            provider="ernie",
            usage=data.get("usage", {}),
            finish_reason=data.get("finish_reason", "stop"),
            raw_response=data
        )

    async def chat_stream(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """文心一言流式聊天"""
        access_token = await self._get_access_token()
        url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token={access_token}"

        payload = {
            "model": self.config.model,
            "messages": self._build_messages(messages),
            "temperature": temperature or self.config.temperature,
            "max_output_tokens": max_tokens or self.config.max_tokens,
            "stream": True
        }

        async with self.client.stream("POST", url, json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        content = data.get("result", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    async def embed(self, text: str) -> List[float]:
        """文心一言文本向量化"""
        access_token = await self._get_access_token()
        url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/embeddings/embedding-v1?access_token={access_token}"

        payload = {
            "input": [text]
        }

        response = await self.client.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        return data.get("data", [{}])[0].get("embedding", [])

    async def is_available(self) -> bool:
        """检查API是否可用"""
        return self.api_key is not None and self.secret_key is not None


class ZhipuAdapter(LLMAdapter):
    """智谱GLM适配器"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://open.bigmodel.cn/api/paas/v4"
        self.api_key = config.api_key or settings.ZHIPU_API_KEY

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """智谱GLM聊天补全"""
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.config.model,
            "messages": self._build_messages(messages),
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens
        }

        response = await self.client.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()

        data = response.json()
        choice = data.get("choices", [{}])[0]

        return LLMResponse(
            content=choice.get("message", {}).get("content", ""),
            model=self.config.model,
            provider="zhipu",
            usage=data.get("usage", {}),
            finish_reason=choice.get("finish_reason", "stop"),
            raw_response=data
        )

    async def chat_stream(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """智谱GLM流式聊天"""
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.config.model,
            "messages": self._build_messages(messages),
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": True
        }

        async with self.client.stream("POST", url, json=payload, headers=self._get_headers()) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    async def embed(self, text: str) -> List[float]:
        """智谱GLM文本向量化"""
        url = f"{self.base_url}/embeddings"

        payload = {
            "model": "embedding-2",
            "input": text
        }

        response = await self.client.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()

        data = response.json()
        return data.get("data", [{}])[0].get("embedding", [])

    async def is_available(self) -> bool:
        """检查API是否可用"""
        return self.api_key is not None


class LLMFactory:
    """LLM工厂类"""

    _adapters: Dict[str, type] = {
        "ollama": OllamaAdapter,
        "qwen": QwenAdapter,
        "ernie": ERNIEAdapter,
        "zhipu": ZhipuAdapter,
    }

    @classmethod
    def create(cls, config: LLMConfig) -> LLMAdapter:
        """创建LLM适配器"""
        provider = config.provider.lower()

        if provider not in cls._adapters:
            raise ValueError(f"不支持的LLM提供商: {provider}")

        return cls._adapters[provider](config)

    @classmethod
    def register_adapter(cls, name: str, adapter_class: type):
        """注册新的适配器"""
        cls._adapters[name.lower()] = adapter_class

    @classmethod
    def list_providers(cls) -> List[str]:
        """列出所有支持的提供商"""
        return list(cls._adapters.keys())


def create_default_config() -> LLMConfig:
    """从配置创建默认LLM配置"""
    return LLMConfig(
        provider=settings.AI_PROVIDER,
        model=settings.AI_DEFAULT_MODEL,
        api_key=settings.QWEN_API_KEY if settings.AI_PROVIDER == "qwen" else None,
        base_url=settings.QWEN_BASE_URL if settings.AI_PROVIDER == "qwen" else None,
        temperature=settings.AI_TEMPERATURE,
        max_tokens=settings.AI_MAX_TOKENS,
    )


class LLMService:
    """LLM服务统一接口"""

    def __init__(self, config: LLMConfig = None):
        # 使用配置文件中的默认配置
        self.config = config or create_default_config()
        self._adapter: Optional[LLMAdapter] = None

    @property
    def adapter(self) -> LLMAdapter:
        """获取适配器（懒加载，自动重建失效的客户端）"""
        if self._adapter is None:
            self._adapter = LLMFactory.create(self.config)
        elif self._adapter.client.is_closed:
            # 客户端已关闭，重新创建
            self._adapter = LLMFactory.create(self.config)
        return self._adapter

    def set_config(self, config: LLMConfig):
        """更新配置"""
        self.config = config
        self._adapter = None  # 重置适配器

    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        purpose: str = "general",
        operation: str = "chat",
        project_id: Optional[str] = None
    ) -> LLMResponse:
        """聊天补全（带追踪）"""
        start_time = time.time()
        request_preview = str([{"role": m.role, "content": m.content[:100]} for m in messages])

        try:
            response = await self.adapter.chat(messages, temperature, max_tokens)
            latency_ms = (time.time() - start_time) * 1000

            # 记录调用日志
            AIUsageTracker.log_call(
                purpose=purpose,
                provider=self.config.provider,
                model=self.config.model,
                operation=operation,
                input_tokens=response.usage.get('input_tokens', response.usage.get('prompt_tokens', 0)),
                output_tokens=response.usage.get('output_tokens', response.usage.get('completion_tokens', 0)),
                latency_ms=latency_ms,
                status="success",
                request_content=request_preview,
                response_content=response.content[:500] if response.content else None,
                project_id=project_id
            )

            return response

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            # 记录失败日志
            AIUsageTracker.log_call(
                purpose=purpose,
                provider=self.config.provider,
                model=self.config.model,
                operation=operation,
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                status="error",
                error_message=str(e),
                request_content=request_preview,
                project_id=project_id
            )

            raise

    async def chat_stream(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """流式聊天补全（不追踪，流式输出）"""
        async for chunk in self.adapter.chat_stream(messages, temperature, max_tokens):
            yield chunk

    async def chat_with_images(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        purpose: str = "recognition",
        operation: str = "chat_with_images",
        project_id: Optional[str] = None
    ) -> LLMResponse:
        """带图片的聊天补全（带追踪）"""
        start_time = time.time()
        request_preview = "image_analysis_request"

        try:
            response = await self.adapter.chat_with_images(messages, temperature, max_tokens)
            latency_ms = (time.time() - start_time) * 1000

            # 记录调用日志
            AIUsageTracker.log_call(
                purpose=purpose,
                provider=self.config.provider,
                model=self.config.model,
                operation=operation,
                input_tokens=response.usage.get('input_tokens', response.usage.get('prompt_tokens', 0)),
                output_tokens=response.usage.get('output_tokens', response.usage.get('completion_tokens', 0)),
                latency_ms=latency_ms,
                status="success",
                request_content=request_preview,
                response_content=response.content[:500] if response.content else None,
                project_id=project_id
            )

            return response

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            AIUsageTracker.log_call(
                purpose=purpose,
                provider=self.config.provider,
                model=self.config.model,
                operation=operation,
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                status="error",
                error_message=str(e),
                request_content=request_preview,
                project_id=project_id
            )

            raise

    async def embed(
        self,
        text: str,
        purpose: str = "general",
        operation: str = "embed",
        project_id: Optional[str] = None
    ) -> List[float]:
        """文本向量化（带追踪）"""
        start_time = time.time()
        request_preview = text[:100] if text else None

        try:
            embedding = await self.adapter.embed(text)
            latency_ms = (time.time() - start_time) * 1000

            # embedding通常没有token统计，记录0
            AIUsageTracker.log_call(
                purpose=purpose,
                provider=self.config.provider,
                model=self.config.model,
                operation=operation,
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                status="success",
                request_content=request_preview,
                project_id=project_id
            )

            return embedding

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            AIUsageTracker.log_call(
                purpose=purpose,
                provider=self.config.provider,
                model=self.config.model,
                operation=operation,
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                status="error",
                error_message=str(e),
                request_content=request_preview,
                project_id=project_id
            )

            raise

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量文本向量化"""
        tasks = [self.embed(text) for text in texts]
        return await asyncio.gather(*tasks)

    async def is_available(self) -> bool:
        """检查服务是否可用"""
        try:
            return await self.adapter.is_available()
        except:
            return False

    async def close(self):
        """关闭服务"""
        if self._adapter:
            await self._adapter.close()

    @staticmethod
    def build_system_prompt(task: str, context: str = "") -> str:
        """构建系统提示词"""
        prompts = {
            "risk_analysis": """你是一位专业的审计专家，负责分析凭证的风险。
请根据凭证信息，从以下几个维度评估风险：
1. 金额合理性：金额是否异常（过大、过小、非整数）
2. 时间合理性：日期是否在工作日、是否跨期
3. 摘要完整性：摘要是否清晰、是否合理
4. 科目匹配性：科目与摘要是否匹配
5. 交易对手：交易对手是否异常

请以JSON格式输出评估结果。""",

            "intelligent_sampling": """你是一位经验丰富的审计抽样专家。
请根据凭证信息和审计目标，推荐最应该抽查的凭证。
考虑以下因素：
1. 金额重要性
2. 业务复杂性
3. 异常信号
4. 历史问题关联

请以JSON格式输出推荐结果和理由。""",

            "voucher_understanding": """你是一位会计专家，请分析并理解这张凭证的内容。
请识别：
1. 业务类型（采购、销售、费用等）
2. 涉及的会计分录
3. 可能的风险点
4. 需要关注的要点

请以清晰、专业的语言描述。"""
        }

        base_prompt = prompts.get(task, "你是一位专业助手。")
        if context:
            base_prompt += f"\n\n背景信息：{context}"

        return base_prompt


# 全局LLM服务实例 - 启动时从配置文件初始化
llm_service = LLMService()


class MultiPurposeLLMServiceManager:
    """
    多用途LLM服务管理器

    支持按用途获取不同的LLM服务实例：
    - general: 通用AI服务（默认）
    - recognition: 图片/PDF识别专用
    - risk_analysis: 风险分析专用
    """

    _instances: Dict[str, LLMService] = {}

    @classmethod
    def get_service(cls, purpose: str = "general") -> LLMService:
        """
        获取指定用途的LLM服务实例

        Args:
            purpose: 用途类型 (general/recognition/risk_analysis)

        Returns:
            LLMService: 对应用途的LLM服务实例
        """
        if purpose not in cls._instances:
            config_dict = settings.get_ai_config_for_purpose(purpose)
            config = LLMConfig(
                provider=config_dict["provider"],
                model=config_dict["model"],
                api_key=config_dict.get("api_key"),
                base_url=config_dict.get("base_url"),
                temperature=config_dict["temperature"],
                max_tokens=config_dict["max_tokens"],
            )
            cls._instances[purpose] = LLMService(config)

        return cls._instances[purpose]

    @classmethod
    async def refresh_service(cls, purpose: str):
        """
        刷新指定用途的服务实例

        配置变更后调用，清除旧实例并重新创建
        """
        if purpose in cls._instances:
            await cls._instances[purpose].close()
            del cls._instances[purpose]

    @classmethod
    async def refresh_all(cls):
        """刷新所有服务实例"""
        for purpose in list(cls._instances.keys()):
            await cls._instances[purpose].close()
        cls._instances.clear()

    @classmethod
    def get_purpose_status(cls, purpose: str) -> Dict[str, Any]:
        """获取指定用途的配置状态"""
        config_dict = settings.get_ai_config_for_purpose(purpose)
        return {
            "purpose": purpose,
            "purpose_name": {
                "general": "通用AI服务",
                "recognition": "图片/PDF识别",
                "risk_analysis": "风险分析"
            }.get(purpose, purpose),
            "provider": config_dict["provider"],
            "model": config_dict["model"],
            "temperature": config_dict["temperature"],
            "max_tokens": config_dict["max_tokens"]
        }


# 全局服务管理器实例
llm_service_manager = MultiPurposeLLMServiceManager()


def get_recognition_service() -> LLMService:
    """获取图片/PDF识别服务"""
    return llm_service_manager.get_service("recognition")


def get_risk_analysis_service() -> LLMService:
    """获取风险分析服务"""
    return llm_service_manager.get_service("risk_analysis")


def get_general_service() -> LLMService:
    """获取通用AI服务"""
    return llm_service_manager.get_service("general")