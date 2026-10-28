"""
Health-check and system info endpoint.
"""

from fastapi import APIRouter

from ..config import settings
from ..models import HealthResponse
from ..services import background_removal, upscaling, face_enhancement

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Return backend status and loaded model availability."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        device=settings.device,
        models={
            "background_removal": background_removal.is_available(),
            "upscaling": upscaling.is_available(),
            "face_enhancement": face_enhancement.is_available(),
        },
    )
