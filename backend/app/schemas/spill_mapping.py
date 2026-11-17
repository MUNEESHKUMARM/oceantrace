from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

class Centroid(BaseModel):
    latitude: float = Field(..., description="Latitude of spill centroid in degrees EPSG:4326")
    longitude: float = Field(..., description="Longitude of spill centroid in degrees EPSG:4326")

class BoundingBox(BaseModel):
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float

class SeverityInfo(BaseModel):
    level: str = Field(..., description="Severity category: Minor, Moderate, Major, or Critical")
    index: float = Field(..., description="Normalized severity score [0.0 to 1.0]")
    basis: str = Field(..., description="Documented rule basis for severity calculation")

class SpillRegionDetail(BaseModel):
    region_id: int
    pixel_count: Optional[int] = Field(None, description="Number of connected pixels in region")
    area_m2: float
    area_km2: float
    centroid: Centroid
    bbox: BoundingBox

class SpillMappingRequest(BaseModel):
    mask_path: str = Field(..., description="Path to Phase 2 binary prediction mask GeoTIFF")
    confidence_path: Optional[str] = Field(None, description="Path to Phase 2 confidence raster GeoTIFF")
    source_geotiff_path: Optional[str] = Field(None, description="Path to preprocessed Sentinel-1 SAR GeoTIFF")
    min_region_pixels: int = Field(10, description="Minimum pixel size threshold for noise removal filtering")
    acquisition_time: Optional[str] = Field(None, description="Sentinel-1 acquisition datetime ISO string")
    scene_id: Optional[str] = Field(None, description="Sentinel-1 scene/product identifier")

class SpillMappingResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: str = "success"
    phase: int = 3
    spill_detected: bool
    regions_count: int
    total_area_m2: float
    total_area_km2: float
    centroid: Optional[Centroid] = None
    bbox: Optional[BoundingBox] = None
    severity: SeverityInfo
    confidence: float
    acquisition_time: str
    processing_time: str
    scene_id: str
    spill_regions: List[SpillRegionDetail] = []
    geojson_file: str
    cleaned_mask_file: str
    visualization_file: str
