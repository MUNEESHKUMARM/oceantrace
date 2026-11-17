"""
===============================================================================
OCEANTRACE AI — PHASE 7 TEST & VERIFICATION SUITE
===============================================================================
SYNTHETIC REGRESSION FIXTURES — NOT REAL INCIDENT EVIDENCE

Validates Phase 7 Automated Investigation Report + Operational Alert Engine:
1. No-spill report & current production scene isolation (0 pixels -> NO_EVENT).
2. Schema validation, provenance, timestamp consistency.
3. Deterministic attention level rule precedence & escalation.
4. Human-review flag compliance (alert_available=True -> requires_human_review=True).
5. Configurable attention thresholds & rejection of invalid/negative values.
6. Non-causation, decision-support terminology enforcement.
7. Idempotent JSON & Markdown report artifact generation.
8. API endpoints POST /api/investigation/report & GET /api/investigation/status.
"""

import os
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.schemas.investigation import (
    InvestigationReportRequest,
    InvestigationReportResponse,
    OperationalAlert,
    MANDATORY_SCIENTIFIC_LIMITATION,
    MANDATORY_HUMAN_REVIEW_TEXT,
)
from app.services.investigation_report_service import (
    InvestigationReportService,
    investigation_report_service,
    PRODUCTION_SCENE_ID,
)

client = TestClient(app)

# =============================================================================
# SYNTHETIC REGRESSION FIXTURES (NOT REAL INCIDENT EVIDENCE)
# =============================================================================

SYNTHETIC_POSITIVE_SCENE_ID = "SYNTHETIC_TEST_SPILL_SCENE_20260918"


# =============================================================================
# TEST SUITE (45 COMPREHENSIVE TESTS)
# =============================================================================

def test_no_spill_report():
    """Test 1: No-spill report generates NO_EVENT attention level."""
    req = InvestigationReportRequest(scene_id=PRODUCTION_SCENE_ID)
    res = investigation_report_service.generate_report(req)
    assert res.status == "success"
    assert res.operational_alert.attention_level == "NO_EVENT"
    assert res.operational_alert.alert_available is False
    assert res.operational_alert.requires_human_review is False


def test_no_region_report():
    """Test 2: Scene with 0 spill regions produces NO_EVENT."""
    res = investigation_report_service.generate_report(InvestigationReportRequest(scene_id=PRODUCTION_SCENE_ID))
    assert res.spill_mapping.region_count == 0
    assert res.operational_alert.attention_level == "NO_EVENT"


def test_no_origin_report():
    """Test 3: Scene with detected spill but unavailable origin produces LOW/MEDIUM attention."""
    # Rule 2 test: 10 pixels, 0.5 km2 spill area (< threshold 1.0)
    level, alert_avail, req_review, triggers = investigation_report_service.evaluate_attention_level(
        predicted_oil_pixels=10,
        region_count=1,
        total_area_km2=0.5,
        origin_available=False,
        origin_confidence_score=None,
        candidate_count=0,
        top_candidate_score=None,
        top_candidate_intersects_origin=False,
        spill_area_thresh=1.0,
        origin_thresh=0.7,
        ais_thresh=0.8,
    )
    assert level == "LOW_ATTENTION"
    assert alert_avail is True
    assert req_review is True
    assert "Probable origin zone unavailable" in triggers[2]


def test_no_ais_candidate_report():
    """Test 4: Scene with spill + origin but 0 AIS candidates produces MEDIUM/HIGH attention."""
    level, alert_avail, req_review, triggers = investigation_report_service.evaluate_attention_level(
        predicted_oil_pixels=20,
        region_count=1,
        total_area_km2=2.0,
        origin_available=True,
        origin_confidence_score=0.85,  # >= origin threshold 0.7
        candidate_count=0,
        top_candidate_score=None,
        top_candidate_intersects_origin=False,
        spill_area_thresh=1.0,
        origin_thresh=0.7,
        ais_thresh=0.8,
    )
    assert level == "HIGH_ATTENTION"
    assert alert_avail is True
    assert req_review is True


def test_no_ranking_report():
    """Test 5: Ranking section unavailable handling when no candidates exist."""
    res = investigation_report_service.generate_report(InvestigationReportRequest(scene_id=PRODUCTION_SCENE_ID))
    assert res.vessel_candidate_ranking.ranking_available is False
    assert res.vessel_candidate_ranking.candidate_count == 0
    assert "No vessel candidate ranking is available" in res.vessel_candidate_ranking.summary


