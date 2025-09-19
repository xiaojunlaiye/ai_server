from typing import Dict, Any, List

from pydantic import BaseModel

from app.common.openai_client import create_openai_client, has_responses_api


class TranslationRequest(BaseModel):
    text: str
    source_lang: str | None = None  # 自动检测可留空
    target_lang: str
    model: str | None = None  # 可覆盖默认模型
    temperature: float | None = 0.2
    max_tokens: int | None = None
    extra: Dict[str, Any] | None = None


class TranslationResponse(BaseModel):
    translated_text: str
    model: str | None = None
    id: str | None = None


def build_prompt(text: str, target_lang: str, source_lang: str | None) -> str:
    if source_lang:
        return (
            f"You are a professional translator. Translate the following text from {source_lang} to {target_lang}.\n"
            f"Only return the translation, no extra commentary.\n\n"
            f"Text:\n{text}"
        )
    else:
        return (
            f"You are a professional translator. Detect the source language and translate to {target_lang}.\n"
            f"Only return the translation, no extra commentary.\n\n"
            f"Text:\n{text}"
        )


def translate(req: TranslationRequest) -> TranslationResponse:
    client = create_openai_client()
    default_model = req.model or "gpt-4o-mini"

    if has_responses_api(client):
        prompt = build_prompt(req.text, req.target_lang, req.source_lang)
        resp = client.responses.create(
            model=default_model,
            input=prompt,
            temperature=req.temperature,
            max_output_tokens=req.max_tokens,
            **(req.extra or {}),
        )
        text = getattr(resp, "output_text", "") or ""
        return TranslationResponse(translated_text=text, model=getattr(resp, "model", None), id=getattr(resp, "id", None))
    else:
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": "You are a professional translator."},
            {"role": "user", "content": build_prompt(req.text, req.target_lang, req.source_lang)},
        ]
        resp = client.chat.completions.create(
            model=default_model,
            messages=messages,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            **(req.extra or {}),
        )
        first = resp.choices[0].message.content if resp.choices else ""
        return TranslationResponse(translated_text=first or "", model=getattr(resp, "model", None), id=getattr(resp, "id", None))
