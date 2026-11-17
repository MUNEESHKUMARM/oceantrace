import logging
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.sentinel1 import Sentinel1ProcessRequest
from app.services.sentinel1_service import sentinel1_service
from app.services.oil_detection_service import oil_detection_service
from app.services.cdse_auth import CDSEAuthenticationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/detection", tags=["AI Oil-Spill Detection"])


class DetectionRunRequest(BaseModel):
    geotiff_path: Optional[str] = Field(default=None, description="Path to preprocessed Sentinel-1 SAR GeoTIFF file, or None for latest Phase 1 scene")


class ClassDistribution(BaseModel):
    background_pixels: int
    oil_spill_pixels: int
    lookalike_pixels: int


class DetectionRunResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    detected: bool
    confidence: float
    mask_file: str
    confidence_file: str
    overlay_file: str
    class_distribution: ClassDistribution
    model_info: Dict[str, Any]
    oil_pixel_percentage: Optional[float] = None
    threshold: Optional[float] = 0.5
    compatibility: Optional[Dict[str, Any]] = None
    disclaimer: Optional[str] = None


@router.post("/run", response_model=DetectionRunResponse, status_code=status.HTTP_200_OK)
def run_oil_detection(request: DetectionRunRequest):
    """
    Executes AI-based Oil-Spill Detection / Semantic Segmentation on preprocessed Sentinel-1 SAR GeoTIFF.
    """
    try:
        result = oil_detection_service.run_detection(geotiff_path=request.geotiff_path)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error during oil detection inference: %s", str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Inference error: {str(e)}")


from app.services.spill_mapping_service import spill_mapping_service
from app.services.environment_service import environment_service
from app.services.drift_modelling_service import drift_modelling_service
from app.schemas.environment import EnvironmentAnalysisRequest
from app.schemas.drift import DriftAnalysisRequest

@router.post("/run-pipeline", status_code=status.HTTP_200_OK)
def run_full_pipeline(request: Sentinel1ProcessRequest):
    """
    Executes Phase 1 (Sentinel-1 SAR acquisition & preprocessing),
    Phase 2 (PyTorch U-Net AI Oil-Spill Detection),
    Phase 3 (Real Oil-Spill Mapping & Polygonization),
    Phase 4 (Real Wind & Ocean Current Analysis), and
    Phase 5 (Lagrangian Particle Drift Modelling & Origin Estimation).
    Returns combined structured metadata and output artifacts.
    """
    try:
        # Phase 1: Fetch and preprocess SAR imagery
        p1_result = sentinel1_service.fetch_and_process_sar(
            bbox=(request.bbox[0], request.bbox[1], request.bbox[2], request.bbox[3]),
            start_date=request.start_date,
            end_date=request.end_date,
            polarization=request.polarization,
            width=request.width,
            height=request.height,
        )

        # Phase 2: AI U-Net Detection
        geotiff_path = p1_result["output_file"]
        p2_result = oil_detection_service.run_detection(geotiff_path=geotiff_path)

        # Phase 3: Real Oil-Spill Mapping & Vector Polygonization
        p3_result = spill_mapping_service.run_spill_mapping(
            mask_path=p2_result["mask_file"],
            confidence_path=p2_result["confidence_file"],
            source_geotiff_path=geotiff_path,
            min_region_pixels=10,
        )

        # Phase 4: Real Wind & Ocean Current Analysis
        scene_id = p1_result["output_filename"].replace("_processed.tif", "")
        acq_time = p1_result.get("acquisition_time", "2024-06-29T01:03:54Z")
        centroid = p3_result.get("centroid") or {"latitude": (request.bbox[1] + request.bbox[3]) / 2.0, "longitude": (request.bbox[0] + request.bbox[2]) / 2.0}
        bbox_dict = p3_result.get("bbox") or {"min_lat": request.bbox[1], "min_lon": request.bbox[0], "max_lat": request.bbox[3], "max_lon": request.bbox[2]}

        env_req = EnvironmentAnalysisRequest(
            scene_id=scene_id,
            acquisition_time=acq_time,
            centroid=centroid,
            bbox=bbox_dict,
        )
        p4_result = environment_service.analyze_environment(env_req)

        # Phase 5: Lagrangian Drift Modelling & Probable Origin Estimation
        drift_req = DriftAnalysisRequest(
            centroid=centroid,
            bbox=bbox_dict,
            acquisition_time=acq_time,
            wind=p4_result.wind.model_dump(),
            ocean_current=p4_result.ocean_current.model_dump(),
            vector_field=p4_result.vector_field.model_dump(),
            particle_count=100,
            duration_hours=24.0,
        )
        p5_result = drift_modelling_service.run_drift_simulation(drift_req)

        overlay_filename = Path(p2_result["overlay_file"]).name
        mask_filename = Path(p2_result["mask_file"]).name
        conf_filename = Path(p2_result["confidence_file"]).name

        return {
            "status": "success",
            "phase": 5,
            "phase1": p1_result,
            "phase2": p2_result,
            "phase3": p3_result,
            "phase4": p4_result.model_dump(),
            "phase5": p5_result.model_dump(),
            "scene": {
                "id": scene_id,
                "satellite": "Sentinel-1",
                "product_type": p1_result.get("product_type", "GRD"),
                "polarization": p1_result.get("polarization", "VV"),
                "acquisition_time": acq_time,
            },
            "raster": {
                "width": p1_result.get("raster_info", {}).get("width", 512),
                "height": p1_result.get("raster_info", {}).get("height", 512),
                "dtype": "float32",
                "crs": p1_result.get("raster_info", {}).get("crs", "EPSG:4326"),
            },
            "preprocessing": {
                "completed": True,
            },
            "detection": {
                "model": "PyTorch U-Net",
                "model_type": "binary",
                "oil_detected": p3_result.get("spill_detected", False),
                "confidence": p3_result.get("confidence", 0.0),
            },
            "mapping": {
                "spill_detected": p3_result.get("spill_detected", False),
                "total_area_km2": p3_result.get("total_area_km2", 0.0),
                "total_area_m2": p3_result.get("total_area_m2", 0.0),
                "regions_count": p3_result.get("regions_count", 0),
                "centroid": centroid,
                "bbox": bbox_dict,
                "severity": p3_result.get("severity"),
                "geojson_file": Path(p3_result.get("geojson_file", "")).name,
            },
            "environment": p4_result.model_dump(),
            "drift": p5_result.model_dump(),
            "outputs": {
                "sar_preview": p1_result.get("preview_filename", ""),
                "mask": mask_filename,
                "confidence": conf_filename,
                "overlay": overlay_filename,
                "spill_polygon_geojson": Path(p3_result.get("geojson_file", "")).name,
                "spill_map_png": Path(p3_result.get("visualization_file", "")).name,
                "backward_drift_geojson": p5_result.outputs.get("backward_drift_geojson", ""),
                "forward_drift_geojson": p5_result.outputs.get("forward_drift_geojson", ""),
                "origin_zone_geojson": p5_result.outputs.get("origin_zone_geojson", ""),
                "drift_map_png": p5_result.outputs.get("drift_map_png", ""),
            },
        }
    except CDSEAuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error during pipeline execution: %s", str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Pipeline error: {str(e)}")

