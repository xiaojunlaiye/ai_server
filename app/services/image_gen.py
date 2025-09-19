from typing import Dict, Any, Optional

from pydantic import BaseModel

from app.common.openai_client import create_openai_client


class ImageGenRequest(BaseModel):
    prompt: str
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
    client = create_openai_client()
    model = req.model or "gpt-image-1"

    # 兼容 openai.images.generate (新版SDK) 接口
    if not hasattr(client, "images") or not hasattr(client.images, "generate"):
        raise RuntimeError("Images API not available in current SDK")

    resp = client.images.generate(
        model=model,
        prompt=req.prompt,
        size=req.size,
        quality=req.quality,
        n=req.n or 1,
        **(req.extra or {}),
    )

    images: list[ImageItem] = []
    data = getattr(resp, "data", None) or []
    for d in data:
        images.append(ImageItem(url=getattr(d, "url", None), b64_json=getattr(d, "b64_json", None)))

    return ImageGenResponse(images=images, model=getattr(resp, "model", None), id=getattr(resp, "id", None))
