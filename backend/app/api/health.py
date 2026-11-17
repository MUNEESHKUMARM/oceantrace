from fastapi import APIRouter
from app.schemas.sentinel1 import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def get_health_status():
    """
    Health check endpoint for OceanTrace AI Backend.
    """
    return HealthResponse(status="ok", service="OceanTrace AI Backend")
