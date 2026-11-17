from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class SceneMetadata(BaseModel):
    product_id: str = Field(..., description="Sentinel-1 scene product ID")
    platform: str = Field("SENTINEL-1", description="Satellite platform name")
    acquisition_datetime: str = Field(..., description="Exact Sentinel-1 acquisition sensing datetime ISO string")
    bbox: List[float] = Field(..., description="Bounding box [min_lon, min_lat, max_lon, max_lat]")

class WindData(BaseModel):
    source: str = Field("ECMWF Operational Open Data (IFS/AIFS)", description="Wind data source name")
    source_type: str = Field("operational_model_forecast", description="Environmental source classification: operational_model_forecast or ERA5 reanalysis")
    model: str = Field("ECMWF IFS (Operational)", description="Specific numerical weather prediction model name")
    run_time: str = Field(..., description="Operational forecast model run timestamp ISO string")
    valid_time: str = Field(..., description="Forecast valid timestamp ISO string")
    lead_time: str = Field("+0h", description="Forecast lead time")
    data_time: str = Field(..., description="Timestamp of actual retrieved wind data ISO string")
    offset_seconds: float = Field(0.0, description="Time offset from requested Sentinel-1 acquisition time in seconds")
    u10_mean: float = Field(..., description="Mean 10m Eastward wind component (m/s)")
    v10_mean: float = Field(..., description="Mean 10m Northward wind component (m/s)")
    speed_ms: float = Field(..., description="Wind speed in m/s")
    direction_deg: float = Field(..., description="Wind direction in degrees [0, 360)")
    direction_convention: str = Field("meteorological_from", description="Direction convention: meteorological_from (direction FROM which wind blows)")
    units: str = Field("m/s", description="Wind speed unit")
    status: str = Field("VALID", description="Data quality status: VALID, PARTIAL, or UNAVAILABLE")

class CurrentData(BaseModel):
    source: str = Field("Copernicus Marine Service (GLOBAL_ANALYSISFORECAST_PHY_001_024)", description="Ocean current data source name")
    dataset_id: str = Field("GLOBAL_ANALYSISFORECAST_PHY_001_024", description="Copernicus dataset identifier")
    source_type: str = Field("Copernicus Marine analysis/forecast current", description="Environmental source classification")
    data_time: str = Field(..., description="Timestamp of actual retrieved ocean current data ISO string")
    offset_seconds: float = Field(0.0, description="Time offset from requested Sentinel-1 acquisition time in seconds")
    u_mean: float = Field(..., description="Mean surface Eastward sea water velocity (m/s)")
    v_mean: float = Field(..., description="Mean surface Northward sea water velocity (m/s)")
    speed_ms: float = Field(..., description="Ocean current speed in m/s")
    direction_deg: float = Field(..., description="Ocean current direction in degrees [0, 360)")
    direction_convention: str = Field("oceanographic_towards", description="Direction convention: oceanographic_towards (direction TOWARDS which current flows)")
    units: str = Field("m/s", description="Ocean current velocity unit")
    status: str = Field("VALID", description="Data quality status: VALID, PARTIAL, or UNAVAILABLE")

class VectorFieldPoint(BaseModel):
    latitude: float
    longitude: float
    u: float
    v: float
    speed: float
    direction: float
    wind_u: Optional[float] = None
    wind_v: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    current_u: Optional[float] = None
    current_v: Optional[float] = None
    current_speed: Optional[float] = None
    current_direction: Optional[float] = None

class VectorFieldGroup(BaseModel):
    grid_rows: int = Field(3, description="Sampling grid rows")
    grid_columns: int = Field(3, description="Sampling grid columns")
    total_points: int = Field(10, description="Total sampled spatial vector points")
    wind: List[VectorFieldPoint]
    current: List[VectorFieldPoint]

class TimestampInfo(BaseModel):
    requested: str = Field(..., description="Requested Sentinel-1 acquisition ISO timestamp")
    wind_data: str = Field(..., description="Actual ECMWF IFS/AIFS wind data ISO timestamp")
    current_data: str = Field(..., description="Actual Copernicus ocean current data ISO timestamp")
    time_difference_sec: float = Field(..., description="Time offset in seconds")

class SourceMetadata(BaseModel):
    wind: str = Field("ECMWF Operational Open Data (IFS/AIFS)", description="Wind data source")
    current: str = Field("Copernicus Marine Service (GLOBAL_ANALYSISFORECAST_PHY_001_024)", description="Ocean current data source")
    classification: str = Field("OPERATIONAL_MODEL_FORECAST_AND_ANALYSIS", description="Observation classification")

class EnvironmentAnalysisRequest(BaseModel):
    scene_id: Optional[str] = Field(None, description="Sentinel-1 scene ID")
    acquisition_time: Optional[str] = Field(None, description="Sentinel-1 acquisition ISO timestamp")
    centroid: Optional[Dict[str, float]] = Field(None, description="Centroid dict with latitude and longitude")
    bbox: Optional[Dict[str, float]] = Field(None, description="BBox dict with min_lat, min_lon, max_lat, max_lon")
    spill_polygon: Optional[Dict[str, Any]] = Field(None, description="GeoJSON geometry or feature")
    spill_conditioned: bool = Field(False, description="Whether environmental analysis is conditioned on a detected spill region")
    spill_regions_count: int = Field(0, description="Number of Phase 3 detected spill regions")
    mode: str = Field("INCIDENT_TIME", description="Environment mode: INCIDENT_TIME or LIVE_NRT")

class EnvironmentAnalysisResponse(BaseModel):
    status: str = "success"
    phase: int = 4
    scene: SceneMetadata
    timestamp: TimestampInfo
    wind: WindData
    ocean_current: CurrentData
    sources: SourceMetadata
    vector_field: VectorFieldGroup
    analysis_context: str = Field("scene/AOI environmental context", description="Environmental spatial analysis context")
    spill_conditioned: bool = Field(False, description="Whether analysis is conditioned on a detected spill polygon")
    spill_regions_count: int = Field(0, description="Number of detected spill regions")
    mode: str = Field("INCIDENT_TIME", description="Environment analysis mode: INCIDENT_TIME or LIVE_NRT")