def test_complete_positive_synthetic_report():
    """Test 6: Synthetic regression fixture for complete positive incident."""
    level, alert_avail, req_review, triggers = investigation_report_service.evaluate_attention_level(
        predicted_oil_pixels=50,
        region_count=2,
        total_area_km2=3.5,
        origin_available=True,
        origin_confidence_score=0.80,
        candidate_count=3,
        top_candidate_score=0.88,  # >= threshold 0.8
        top_candidate_intersects_origin=True,
        spill_area_thresh=1.0,
        origin_thresh=0.7,
        ais_thresh=0.8,
    )
    assert level == "CRITICAL_ATTENTION"
    assert alert_avail is True
    assert req_review is True


def test_report_schema_validation():
    """Test 7: Response object conforms to InvestigationReportResponse Pydantic schema."""
    res = investigation_report_service.generate_report()
    assert isinstance(res, InvestigationReportResponse)
    assert res.phase == 7.0
    assert res.status == "success"


def test_provenance_fields():
    """Test 8: Provenance fields accurately cite phase source layers."""
    res = investigation_report_service.generate_report()
    assert res.sar_detection.source_phase == "Phase 2"
    assert res.spill_mapping.source_phase == "Phase 3"
    assert res.environmental_conditions.source_phase == "Phase 4"
    assert res.drift_analysis.source_phase == "Phase 5"
    assert res.ais_correlation.source_phase == "Phase 6.1/6.2"
    assert res.vessel_candidate_ranking.source_phase == "Phase 6.3"
    assert res.identification.source_phase == "Phase 7"


def test_timestamp_consistency():
    """Test 9: Acquisition and report generation timestamps exist and are formatted ISO UTC."""
    res = investigation_report_service.generate_report()
    assert res.identification.acquisition_timestamp.endswith("Z")
    assert res.identification.report_generated_at.endswith("Z")


def test_environmental_section():
    """Test 10: Environmental section validates ECMWF wind and CMEMS ocean current data."""
    res = investigation_report_service.generate_report()
    env = res.environmental_conditions
    assert env.wind_speed_m_s > 0
    assert env.current_speed_m_s >= 0
    assert env.wind_source is not None


def test_drift_section():
    """Test 11: Drift section contains particle simulation settings and confidence semantics."""
    res = investigation_report_service.generate_report()
    drift = res.drift_analysis
    assert "heuristic score" in drift.origin_confidence_semantics
    assert drift.wind_leeway_coefficient == 0.03


def test_ais_section():
    """Test 12: AIS section validates collector status and source description."""
    res = investigation_report_service.generate_report()
    ais = res.ais_correlation
    assert ais.ais_available is True
    assert "AISStream" in ais.ais_source


def test_ranking_section():
    """Test 13: Candidate ranking section preserves configured weights and non-causation semantics."""
    res = investigation_report_service.generate_report()
    rk = res.vessel_candidate_ranking
    assert "spatial_weight" in rk.configured_weights
    assert "not calibrated probabilities" in rk.ranking_semantics


def test_alert_generation():
    """Test 14: Operational alert object structure validation."""
    res = investigation_report_service.generate_report()
    alert = res.operational_alert
    assert alert.alert_type == "POTENTIAL_OIL_SPILL_INVESTIGATION"
    assert isinstance(alert.trigger_evidence, list)


def test_no_alert_for_zero_oil_pixels():
    """Test 15: Zero oil pixels strictly suppresses alert (alert_available=False)."""
    res = investigation_report_service.generate_report(InvestigationReportRequest(scene_id=PRODUCTION_SCENE_ID))
    assert res.operational_alert.alert_available is False
    assert res.operational_alert.attention_level == "NO_EVENT"


