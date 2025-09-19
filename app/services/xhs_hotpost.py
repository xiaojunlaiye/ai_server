from typing import Dict, Any, List

from pydantic import BaseModel

from app.common.openai_client import create_openai_client, has_responses_api


class XHSRequest(BaseModel):
    topic: str
    audience: str | None = None
    style: str | None = None  # 如：真实、种草、专业、俏皮
    model: str | None = None
    temperature: float | None = 0.8
    max_tokens: int | None = None
    extra: Dict[str, Any] | None = None


class XHSItem(BaseModel):
    title: str
    content: str
    hashtags: List[str] | None = None


class XHSResponse(BaseModel):
    ideas: List[XHSItem]
    model: str | None = None
    id: str | None = None


PROMPT_TEMPLATE = (
    "你是一名擅长小红书爆款内容创作者。根据主题与目标受众，给出3条高质量爆款文案，"
    "每条包含：吸睛标题、正文内容（强调真实体验、场景、痛点-解决方案）、以及3-5个相关话题#。"
    "要求：标题简短有力，正文有节奏、有表情符号并可包含清单/步骤；输出为 JSON 数组，每条含 title、content、hashtags。\n\n"
    "主题: {topic}\n"
    "受众: {audience}\n"
    "风格: {style}\n"
)


def generate_xhs(req: XHSRequest) -> XHSResponse:
    client = create_openai_client()
    default_model = req.model or "gpt-4o-mini"

    audience = req.audience or "大众人群"
    style = req.style or "真实、种草"
    prompt = PROMPT_TEMPLATE.format(topic=req.topic, audience=audience, style=style)

    if has_responses_api(client):
        resp = client.responses.create(
            model=default_model,
            input=prompt,
            temperature=req.temperature,
            max_output_tokens=req.max_tokens,
            **(req.extra or {}),
        )
        text = getattr(resp, "output_text", "") or ""
    else:
        messages = [
            {"role": "system", "content": "你是一名资深的小红书爆款内容创作者。"},
            {"role": "user", "content": prompt},
        ]
        cr = client.chat.completions.create(
            model=default_model,
            messages=messages,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            **(req.extra or {}),
        )
        text = cr.choices[0].message.content if cr.choices else ""

    # 解析成结构化输出，尽量稳健
    import json

    ideas: List[XHSItem] = []
    try:
        arr = json.loads(text)
        if isinstance(arr, list):
            for it in arr:
                title = str(it.get("title", "")).strip()
                content = str(it.get("content", "")).strip()
                hashtags = it.get("hashtags")
                if isinstance(hashtags, list):
                    hashtags = [str(h).strip() for h in hashtags]
                else:
                    hashtags = None
                if title or content:
                    ideas.append(XHSItem(title=title, content=content, hashtags=hashtags))
    except Exception:
        # 回退：若非JSON，包一层
        if text.strip():
            ideas.append(XHSItem(title="爆款文案建议", content=text.strip(), hashtags=None))

    return XHSResponse(ideas=ideas, model=getattr(locals().get('resp', None), "model", None), id=getattr(locals().get('resp', None), "id", None))
