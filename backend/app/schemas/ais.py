from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class AISPositionReport(BaseModel):
    """
    Normalized internal representation of an AIS PositionReport event.
    Strictly validated for coordinate bounds and required identifiers.
    """
    mmsi: str = Field(..., description="9-digit Vessel MMSI string")
    timestamp_utc: datetime = Field(..., description="AIS-reported UTC timestamp")
    latitude: float = Field(..., description="Latitude in decimal degrees (-90 to +90)")
    longitude: float = Field(..., description="Longitude in decimal degrees (-180 to +180)")
    sog_knots: Optional[float] = Field(None, description="Speed Over Ground in knots")
    cog_degrees: Optional[float] = Field(None, description="Course Over Ground in degrees (0 to 360)")
    true_heading: Optional[float] = Field(None, description="True Heading in degrees")
    navigational_status: Optional[int] = Field(None, description="Navigational Status integer code")
    position_accuracy: Optional[bool] = Field(None, description="High accuracy position flag")
    valid_position: bool = Field(True, description="Validity flag of raw AIS position")
    ais_message_type: str = Field("PositionReport", description="AIS Message Type string")
    source: str = Field("aisstream", description="Data source identifier")
    received_at_utc: datetime = Field(..., description="Backend receipt timestamp in UTC")

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if not (-90.0 <= v <= 90.0):
            raise ValueError(f"Latitude out of bounds: {v}")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if not (-180.0 <= v <= 180.0):
            raise ValueError(f"Longitude out of bounds: {v}")
        return v


class AISCollectorStatus(BaseModel):
    """
    Health and status metrics of the Phase 6.1 AISStream live WebSocket collector.
    Never exposes API secrets or internal credentials.
    """
    service: str = "AISStream"
    available: bool = Field(..., description="True if API key is present and service is operational")
    connected: bool = Field(..., description="True if WebSocket connection is active")
    subscription_active: bool = Field(..., description="True if AOI subscription confirmed")
    last_message_at: Optional[str] = Field(None, description="ISO timestamp of last received WebSocket message")
    last_position_at: Optional[str] = Field(None, description="ISO timestamp of last stored AIS position")
    messages_received: int = Field(0, description="Total WebSocket messages received")
    messages_stored: int = Field(0, description="Total valid AIS positions stored in DB")
    messages_rejected: int = Field(0, description="Total malformed/invalid messages discarded")
    tracked_mmsi_count: int = Field(0, description="Number of distinct vessel MMSIs observed")
    last_error: Optional[str] = Field(None, description="Safe diagnostic message of last encountered error")


class AISCorrelationCandidate(BaseModel):
    """
    Phase 6.2 Unordered AIS Vessel Correlation Evidence.
    Strictly contains spatial and temporal observation metrics.
    Does NOT contain vessel scores, ranks, culpability tags, or causation claims.
    """
    mmsi: str = Field(..., description="Vessel MMSI string identifier")
    observation_count: int = Field(..., description="Total valid AIS observations in release window")
    first_observation: str = Field(..., description="ISO timestamp of earliest observation in window")
    last_observation: str = Field(..., description="ISO timestamp of latest observation in window")
    minimum_distance_to_origin_km: float = Field(..., description="Minimum geodesic WGS84 distance to origin polygon in km")
    closest_approach_time: str = Field(..., description="ISO timestamp of position closest to origin")
    position_count_inside_origin_zone: int = Field(..., description="Number of positions strictly inside origin polygon")
    track_intersects_origin_zone: bool = Field(..., description="True if vessel track line intersects origin polygon")
    temporal_overlap: bool = Field(True, description="True if observations fall within release window")
    track_geometry_available: bool = Field(..., description="True if >=2 valid points exist to construct track line")
    mean_sog_knots: Optional[float] = Field(None, description="Mean Speed Over Ground in knots")
    max_sog_knots: Optional[float] = Field(None, description="Maximum Speed Over Ground in knots")
    min_sog_knots: Optional[float] = Field(None, description="Minimum Speed Over Ground in knots")
    mean_cog_degrees: Optional[float] = Field(None, description="Trigonometric circular mean Course Over Ground in degrees [0, 360)")
    navigation_status_values: List[int] = Field(default_factory=list, description="List of observed navigation status codes")


class AISCorrelationRequest(BaseModel):
    """
    Input request for Phase 6.2 AIS Spatial + Temporal Correlation.
    """
    scene_id: Optional[str] = Field(None, description="Sentinel-1 scene product ID or timestamp")
    search_radius_km: Optional[float] = Field(None, description="Engineering search radius in km (defaults to 50.0 km)")
    drift_analysis: Optional[Dict[str, Any]] = Field(None, description="Canonical Phase 5 DriftAnalysisResponse model dict")


