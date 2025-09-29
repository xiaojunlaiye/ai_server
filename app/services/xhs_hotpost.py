from typing import Dict, Any, List, Optional

from pydantic import BaseModel

from app.common.llm_client import get_default_client, get_client_by_provider


class XHSRequest(BaseModel):
    topic: str
    audience: str | None = None
    style: str | None = None  # 如：真实、种草、专业、俏皮
    provider: str | None = None  # "openai" 或 "tongyi"
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
    # 获取LLM客户端
    try:
        if req.provider:
            client = get_client_by_provider(req.provider)
        else:
            client = get_default_client()
    except Exception as e:
        raise ValueError(f"Failed to initialize LLM client: {e}")

    # 设置默认模型
    if req.provider == "tongyi":
        default_model = req.model or "qwen-turbo"
    else:
        default_model = req.model or "gpt-4o-mini"

    audience = req.audience or "大众人群"
    style = req.style or "真实、种草"
    prompt = PROMPT_TEMPLATE.format(topic=req.topic, audience=audience, style=style)

    # 构建请求参数
    kwargs = {
        "model": default_model,
        "temperature": req.temperature,
    }
    if req.max_tokens:
        kwargs["max_tokens"] = req.max_tokens
    if req.extra:
        kwargs.update(req.extra)

    # 调用LLM API
    response = client.text_completion(prompt, **kwargs)
    text = response.get("text", "")

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
