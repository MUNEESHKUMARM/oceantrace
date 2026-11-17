import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Query

from app.schemas.environment import EnvironmentAnalysisRequest, EnvironmentAnalysisResponse
from app.services.environment_service import environment_service
from app.services.scene_state_service import scene_state_service
from app.services.scene_watcher_service import scene_watcher_service

logger = logging.getLogger("oceantrace.api.environment")
router = APIRouter(prefix="/environment", tags=["Phase 4 - Wind & Ocean Current Analysis"])


@router.post("/analyze", response_model=EnvironmentAnalysisResponse, status_code=status.HTTP_200_OK)
def analyze_environment(request: EnvironmentAnalysisRequest):
    """
    Perform Phase 4 Wind + Ocean Current Analysis for Sentinel-1 scene acquisition timestamp and spatial geometry.
    Returns real U/V vector components, wind/current speeds, directions, and spatial vector fields.
    """
    try:
        logger.info(f"Processing Phase 4 environment analysis for acquisition_time={request.acquisition_time}")
        response = environment_service.analyze_environment(request)
        return response
    except ValueError as ve:
        logger.error(f"Validation error in environment analysis: {str(ve)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to execute environment analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Phase 4 environment analysis failed: {str(e)}",
        )


@router.get("/status", status_code=status.HTTP_200_OK)
def get_environment_status():
    """
    Returns current backend Phase 4 Auto-Sync scene status, latest product ID,
    acquisition timestamp, time offsets, and processing status.
    """
    try:
        state = scene_state_service.get_state()
        return {
            "status": "success",
            "phase": 4,
            "latest_product_id": state.get("last_processed_product_id"),
            "latest_acquisition_datetime": state.get("last_processed_acquisition_datetime"),
            "last_updated": state.get("last_updated"),
            "processing_status": state.get("processing_status"),
            "environment_status": state.get("phase4_status"),
            "wind_data_time": state.get("wind_data_time"),
            "wind_offset_seconds": state.get("wind_offset_seconds"),
            "current_data_time": state.get("current_data_time"),
            "current_offset_seconds": state.get("current_offset_seconds"),
            "spill_conditioned": state.get("spill_conditioned", False),
            "spill_regions_count": state.get("spill_regions_count", 0),
        }
    except Exception as e:
        logger.error(f"Failed to retrieve environment status: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/auto-sync", status_code=status.HTTP_200_OK)
def trigger_auto_sync(force_retry: bool = Query(False, description="Force retry processing even if product_id is unchanged")):
    """
    Triggers Phase 4 Auto-Sync check for new CDSE Sentinel-1 acquisitions.
    Executes Phase 1-5 pipeline if a new scene is detected or retry is forced.
    Guarantees duplicate protection if scene is unchanged.
    """
    try:
        res = scene_watcher_service.check_and_sync_latest_scene(force_retry=force_retry)
        return res
    except Exception as e:
        logger.error(f"Auto-sync check failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
