from fastapi import APIRouter, HTTPException

from app.services.xhs_hotpost import XHSRequest, XHSResponse, generate_xhs

router = APIRouter(prefix="/xhs", tags=["xhs"])


@router.post("/hotpost", response_model=XHSResponse)
def generate_xhs_endpoint(req: XHSRequest) -> XHSResponse:
    try:
        return generate_xhs(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"XHS generation error: {e}")