class AISCorrelationResponse(BaseModel):
    """
    Phase 6.2 AIS Correlation Engine Response.
    Consumes canonical Phase 5 outputs and returns unordered evidence candidates.
    """
    status: str = "success"
    phase: float = 6.2
    scene_id: str = Field(..., description="Sentinel-1 product ID or scene identifier")
    ais_available: bool = Field(..., description="True if live AIS collector/database is accessible")
    spill_conditioned: bool = Field(False, description="Canonical Phase 5 spill conditioning state")
    origin_available: bool = Field(False, description="Canonical Phase 5 origin zone availability state")
    correlation_available: bool = Field(False, description="True if spatial/temporal AIS correlation executed")
    release_window_start: Optional[str] = Field(None, description="Phase 5 estimated release window start UTC")
    release_window_end: Optional[str] = Field(None, description="Phase 5 estimated release window end UTC")
    origin_centroid: Optional[Dict[str, float]] = Field(None, description="Phase 5 origin centroid with latitude and longitude")
    origin_area_km2: float = Field(0.0, description="Phase 5 origin zone area in sq km")
    search_radius_km: float = Field(50.0, description="Engineering search radius in km used for candidate retrieval")
    candidate_count: int = Field(0, description="Total candidate vessels meeting search/overlap criteria")
    candidates: List[AISCorrelationCandidate] = Field(default_factory=list, description="Unordered evidence candidate list")
    reason: Optional[str] = Field(None, description="Diagnostic explanation when correlation is unavailable")
    output_file: Optional[str] = Field(None, description="Filename of persisted JSON correlation artifact")
    ais_source: str = Field("aisstream", description="Source of AIS data")
    methodology_version: str = Field("6.2-evidence-v1", description="Phase 6.2 methodology version")


class AISRankedCandidate(BaseModel):
    """
    Phase 6.3 Explainable Ranked Candidate Vessel.
    Orders candidates by an engineering correlation score derived from Phase 6.2 evidence.
    Does NOT represent a probability of guilt, legal attribution, or proof of causation.
    """
    rank: int = Field(..., description="1-indexed candidate rank based on composite engineering score")
    mmsi: str = Field(..., description="Vessel MMSI string identifier")
    candidate_score: float = Field(..., description="Engineering correlation score in [0.0, 1.0]")
    score_type: str = Field("engineering_correlation_score", description="Explicit designation of score type")
    evidence: Dict[str, float] = Field(..., description="Breakdown of normalized dimension scores")
    evidence_summary: List[str] = Field(default_factory=list, description="Human-readable evidence statements")
    explanation: str = Field(..., description="Transparent, explainable ranking interpretation string")
    raw_evidence: AISCorrelationCandidate = Field(..., description="Underlying Phase 6.2 evidence candidate")


class AISRankingRequest(BaseModel):
    """
    Input request for Phase 6.3 Explainable AIS Candidate Ranking Engine.
    """
    scene_id: Optional[str] = Field(None, description="Sentinel-1 scene product ID or timestamp")
    correlation_response: Optional[Dict[str, Any]] = Field(None, description="Phase 6.2 AISCorrelationResponse model dict")
    spatial_weight: Optional[float] = Field(None, description="Weight for spatial proximity dimension")
    intersection_weight: Optional[float] = Field(None, description="Weight for origin-zone intersection dimension")
    temporal_weight: Optional[float] = Field(None, description="Weight for temporal overlap dimension")
    observation_weight: Optional[float] = Field(None, description="Weight for observation density dimension")


class AISRankingResponse(BaseModel):
    """
    Phase 6.3 Explainable AIS Candidate Ranking Response.
    Titled strictly as POTENTIAL SOURCE VESSEL CANDIDATE RANKING.
    """
    status: str = "success"
    phase: float = 6.3
    scene_id: str = Field(..., description="Sentinel-1 product ID or scene identifier")
    ranking_title: str = Field("POTENTIAL SOURCE VESSEL CANDIDATE RANKING", description="Official non-causation title")
    ranking_available: bool = Field(False, description="True if Phase 6.2 candidates were available and ranked")
    ranking_methodology_version: str = Field("6.3.1-engineering-v1", description="Ranking methodology version string")
    ranking_configuration: Dict[str, float] = Field(..., description="Configured/normalized weights used for feature scoring")
    configured_weights: Dict[str, float] = Field(default_factory=dict, description="Raw configured input weights prior to normalization")
    normalized_weights: Dict[str, float] = Field(default_factory=dict, description="Normalized weights summing to 1.0")
    candidate_count: int = Field(0, description="Total ranked candidate count")
    ranked_candidates: List[AISRankedCandidate] = Field(default_factory=list, description="Ordered candidate list with explanations")
    interpretation: str = Field(
        "Candidates are ordered by an engineering evidence score and are not presented as proof of causation or responsibility.",
        description="Mandatory semantic disclaimer interpretation string",
    )
    reason: Optional[str] = Field(None, description="Diagnostic explanation when ranking is unavailable")
    output_file: Optional[str] = Field(None, description="Filename of persisted JSON ranking artifact")
    source_correlation_phase: str = Field("Phase 6.2", description="Provenanced source phase")
