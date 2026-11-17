import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.spill_mapping import SpillMappingRequest, SpillMappingResponse
from app.services.spill_mapping_service import spill_mapping_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/spill", tags=["Phase 3 — Real Oil-Spill Mapping"])


@router.post("/mapping", response_model=SpillMappingResponse, status_code=status.HTTP_200_OK)
def run_spill_mapping_endpoint(request: SpillMappingRequest):
    """
    Executes Phase 3 Real Oil-Spill Mapping & Polygon Extraction:
    - Validates prediction mask
    - Noise filtering
    - Vector polygonization (Rasterio + Shapely)
    - Geodesic area calculation (m² & km²)
    - GeoJSON spill polygon export
    - Transparent severity index computation
    """
    try:
        result = spill_mapping_service.run_spill_mapping(
            mask_path=request.mask_path,
            confidence_path=request.confidence_path,
            source_geotiff_path=request.source_geotiff_path,
            min_region_pixels=request.min_region_pixels,
            acquisition_time=request.acquisition_time,
            scene_id=request.scene_id,
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error during spill mapping execution: %s", str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Spill mapping error: {str(e)}")
