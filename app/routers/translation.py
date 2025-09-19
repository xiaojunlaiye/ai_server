from fastapi import APIRouter, HTTPException

from app.services.translation import TranslationRequest, TranslationResponse, translate

router = APIRouter(prefix="/translation", tags=["translation"])


@router.post("/translate", response_model=TranslationResponse)
def translate_endpoint(req: TranslationRequest) -> TranslationResponse:
    try:
        return translate(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Translation error: {e}")