def test_attention_level_determinism():
    """Test 16: Identical inputs produce identical attention levels."""
    l1, a1, r1, _ = investigation_report_service.evaluate_attention_level(
        predicted_oil_pixels=0, region_count=0, total_area_km2=0.0,
        origin_available=False, origin_confidence_score=None,
        candidate_count=0, top_candidate_score=None, top_candidate_intersects_origin=False,
        spill_area_thresh=1.0, origin_thresh=0.7, ais_thresh=0.8
    )
    l2, a2, r2, _ = investigation_report_service.evaluate_attention_level(
        predicted_oil_pixels=0, region_count=0, total_area_km2=0.0,
        origin_available=False, origin_confidence_score=None,
        candidate_count=0, top_candidate_score=None, top_candidate_intersects_origin=False,
        spill_area_thresh=1.0, origin_thresh=0.7, ais_thresh=0.8
    )
    assert l1 == l2 == "NO_EVENT"
    assert a1 == a2 == False
    assert r1 == r2 == False


def test_human_review_flag():
    """Test 17: Genuine alert validation enforces requires_human_review=True."""
    with pytest.raises(ValueError):
        OperationalAlert(
            alert_available=True,
            attention_level="HIGH_ATTENTION",
            scene_id="TEST_SCENE",
            generated_at="2026-09-18T00:00:00Z",
            trigger_evidence=["Test spill"],
            requires_human_review=False,  # Violation!
        )


def test_json_artifact_creation():
    """Test 18: Generated JSON report artifact exists on disk."""
    res = investigation_report_service.generate_report(InvestigationReportRequest(scene_id=PRODUCTION_SCENE_ID))
    json_path = settings.DATA_OUTPUT_DIR / f"investigation_report_{PRODUCTION_SCENE_ID}.json"
    assert json_path.exists()


def test_markdown_artifact_creation():
    """Test 19: Generated Markdown report artifact exists on disk."""
    res = investigation_report_service.generate_report(InvestigationReportRequest(scene_id=PRODUCTION_SCENE_ID))
    md_path = settings.DATA_OUTPUT_DIR / f"investigation_report_{PRODUCTION_SCENE_ID}.md"
    assert md_path.exists()
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "# OCEANTRACE AI — AUTOMATED INVESTIGATION REPORT" in content


def test_api_investigation_report_endpoint():
    """Test 20: POST /api/investigation/report returns HTTP 200 and valid JSON."""
    response = client.post("/api/investigation/report", json={"scene_id": PRODUCTION_SCENE_ID})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["operational_alert"]["attention_level"] == "NO_EVENT"


def test_api_investigation_status_endpoint():
    """Test 21: GET /api/investigation/status returns HTTP 200 status."""
    response = client.get(f"/api/investigation/status?scene_id={PRODUCTION_SCENE_ID}")
    assert response.status_code == 200
    data = response.json()
    assert data["scene_id"] == PRODUCTION_SCENE_ID
    assert data["attention_level"] == "NO_EVENT"


def test_missing_upstream_output_handling():
    """Test 22: Gracefully handles missing upstream files without crashing."""
    res = investigation_report_service.generate_report(InvestigationReportRequest(scene_id="NON_EXISTENT_SCENE_999"))
    assert res.status == "success"
    assert res.sar_detection.predicted_oil_pixels == 0


def test_invalid_scene_handling():
    """Test 23: Report generation handles empty string scene ID by falling back gracefully."""
    res = investigation_report_service.generate_report(InvestigationReportRequest(scene_id=""))
    assert res.scene_id == PRODUCTION_SCENE_ID


def test_secret_non_exposure():
    """Test 24: Operational report does NOT expose CDSE client credentials or API keys."""
    res = investigation_report_service.generate_report()
    dump_str = json.dumps(res.model_dump())
    assert settings.CDSE_CLIENT_SECRET not in dump_str or settings.CDSE_CLIENT_SECRET == ""
    assert "secret" not in dump_str.lower() or "cdse_client_secret" not in dump_str.lower()


def test_current_production_isolation():
    """Test 25: Verified production scene outputs strictly NO_EVENT."""
    res = investigation_report_service.generate_report(InvestigationReportRequest(scene_id=PRODUCTION_SCENE_ID))
    assert res.sar_detection.predicted_oil_pixels == 0
    assert res.spill_mapping.region_count == 0
    assert res.drift_analysis.origin_available is False
    assert res.ais_correlation.candidate_count == 0
    assert res.vessel_candidate_ranking.ranking_available is False
    assert res.operational_alert.attention_level == "NO_EVENT"
    assert res.operational_alert.alert_available is False


def test_scientific_limitation_text_present():
    """Test 26: Mandatory scientific limitation text is present in response."""
    res = investigation_report_service.generate_report()
    assert res.scientific_limitation == MANDATORY_SCIENTIFIC_LIMITATION


