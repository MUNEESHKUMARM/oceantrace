import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.ais import (
    AISCollectorStatus,
    AISCorrelationRequest,
    AISCorrelationResponse,
    AISRankingRequest,
    AISRankingResponse,
)
from app.services.ais_stream_service import ais_stream_service
from app.core.database import SessionLocal
from app.models.ais import AISVesselPosition

logger = logging.getLogger("oceantrace.api.ais")
router = APIRouter(prefix="/ais", tags=["Phase 6 - Live AIS, Correlation & Explainable Ranking"])


@router.get("/status", response_model=AISCollectorStatus, status_code=status.HTTP_200_OK)
async def get_ais_collector_status():
    """
    Returns operational health, connection status, and message telemetry for the
    Phase 6.1 AISStream real-time WebSocket collector. Never exposes secrets or credentials.
    """
    try:
        return ais_stream_service.get_status()
    except Exception as e:
        logger.error(f"Failed to fetch AIS collector status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve AIS collector status: {str(e)}",
        )


@router.get("/recent", response_model=List[Dict[str, Any]], status_code=status.HTTP_200_OK)
async def get_recent_ais_positions(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of recent normalized AIS position records to return")
):
    """
    Safe diagnostic endpoint returning recent normalized AIS vessel positions persisted in the database.
    """
    try:
        db = SessionLocal()
        try:
            records = (
                db.query(AISVesselPosition)
                .order_by(AISVesselPosition.received_at_utc.desc())
                .limit(limit)
                .all()
            )
            return [rec.to_dict() for rec in records]
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Could not retrieve recent AIS records: {e}")
        return []


@router.post("/correlate", response_model=AISCorrelationResponse, status_code=status.HTTP_200_OK)
async def correlate_ais_vessels(request: AISCorrelationRequest = AISCorrelationRequest()):
    """
    Phase 6.2 — AIS Spatial + Temporal Correlation Engine.
    Correlates stored Phase 6.1 AIS positions with canonical Phase 5 probable origin zones.
    Returns unordered evidence candidate vessels without ranking or causation claims.
    """
    try:
        from app.services.ais_correlation_service import ais_correlation_service
        return ais_correlation_service.correlate_ais(request)
    except Exception as e:
        logger.error(f"Phase 6.2 AIS correlation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Phase 6.2 AIS correlation failed: {str(e)}",
        )


@router.post("/rank", response_model=AISRankingResponse, status_code=status.HTTP_200_OK)
async def rank_ais_candidates(request: AISRankingRequest = AISRankingRequest()):
    """
    Phase 6.3 — Explainable AIS Candidate Ranking Engine.
    Consumes Phase 6.2 candidate evidence and applies a transparent, deterministic,
    configurable evidence-weighting formula to generate an ordered candidate list.
    """
    try:
        from app.services.ais_ranking_service import ais_ranking_service
        return ais_ranking_service.rank_candidates(request)
    except ValueError as ve:
        logger.error(f"Validation error in candidate ranking: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Phase 6.3 candidate ranking failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Phase 6.3 candidate ranking failed: {str(e)}",
        )
