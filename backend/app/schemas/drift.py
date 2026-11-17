from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class TrajectoryPoint(BaseModel):
    particle_id: int
    timestamp: str
    latitude: float
    longitude: float

class DriftSimulationSummary(BaseModel):
    duration_hours: float = Field(..., description="Simulation duration in hours")
    particle_count: int = Field(..., description="Number of particles simulated")
    trajectory_file: str = Field(..., description="Path to GeoJSON file storing particle trajectories")
    points_sample: List[TrajectoryPoint] = Field(default_factory=list, description="Sample points for display")

class OriginZoneInfo(BaseModel):
    zone_file: str = Field(..., description="GeoJSON file path of probable origin zone polygon")
    centroid: Dict[str, float] = Field(..., description="Centroid dict with latitude and longitude")
    area_km2: float = Field(..., description="Area of probable origin zone in sq km")
    confidence: float = Field(..., description="Origin confidence score (0.0 to 1.0)")
    geojson_feature: Dict[str, Any] = Field(default_factory=dict, description="GeoJSON feature geometry of origin zone")

class ReleaseWindow(BaseModel):
    start: str = Field(..., description="Estimated historical release window start ISO timestamp")
    end: str = Field(..., description="Estimated historical release window end ISO timestamp")

class DriftAnalysisRequest(BaseModel):
    spill_polygon: Optional[Dict[str, Any]] = Field(None, description="Phase 3 oil spill GeoJSON geometry or feature")
    centroid: Optional[Dict[str, float]] = Field(default_factory=dict, description="Phase 3 spill centroid with latitude and longitude")
    bbox: Optional[Dict[str, float]] = Field(default_factory=dict, description="Phase 3 spill bounding box")
    acquisition_time: str = Field(..., description="Sentinel-1 acquisition ISO timestamp")
    wind: Dict[str, Any] = Field(..., description="Phase 4 wind data dict with u10_mean, v10_mean, speed_ms, direction_deg")
    ocean_current: Dict[str, Any] = Field(..., description="Phase 4 ocean current data dict with u_mean, v_mean, speed_ms, direction_deg")
    vector_field: Optional[Dict[str, Any]] = Field(None, description="Phase 4 vector field points")
    particle_count: int = Field(100, description="Number of particles to simulate (default 100)")
    time_step_mins: int = Field(15, description="Integration timestep in minutes (default 15)")
    duration_hours: float = Field(24.0, description="Simulation duration in hours (default 24)")
    wind_drift_coeff: float = Field(0.03, description="Wind leeway coefficient (default 0.03)")
    diffusion_coeff: float = Field(1.0, description="Stochastic diffusion coefficient m2/s")
    spill_conditioned: Optional[bool] = Field(False, description="Flag indicating if a valid spill region exists")
    spill_regions_count: Optional[int] = Field(0, description="Number of detected spill regions")

class DriftAnalysisResponse(BaseModel):
    status: str = "success"
    phase: int = 5
    drift_available: bool = Field(False, description="Flag indicating if drift simulation is active")
    spill_conditioned: bool = Field(False, description="Flag indicating if spill geometry was conditioned")
    origin_available: bool = Field(False, description="Flag indicating if probable origin zone is available")
    backward_drift: DriftSimulationSummary
    forward_drift: DriftSimulationSummary
    origin: OriginZoneInfo
    release_window: ReleaseWindow
    probable_origin_zone: Optional[Dict[str, Any]] = Field(None, description="Phase 6 schema compatibility: GeoJSON feature of origin zone")
    origin_centroid: Optional[Dict[str, float]] = Field(None, description="Phase 6 schema compatibility: Origin centroid lat/lon")
    estimated_release_window: Optional[Dict[str, str]] = Field(None, description="Phase 6 schema compatibility: Release window start/end")
    origin_confidence: Optional[float] = Field(None, description="Phase 6 schema compatibility: Origin confidence score")
    outputs: Dict[str, str] = Field(default_factory=dict)
