import os
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    OPENAI = "openai"
    TONGYI = "tongyi"


class LLMClient(ABC):
    """通用LLM客户端抽象基类"""
    
    @abstractmethod
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """聊天完成接口"""
        pass
    
    @abstractmethod
    def text_completion(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """文本完成接口"""
        pass


class OpenAILLMClient(LLMClient):
    """OpenAI客户端实现"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
        return self._client
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """OpenAI聊天完成"""
        try:
            response = self.client.chat.completions.create(
                messages=messages,
                **kwargs
            )
            return {
                "text": response.choices[0].message.content or "",
                "model": getattr(response, "model", None),
                "id": getattr(response, "id", None),
                "usage": getattr(response, "usage", None)
            }
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def text_completion(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """OpenAI文本完成（使用Responses API或Chat Completions）"""
        try:
            # 检查是否有Responses API
            if hasattr(self.client, "responses") and hasattr(self.client.responses, "create"):
                response = self.client.responses.create(
                    input=prompt,
                    **kwargs
                )
                return {
                    "text": getattr(response, "output_text", "") or "",
                    "model": getattr(response, "model", None),
                    "id": getattr(response, "id", None)
                }
            else:
                # 回退到Chat Completions
                messages = [{"role": "user", "content": prompt}]
                return self.chat_completion(messages, **kwargs)
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


class TongyiLLMClient(LLMClient):
    """阿里巴巴通义大模型客户端实现"""
    
    def __init__(self, api_key: str, base_url: str = "https://dashscope.aliyuncs.com/api/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        return self._client
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """通义大模型聊天完成"""
        try:
            # 设置默认模型
            model = kwargs.get("model", "qwen-plus")
            kwargs["model"] = model
            
            response = self.client.chat.completions.create(
                messages=messages,
                **kwargs
            )
            return {
                "text": response.choices[0].message.content or "",
                "model": getattr(response, "model", None),
                "id": getattr(response, "id", None),
                "usage": getattr(response, "usage", None)
            }
        except Exception as e:
            logger.error(f"Tongyi API error: {e}")
            raise
    
    def text_completion(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """通义大模型文本完成"""
        try:
            # 将prompt转换为messages格式
            messages = [{"role": "user", "content": prompt}]
            return self.chat_completion(messages, **kwargs)
        except Exception as e:
            logger.error(f"Tongyi API error: {e}")
            raise


class LLMClientFactory:
    """LLM客户端工厂类"""
    
    @staticmethod
    def create_client(provider: LLMProvider, **kwargs) -> LLMClient:
        """创建LLM客户端"""
        if provider == LLMProvider.OPENAI:
            api_key = kwargs.get("api_key") or os.getenv("OPENAI_API_KEY")
            base_url = kwargs.get("base_url") or os.getenv("OPENAI_BASE_URL")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is required")
            return OpenAILLMClient(api_key=api_key, base_url=base_url)
        
        elif provider == LLMProvider.TONGYI:
            api_key = kwargs.get("api_key") or os.getenv("TONGYI_API_KEY")
            base_url = kwargs.get("base_url") or os.getenv("TONGYI_BASE_URL", "https://dashscope.aliyuncs.com/api/v1")
            if not api_key:
                raise ValueError("TONGYI_API_KEY is required")
            return TongyiLLMClient(api_key=api_key, base_url=base_url)
        
        else:
            raise ValueError(f"Unsupported provider: {provider}")


def get_default_client() -> LLMClient:
    """获取默认LLM客户端"""
    # 优先使用通义大模型，如果没有配置则使用OpenAI
    if os.getenv("TONGYI_API_KEY"):
        return LLMClientFactory.create_client(LLMProvider.TONGYI)
    elif os.getenv("OPENAI_API_KEY"):
        return LLMClientFactory.create_client(LLMProvider.OPENAI)
    else:
        raise ValueError("No LLM API key configured. Please set TONGYI_API_KEY or OPENAI_API_KEY")


def get_client_by_provider(provider: str) -> LLMClient:
    """根据提供商名称获取客户端"""
    try:
        provider_enum = LLMProvider(provider.lower())
        return LLMClientFactory.create_client(provider_enum)
    except ValueError:
        raise ValueError(f"Unsupported provider: {provider}. Supported providers: {[p.value for p in LLMProvider]}")
