import logging
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field

from app.common.llm_client import get_default_client, get_client_by_provider, LLMProvider

logger = logging.getLogger(__name__)


class TranslationRequest(BaseModel):
    text: str
    # 如果 auto_detect 为 True，将忽略 source_lang
    source_lang: str | None = None
    # 兼容客户端字段 target_language
    target_lang: str = Field(..., alias="target_language")
    # 翻译风格，如 "书面风格" / "简洁" / "学术"
    style: str | None = None
    # 是否自动识别源语言
    auto_detect: bool = True
    # LLM 提供商选择
    provider: str | None = None  # "openai" 或 "tongyi"
    # 模型相关参数
    model: str | None = None
    temperature: float | None = 0.2
    max_tokens: int | None = None
    extra: Dict[str, Any] | None = None

    model_config = {
        # 同时允许通过字段名与别名传入（既兼容 target_lang，也兼容 target_language）
        "populate_by_name": True
    }


class TranslationResponse(BaseModel):
    translated_text: str
    model: str | None = None
    id: str | None = None
    provider: str | None = None


def build_prompt(text: str, target_lang: str, source_lang: str | None, style: str | None, auto_detect: bool) -> str:
    # 处理 "all" 风格参数
    if style and style.lower() == "all":
        style_clause = (
            " Please provide translations in two different styles:\n"
            "1. 口语风格 (Colloquial style) - natural, conversational tone\n"
            "2. 书面风格 (Formal style) - professional, written tone\n"
            "Format your response as:\n"
            "口语风格: [translation]\n"
            "书面风格: [translation]"
        )
    else:
        style_clause = f" Use the following style: {style}." if style else ""
    
    if auto_detect or not source_lang:
        return (
            f"You are a professional translator. Detect the source language and translate to {target_lang}.{style_clause}\n"
            f"Only return the translation, no extra commentary.\n\n"
            f"Text:\n{text}"
        )
    else:
        return (
            f"You are a professional translator. Translate the following text from {source_lang} to {target_lang}.{style_clause}\n"
            f"Only return the translation, no extra commentary.\n\n"
            f"Text:\n{text}"
        )


def translate(req: TranslationRequest) -> TranslationResponse:
    # 获取LLM客户端
    try:
        if req.provider:
            client = get_client_by_provider(req.provider)
            provider_name = req.provider
        else:
            client = get_default_client()
            # 根据可用的API密钥判断默认提供商
            import os
            if os.getenv("TONGYI_API_KEY"):
                provider_name = "tongyi"
            else:
                provider_name = "openai"
    except Exception as e:
        logger.error(f"Failed to create LLM client: {e}")
        raise ValueError(f"Failed to initialize LLM client: {e}")

    # 设置默认模型
    if provider_name == "tongyi":
        default_model = req.model or "qwen-turbo"
    else:
        default_model = req.model or "gpt-4o-mini"

    # 构建请求参数
    kwargs = {
        "model": default_model,
        "temperature": req.temperature,
    }
    if req.max_tokens:
        kwargs["max_tokens"] = req.max_tokens
    if req.extra:
        kwargs.update(req.extra)

    try:
        # 构建提示词
        prompt = build_prompt(
            text=req.text,
            target_lang=req.target_lang,
            source_lang=None if req.auto_detect else req.source_lang,
            style=req.style,
            auto_detect=req.auto_detect,
        )
        
        # 记录请求信息
        logger.info(f"=== {provider_name.upper()} API Request ===")
        logger.info(f"Provider: {provider_name}")
        logger.info(f"Model: {default_model}")
        logger.info(f"Prompt: {prompt}")
        logger.info(f"Temperature: {req.temperature}")
        logger.info(f"Max tokens: {req.max_tokens}")
        logger.info(f"Extra params: {req.extra}")
        
        # 调用LLM API
        response = client.text_completion(prompt, **kwargs)
        
        # 记录响应信息
        logger.info(f"=== {provider_name.upper()} API Response ===")
        logger.info(f"Translated text: {response.get('text', '')}")
        logger.info(f"Model: {response.get('model', '')}")
        logger.info(f"ID: {response.get('id', '')}")
        
        return TranslationResponse(
            translated_text=response.get("text", ""),
            model=response.get("model"),
            id=response.get("id"),
            provider=provider_name
        )
        
    except Exception as e:
        logger.error(f"{provider_name.upper()} API error: {e}")
        raise ValueError(f"Translation error: {e}")
