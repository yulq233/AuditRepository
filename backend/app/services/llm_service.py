"""
LLM适配器框架
统一接口支持多种大语言模型：Ollama、通义千问、文心一言、智谱GLM等
"""
import os
import json
import httpx
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

from app.core.config import settings


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: str = "ollama"
    model: str = "qwen2.5:14b"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 60


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str  # system, user, assistant
    content: str


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
        self.base_url = config.base_url or "http://localhost:11434"

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
    """阿里云通义千问适配器"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.api_key = config.api_key or os.environ.get("QWEN_API_KEY")

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
        """通义千问聊天补全"""
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
        """通义千问流式聊天"""
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
        """通义千问文本向量化"""
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
        self.api_key = config.api_key or os.environ.get("ERNIE_API_KEY")
        self.secret_key = os.environ.get("ERNIE_SECRET_KEY")
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
        self.api_key = config.api_key or os.environ.get("ZHIPU_API_KEY")

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


class LLMService:
    """LLM服务统一接口"""

    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig(
            provider=settings.DEFAULT_AI_PROVIDER,
            model="qwen2.5:14b"
        )
        self._adapter: Optional[LLMAdapter] = None

    @property
    def adapter(self) -> LLMAdapter:
        """获取适配器（懒加载）"""
        if self._adapter is None:
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
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """聊天补全"""
        return await self.adapter.chat(messages, temperature, max_tokens)

    async def chat_stream(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """流式聊天补全"""
        async for chunk in self.adapter.chat_stream(messages, temperature, max_tokens):
            yield chunk

    async def embed(self, text: str) -> List[float]:
        """文本向量化"""
        return await self.adapter.embed(text)

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


# 全局LLM服务实例
llm_service = LLMService()