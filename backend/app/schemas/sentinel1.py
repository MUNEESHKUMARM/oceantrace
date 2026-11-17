from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "OceanTrace AI Backend"


class AuthTestResponse(BaseModel):
    authenticated: bool
    service: str = "Copernicus Data Space Sentinel Hub"
    message: str


class Sentinel1SearchRequest(BaseModel):
    bbox: List[float] = Field(
        default=[64.5, 18.1, 65.7, 18.9],
        description="[min_lon, min_lat, max_lon, max_lat]"
    )
    start_date: Optional[str] = Field(default=None, description="YYYY-MM-DD or None for dynamic latest search")
    end_date: Optional[str] = Field(default=None, description="YYYY-MM-DD or None for dynamic latest search")
    max_results: int = Field(default=10, ge=1, le=50)


class Sentinel1SceneMetadata(BaseModel):
    id: str
    datetime: Optional[str] = None
    satellite: Optional[str] = "SENTINEL-1"
    product_type: Optional[str] = "GRD"
    polarization: Optional[List[str]] = ["VV", "VH"]
    orbit_direction: Optional[str] = "ASCENDING"
    bbox: List[float]


class Sentinel1ProcessRequest(BaseModel):
    bbox: List[float] = Field(
        default=[64.5, 18.1, 65.7, 18.9],
        description="[min_lon, min_lat, max_lon, max_lat]"
    )
    start_date: Optional[str] = Field(default=None, description="YYYY-MM-DD or None for dynamic latest discovery")
    end_date: Optional[str] = Field(default=None, description="YYYY-MM-DD or None for dynamic latest discovery")
    polarization: str = Field(default="VV", description="Polarization band (VV or VH)")
    width: int = Field(default=512, ge=64, le=2048)
    height: int = Field(default=512, ge=64, le=2048)


class Sentinel1ProcessResponse(BaseModel):
    status: str
    product_type: str
    output_file: str
    output_filename: str
    preview_file: Optional[str] = None
    preview_filename: Optional[str] = None
    thumbnail_file: Optional[str] = None
    thumbnail_filename: Optional[str] = None
    acquisition_time: str
    polarization: str
    processing: Dict[str, bool]
    raster_info: Dict[str, Any]
    visualization: Optional[Dict[str, Any]] = None
    source_product_id: Optional[str] = None
    platform: Optional[str] = None
    is_latest_available: Optional[bool] = None
    source_catalogue: Optional[str] = None

