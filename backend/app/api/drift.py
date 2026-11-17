import logging
from fastapi import APIRouter, HTTPException, status

from app.schemas.drift import DriftAnalysisRequest, DriftAnalysisResponse
from app.services.drift_modelling_service import drift_modelling_service

logger = logging.getLogger("oceantrace.api.drift")
router = APIRouter(prefix="/drift", tags=["Phase 5 - Drift Modelling & Origin Estimation"])


@router.post("/analyze", response_model=DriftAnalysisResponse, status_code=status.HTTP_200_OK)
async def analyze_drift(request: DriftAnalysisRequest):
    """
    Executes Phase 5 Lagrangian Backward and Forward Drift Simulations to estimate
    the Probable Origin Zone, Release Window, and Particle Trajectories.
    """
    try:
        logger.info(f"Processing Phase 5 drift analysis for acquisition_time={request.acquisition_time}")
        response = drift_modelling_service.run_drift_simulation(request)
        return response
    except ValueError as ve:
        logger.error(f"Validation error in drift analysis: {str(ve)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to execute drift simulation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Phase 5 drift analysis failed: {str(e)}",
        )
