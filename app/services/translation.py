import logging
from typing import Dict, Any, List

from pydantic import BaseModel, Field

from app.common.openai_client import create_openai_client, has_responses_api

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
    # OpenAI 相关可选参数
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


def build_prompt(text: str, target_lang: str, source_lang: str | None, style: str | None, auto_detect: bool) -> str:
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
    client = create_openai_client()
    default_model = req.model or "gpt-4o-mini"

    if has_responses_api(client):
        prompt = build_prompt(
            text=req.text,
            target_lang=req.target_lang,
            source_lang=None if req.auto_detect else req.source_lang,
            style=req.style,
            auto_detect=req.auto_detect,
        )
        
        # 打印发送给OpenAI的内容
        logger.info(f"=== OpenAI API Request (Responses API) ===")
        logger.info(f"Model: {default_model}")
        logger.info(f"Prompt: {prompt}")
        logger.info(f"Temperature: {req.temperature}")
        logger.info(f"Max tokens: {req.max_tokens}")
        logger.info(f"Extra params: {req.extra}")
        
        resp = client.responses.create(
            model=default_model,
            input=prompt,
            temperature=req.temperature,
            max_output_tokens=req.max_tokens,
            **(req.extra or {}),
        )
        text = getattr(resp, "output_text", "") or ""
        logger.info(f"=== OpenAI API Response ===")
        logger.info(f"Translated text: {text}")
        return TranslationResponse(translated_text=text, model=getattr(resp, "model", None), id=getattr(resp, "id", None))
    else:
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": "You are a professional translator."},
            {
                "role": "user",
                "content": build_prompt(
                    text=req.text,
                    target_lang=req.target_lang,
                    source_lang=None if req.auto_detect else req.source_lang,
                    style=req.style,
                    auto_detect=req.auto_detect,
                ),
            },
        ]
        
        # 打印发送给OpenAI的内容
        logger.info(f"=== OpenAI API Request (Chat Completions) ===")
        logger.info(f"Model: {default_model}")
        logger.info(f"Messages: {messages}")
        logger.info(f"Temperature: {req.temperature}")
        logger.info(f"Max tokens: {req.max_tokens}")
        logger.info(f"Extra params: {req.extra}")
        
        resp = client.chat.completions.create(
            model=default_model,
            messages=messages,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            **(req.extra or {}),
        )
        first = resp.choices[0].message.content if resp.choices else ""
        logger.info(f"=== OpenAI API Response ===")
        logger.info(f"Translated text: {first}")
        return TranslationResponse(translated_text=first or "", model=getattr(resp, "model", None), id=getattr(resp, "id", None))
