import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.investigation import (
    InvestigationReportRequest,
    InvestigationReportResponse,
    InvestigationStatusResponse,
)
from app.services.investigation_report_service import investigation_report_service

logger = logging.getLogger("oceantrace.api.investigation")
router = APIRouter(prefix="/investigation", tags=["Phase 7 - Automated Investigation Report & Operational Alert Engine"])


@router.post("/report", response_model=InvestigationReportResponse, status_code=status.HTTP_200_OK)
async def generate_investigation_report(request: InvestigationReportRequest = InvestigationReportRequest()):
    """
    Phase 7 — Generate or deterministically regenerate an Investigation Report & Operational Alert Metadata object.
    Aggregates immutable outputs from Phase 1 through Phase 6.3.
    """
    try:
        return investigation_report_service.generate_report(request)
    except ValueError as ve:
        logger.error(f"Validation error during investigation report generation: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Investigation report generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Investigation report generation failed: {str(e)}",
        )


@router.get("/report/{scene_id}", response_model=InvestigationReportResponse, status_code=status.HTTP_200_OK)
async def get_existing_investigation_report(scene_id: str):
    """
    Retrieves existing persisted investigation report for a given scene_id, or generates it if absent.
    """
    try:
        req = InvestigationReportRequest(scene_id=scene_id)
        return investigation_report_service.generate_report(req)
    except Exception as e:
        logger.error(f"Failed to retrieve report for scene {scene_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve report for scene {scene_id}: {str(e)}",
        )


@router.get("/status", response_model=InvestigationStatusResponse, status_code=status.HTTP_200_OK)
async def get_investigation_status(
    scene_id: Optional[str] = Query(None, description="Optional scene ID to check status for")
):
    """
    Returns concise operational investigation status, attention level, and alert availability for a scene. Never exposes secrets.
    """
    try:
        return investigation_report_service.get_status(scene_id=scene_id)
    except Exception as e:
        logger.error(f"Failed to fetch investigation status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve investigation status: {str(e)}",
        )
