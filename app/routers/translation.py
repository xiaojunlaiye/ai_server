from fastapi import APIRouter, HTTPException

from app.services.translation import TranslationRequest, TranslationResponse, translate

router = APIRouter(prefix="/translation", tags=["translation"])


@router.post("/translate", response_model=TranslationResponse)
def translate_endpoint(req: TranslationRequest) -> TranslationResponse:
    try:
        return translate(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Translation error: {e}")


# 兼容：/translate 顶层别名，接收相同的请求体
from fastapi import Body  # noqa: E402


@router.post("/translate_compat", response_model=TranslationResponse, include_in_schema=False)
def translate_endpoint_compat(req: TranslationRequest = Body(...)) -> TranslationResponse:
    try:
        return translate(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Translation error: {e}")
