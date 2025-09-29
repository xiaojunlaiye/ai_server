from typing import Dict, Any, Optional

from pydantic import BaseModel

from app.common.llm_client import get_default_client, get_client_by_provider


class ImageGenRequest(BaseModel):
    prompt: str
    provider: str | None = None  # "openai" 或 "tongyi"
    model: str | None = None  # 如 "gpt-image-1" 或兼容模型
    size: str | None = "1024x1024"
    quality: str | None = None  # 如 "high"
    n: int | None = 1
    extra: Dict[str, Any] | None = None


class ImageItem(BaseModel):
    url: Optional[str] = None
    b64_json: Optional[str] = None


class ImageGenResponse(BaseModel):
    images: list[ImageItem]
    model: str | None = None
    id: str | None = None


def generate_image(req: ImageGenRequest) -> ImageGenResponse:
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
        # 通义大模型目前主要支持文本生成，图片生成功能有限
        raise ValueError("Tongyi models currently don't support image generation. Please use OpenAI provider.")
    else:
        model = req.model or "dall-e-3"

    # 检查是否支持图片生成
    if not hasattr(client.client, "images") or not hasattr(client.client.images, "generate"):
        raise RuntimeError("Images API not available in current SDK")

    # 构建请求参数
    kwargs = {
        "model": model,
        "prompt": req.prompt,
        "size": req.size,
        "n": req.n or 1,
    }
    if req.quality:
        kwargs["quality"] = req.quality
    if req.extra:
        kwargs.update(req.extra)

    # 调用图片生成API
    resp = client.client.images.generate(**kwargs)

    images: list[ImageItem] = []
    data = getattr(resp, "data", None) or []
    for d in data:
        images.append(ImageItem(url=getattr(d, "url", None), b64_json=getattr(d, "b64_json", None)))

    return ImageGenResponse(images=images, model=getattr(resp, "model", None), id=getattr(resp, "id", None))
