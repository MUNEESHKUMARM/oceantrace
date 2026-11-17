import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator

MANDATORY_SCIENTIFIC_LIMITATION = (
    "OceanTrace AI produces model-derived decision-support information. "
    "Predicted spill regions, drift trajectories, probable origin zones, AIS "
    "correlations, candidate rankings, and operational attention levels require "
    "independent validation and do not independently establish spill causation, "
    "legal responsibility, or the identity of a responsible vessel."
)

MANDATORY_HUMAN_REVIEW_TEXT = (
    "This report is an automated decision-support output and requires independent human review. "
    "It does not establish spill causation or legal responsibility."
)


class ReportSectionIdent(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    report_id: str
    scene_id: str
    sentinel_product_id: str
    acquisition_timestamp: str
    report_generated_at: str
    system_version: str = "1.0.0"
    methodology_versions: Dict[str, str]
    source_provenance: Dict[str, str]
    source_phase: str = "Phase 7"


class ReportSectionDetection(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    oil_detected: bool
    predicted_oil_pixels: int
    predicted_oil_percentage: float
    model_reference: str
    preprocessing_normalization: str
    detection_output_path: str
    summary: str
    source_phase: str = "Phase 2"


class ReportSectionMapping(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    spill_detected: bool
    region_count: int
    total_area_km2: float
    total_area_m2: float
    severity: Optional[str] = None
    geojson_file: str
    centroid: Optional[Dict[str, float]] = None
    bbox: Optional[Dict[str, float]] = None
    summary: str
    source_phase: str = "Phase 3"


class ReportSectionEnvironment(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    wind_u10: float
    wind_v10: float
    wind_speed_m_s: float
    wind_direction_deg: float
    wind_source: str
    wind_timestamp: str
    wind_offset_seconds: float
    current_u: float
    current_v: float
    current_speed_m_s: float
    current_direction_deg: float
    current_source: str
    current_timestamp: str
    current_offset_seconds: float
    summary: str
    source_phase: str = "Phase 4"


class ReportSectionDrift(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    drift_available: bool
    origin_available: bool
    particle_count: int
    timestep_seconds: int
    duration_hours: float
    wind_leeway_coefficient: float
    diffusion_coefficient: float
    forward_drift_geojson: str
    backward_drift_geojson: str
    origin_centroid: Optional[Dict[str, float]] = None
    origin_area_km2: Optional[float] = None
    estimated_release_window: Optional[Dict[str, str]] = None
    origin_confidence_score: Optional[float] = None
    origin_confidence_semantics: str = (
        "Phase 5 origin confidence is a model-derived heuristic score and is not a calibrated probability."
    )
    summary: str
    source_phase: str = "Phase 5"


class ReportSectionAIS(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    ais_available: bool
    collector_status: str
    ais_source: str
    correlation_available: bool
    observations_considered: int
    candidate_count: int
    spatial_evidence: Dict[str, Any]
    temporal_evidence: Dict[str, Any]
    candidate_summary: List[Dict[str, Any]]
    summary: str
    source_phase: str = "Phase 6.1/6.2"


class ReportSectionRanking(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    ranking_available: bool
    ranking_title: str
    ranking_methodology_version: str
    configured_weights: Dict[str, float]
    normalized_weights: Dict[str, float]
    candidate_count: int
    ranked_candidates: List[Dict[str, Any]]
    ranking_semantics: str = (
        "Candidate scores are engineering correlation scores used to inform operational attention. "
        "They are not calibrated probabilities of causation or responsibility."
    )
    summary: str
    source_phase: str = "Phase 6.3"


class OperationalAlert(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    alert_available: bool
    attention_level: str  # NO_EVENT, LOW_ATTENTION, MEDIUM_ATTENTION, HIGH_ATTENTION, CRITICAL_ATTENTION
    alert_type: str = "POTENTIAL_OIL_SPILL_INVESTIGATION"
    scene_id: str
    generated_at: str
    trigger_evidence: List[str]
    requires_human_review: bool
    attention_rule_version: str = "7.0.0-deterministic-v1"
    disclaimer: str = MANDATORY_HUMAN_REVIEW_TEXT

    @model_validator(mode="after")
    def validate_human_review(self):
        # Strict rule: If alert_available is True, requires_human_review MUST be True
        if self.alert_available and not self.requires_human_review:
            raise ValueError(
                "Compliance Violation: Genuine alerts (alert_available=True) MUST require human review (requires_human_review=True)."
            )
        return self


class InvestigationReportRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    scene_id: Optional[str] = Field(
        default=None,
        description="Sentinel-1 scene ID, or None for current production scene",
    )
    spill_attention_area_threshold_km2: Optional[float] = Field(
        default=None,
        description="Override threshold for spill area escalation (km²)",
    )
    origin_high_attention_threshold: Optional[float] = Field(
        default=None,
        description="Override threshold for origin high attention heuristic score",
    )
    ais_high_correlation_threshold: Optional[float] = Field(
        default=None,
        description="Override threshold for candidate AIS high correlation score",
    )


class InvestigationReportResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: str = "success"
    phase: float = 7.0
    report_id: str
    scene_id: str
    generated_at: str
    identification: ReportSectionIdent
    sar_detection: ReportSectionDetection
    spill_mapping: ReportSectionMapping
    environmental_conditions: ReportSectionEnvironment
    drift_analysis: ReportSectionDrift
    ais_correlation: ReportSectionAIS
    vessel_candidate_ranking: ReportSectionRanking
    operational_alert: OperationalAlert
    attention_threshold_configuration: Dict[str, Any]
    output_files: Dict[str, str]
    scientific_limitation: str = MANDATORY_SCIENTIFIC_LIMITATION


class InvestigationStatusResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    scene_id: str
    report_available: bool
    alert_available: bool
    attention_level: str
    requires_human_review: bool
    generated_at: Optional[str] = None
    report_json_path: Optional[str] = None
    report_md_path: Optional[str] = None