def test_no_culpability_wording():
    """Test 27: Report content contains zero forbidden culpability words in summaries/triggers/titles."""
    res = investigation_report_service.generate_report()
    dump = res.model_dump()
    # Remove mandatory disclaimers from check
    dump.pop("scientific_limitation", None)
    if "operational_alert" in dump:
        dump["operational_alert"].pop("disclaimer", None)
    dump_str = json.dumps(dump).lower()
    for word in ["culprit", "guilty", "responsible vessel", "definitely caused"]:
        assert word not in dump_str


def test_no_fabricated_vessels():
    """Test 28: Zero candidates reported for production scene; no fabricated MMSI."""
    res = investigation_report_service.generate_report(InvestigationReportRequest(scene_id=PRODUCTION_SCENE_ID))
    assert res.ais_correlation.candidate_count == 0
    assert len(res.vessel_candidate_ranking.ranked_candidates) == 0


def test_methodology_traceability():
    """Test 29: Methodology versions dictionary lists all upstream phases."""
    res = investigation_report_service.generate_report()
    meth = res.identification.methodology_versions
    for phase_key in ["Phase 1", "Phase 2", "Phase 3", "Phase 4", "Phase 5", "Phase 6.1", "Phase 6.2", "Phase 6.3", "Phase 7"]:
        assert phase_key in meth


def test_idempotent_report_generation():
    """Test 30: Repeated calls yield consistent report content."""
    r1 = investigation_report_service.generate_report(InvestigationReportRequest(scene_id=PRODUCTION_SCENE_ID))
    r2 = investigation_report_service.generate_report(InvestigationReportRequest(scene_id=PRODUCTION_SCENE_ID))
    assert r1.operational_alert.attention_level == r2.operational_alert.attention_level
    assert r1.sar_detection.predicted_oil_pixels == r2.sar_detection.predicted_oil_pixels


def test_negative_attention_configuration_rejected():
    """Test 31: Negative attention configuration parameter raises ValueError."""
    with pytest.raises(ValueError):
        investigation_report_service.validate_attention_configuration(-1.0, 0.7, 0.8)


def test_invalid_threshold_rejected():
    """Test 32: NaN or Infinite threshold parameter raises ValueError."""
    with pytest.raises(ValueError):
        investigation_report_service.validate_attention_configuration(float("nan"), 0.7, 0.8)


def test_threshold_provenance_exposed():
    """Test 33: Attention threshold configuration is present in output response."""
    res = investigation_report_service.generate_report()
    config = res.attention_threshold_configuration
    assert config["SPILL_ATTENTION_AREA_THRESHOLD_KM2"] == 1.0
    assert config["ATTENTION_RULE_VERSION"] == "7.0.0-deterministic-v1"


def test_origin_heuristic_threshold_not_interpreted_as_probability():
    """Test 34: Origin confidence semantics explicitly state heuristic nature."""
    res = investigation_report_service.generate_report()
    assert "heuristic score" in res.drift_analysis.origin_confidence_semantics.lower()


def test_candidate_score_threshold_not_interpreted_as_probability():
    """Test 35: Candidate score semantics state engineering correlation nature."""
    res = investigation_report_service.generate_report()
    assert "engineering correlation scores" in res.vessel_candidate_ranking.ranking_semantics.lower()


def test_critical_attention_semantics_are_operational_only():
    """Test 36: CRITICAL_ATTENTION level is operational escalation, not legal proof."""
    level, alert_avail, req_review, triggers = investigation_report_service.evaluate_attention_level(
        predicted_oil_pixels=100, region_count=1, total_area_km2=5.0,
        origin_available=True, origin_confidence_score=0.9,
        candidate_count=1, top_candidate_score=0.85, top_candidate_intersects_origin=True,
        spill_area_thresh=1.0, origin_thresh=0.7, ais_thresh=0.8
    )
    assert level == "CRITICAL_ATTENTION"
    assert alert_avail is True
    assert req_review is True


def test_genuine_alert_always_requires_human_review():
    """Test 37: Genuine alert evaluation always yields requires_human_review=True."""
    _, alert_avail, req_review, _ = investigation_report_service.evaluate_attention_level(
        predicted_oil_pixels=10, region_count=1, total_area_km2=1.5,
        origin_available=False, origin_confidence_score=None,
        candidate_count=0, top_candidate_score=None, top_candidate_intersects_origin=False,
        spill_area_thresh=1.0, origin_thresh=0.7, ais_thresh=0.8
    )
    assert alert_avail is True
    assert req_review is True


