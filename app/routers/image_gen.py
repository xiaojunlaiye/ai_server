from fastapi import APIRouter, HTTPException

from app.services.image_gen import ImageGenRequest, ImageGenResponse, generate_image

router = APIRouter(prefix="/images", tags=["images"])


@router.post("/generate", response_model=ImageGenResponse)
def generate_image_endpoint(req: ImageGenRequest) -> ImageGenResponse:
    try:
        return generate_image(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Image generation error: {e}")