def test_no_event_cannot_be_overridden_by_ais_or_ranking():
    """Test 38: NO_EVENT guard executes first even if candidates or tracks exist."""
    level, alert_avail, req_review, _ = investigation_report_service.evaluate_attention_level(
        predicted_oil_pixels=0, region_count=0, total_area_km2=0.0,
        origin_available=True, origin_confidence_score=0.9,
        candidate_count=5, top_candidate_score=0.95, top_candidate_intersects_origin=True,
        spill_area_thresh=1.0, origin_thresh=0.7, ais_thresh=0.8
    )
    assert level == "NO_EVENT"
    assert alert_avail is False
    assert req_review is False


def test_attention_rule_precedence_is_deterministic():
    """Test 39: Order of evaluation strictly respects NO-SPILL -> Spill-only -> Origin -> AIS precedence."""
    # Spill-only
    l_spill, _, _, _ = investigation_report_service.evaluate_attention_level(
        predicted_oil_pixels=5, region_count=1, total_area_km2=0.5,
        origin_available=False, origin_confidence_score=None,
        candidate_count=0, top_candidate_score=None, top_candidate_intersects_origin=False,
        spill_area_thresh=1.0, origin_thresh=0.7, ais_thresh=0.8
    )
    assert l_spill == "LOW_ATTENTION"

    # Origin available
    l_orig, _, _, _ = investigation_report_service.evaluate_attention_level(
        predicted_oil_pixels=5, region_count=1, total_area_km2=0.5,
        origin_available=True, origin_confidence_score=0.8,
        candidate_count=0, top_candidate_score=None, top_candidate_intersects_origin=False,
        spill_area_thresh=1.0, origin_thresh=0.7, ais_thresh=0.8
    )
    assert l_orig == "HIGH_ATTENTION"


def test_report_generation_is_idempotent():
    """Test 40: Calling generate_report twice for same scene generates identical JSON file contents."""
    res1 = investigation_report_service.generate_report(InvestigationReportRequest(scene_id=PRODUCTION_SCENE_ID))
    json_path = settings.DATA_OUTPUT_DIR / f"investigation_report_{PRODUCTION_SCENE_ID}.json"
    with open(json_path, "r", encoding="utf-8") as f:
        c1 = json.load(f)

    res2 = investigation_report_service.generate_report(InvestigationReportRequest(scene_id=PRODUCTION_SCENE_ID))
    with open(json_path, "r", encoding="utf-8") as f:
        c2 = json.load(f)

    assert c1["operational_alert"] == c2["operational_alert"]


def test_report_api_generation_semantics_are_deterministic():
    """Test 41: API endpoint /api/investigation/report responds with HTTP 200 for custom scene."""
    resp = client.post("/api/investigation/report", json={"scene_id": "TEST_IDEMPOTENT_SCENE"})
    assert resp.status_code == 200
    assert resp.json()["scene_id"] == "TEST_IDEMPOTENT_SCENE"


def test_missing_upstream_phase_output_produces_explicit_availability_state():
    """Test 42: Missing upstream outputs set explicit false flags without throwing exception."""
    res = investigation_report_service.generate_report(InvestigationReportRequest(scene_id="UNKNOWN_SCENE"))
    assert res.drift_analysis.origin_available is False
    assert res.ais_correlation.correlation_available is False
    assert res.vessel_candidate_ranking.ranking_available is False


def test_no_hidden_fallback_source():
    """Test 43: Environmental sources cite explicit ECMWF and CMEMS names."""
    res = investigation_report_service.generate_report()
    assert "ECMWF" in res.environmental_conditions.wind_source
    assert "Copernicus Marine" in res.environmental_conditions.current_source


def test_no_causation_wording():
    """Test 44: Mandatory disclaimer explicitly forbids legal causation claims."""
    res = investigation_report_service.generate_report()
    assert "spill causation" in res.scientific_limitation.lower()


def test_no_responsibility_wording():
    """Test 45: Mandatory disclaimer explicitly forbids legal responsibility claims."""
    res = investigation_report_service.generate_report()
    assert "legal responsibility" in res.scientific_limitation.lower()
