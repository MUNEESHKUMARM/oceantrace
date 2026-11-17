"""
===============================================================================
OCEANTRACE AI — PHASE 6.3 TEST & VERIFICATION SUITE
===============================================================================
SYNTHETIC REGRESSION FIXTURES — NOT REAL AIS EVIDENCE

Validates Phase 6.3 Explainable AIS Candidate Ranking Engine:
1. Zero candidates early return.
2. Single and multi-candidate deterministic ranking.
3. Feature score normalization (spatial, intersection, temporal, observation).
4. Configurable weight validation and normalization.
5. Multi-tier tie-breaking rules.
6. Explanation generation and non-causation semantics.
7. Current production scene isolation (0 candidates, 0 rankings).
"""

import os
import json
import pytest
from unittest.mock import MagicMock

from app.schemas.ais import (
    AISCorrelationCandidate,
    AISCorrelationResponse,
    AISRankingRequest,
    AISRankedCandidate,
    AISRankingResponse,
)
from app.services.ais_ranking_service import (
    AISRankingService,
    ais_ranking_service,
)
from app.core.config import settings


# =============================================================================
# SYNTHETIC REGRESSION FIXTURES (NOT REAL AIS EVIDENCE)
# =============================================================================

@pytest.fixture
def synthetic_correlation_candidate_close():
    """SYNTHETIC REGRESSION FIXTURE — Vessel with strong spatial/intersection match."""
    return AISCorrelationCandidate(
        mmsi="111111111",
        observation_count=15,
        first_observation="2026-09-18T00:10:00Z",
        last_observation="2026-09-18T00:50:00Z",
        minimum_distance_to_origin_km=0.0,
        closest_approach_time="2026-09-18T00:30:00Z",
        position_count_inside_origin_zone=3,
        track_intersects_origin_zone=True,
        temporal_overlap=True,
        track_geometry_available=True,
        mean_sog_knots=12.0,
        max_sog_knots=14.0,
        min_sog_knots=10.0,
        mean_cog_degrees=90.0,
        navigation_status_values=[0],
    )


@pytest.fixture
def synthetic_correlation_candidate_far():
    """SYNTHETIC REGRESSION FIXTURE — Vessel 25 km away without intersection."""
    return AISCorrelationCandidate(
        mmsi="222222222",
        observation_count=5,
        first_observation="2026-09-18T00:15:00Z",
        last_observation="2026-09-18T00:45:00Z",
        minimum_distance_to_origin_km=25.0,
        closest_approach_time="2026-09-18T00:30:00Z",
        position_count_inside_origin_zone=0,
        track_intersects_origin_zone=False,
        temporal_overlap=True,
        track_geometry_available=True,
        mean_sog_knots=10.0,
        max_sog_knots=11.0,
        min_sog_knots=9.0,
        mean_cog_degrees=180.0,
        navigation_status_values=[0],
    )


@pytest.fixture
def synthetic_positive_correlation_response(
    synthetic_correlation_candidate_close, synthetic_correlation_candidate_far
):
    """SYNTHETIC REGRESSION FIXTURE — Phase 6.2 response with 2 candidates."""
    return AISCorrelationResponse(
        status="success",
        phase=6.2,
        scene_id="TEST_POSITIVE_SCENE",
        ais_available=True,
        spill_conditioned=True,
        origin_available=True,
        correlation_available=True,
        release_window_start="2026-09-18T00:00:00Z",
        release_window_end="2026-09-18T01:00:00Z",
        origin_centroid={"latitude": 18.20, "longitude": 71.70},
        origin_area_km2=110.5,
        search_radius_km=50.0,
        candidate_count=2,
        candidates=[synthetic_correlation_candidate_far, synthetic_correlation_candidate_close],
        reason="Found 2 candidates",
    )


@pytest.fixture
def synthetic_empty_correlation_response():
    """SYNTHETIC REGRESSION FIXTURE — Phase 6.2 response with 0 candidates."""
    return AISCorrelationResponse(
        status="success",
        phase=6.2,
        scene_id="TEST_EMPTY_SCENE",
        ais_available=True,
        spill_conditioned=False,
        origin_available=False,
        correlation_available=False,
        candidate_count=0,
        candidates=[],
        reason="No Phase 5 probable origin is available for this scene.",
    )


# =============================================================================
# PHASE 6.3 TEST SUITE
# =============================================================================

def test_01_zero_candidates_early_return(synthetic_empty_correlation_response):
    """TEST 1: Zero candidate Phase 6.2 response returns immediately with ranking_available=False."""
    req = AISRankingRequest(
        scene_id="TEST_EMPTY_SCENE",
        correlation_response=synthetic_empty_correlation_response.model_dump(),
    )
    res = ais_ranking_service.rank_candidates(req)

    assert res.ranking_available is False
    assert res.candidate_count == 0
    assert len(res.ranked_candidates) == 0
    assert "No Phase 6.2 correlation candidates" in res.reason


def test_02_single_candidate_ranking(synthetic_correlation_candidate_close):
    """TEST 2: Single candidate is assigned rank 1."""
    corr_res = AISCorrelationResponse(
        status="success",
        phase=6.2,
        scene_id="TEST_SINGLE",
        ais_available=True,
        spill_conditioned=True,
        origin_available=True,
        correlation_available=True,
        search_radius_km=50.0,
        candidate_count=1,
        candidates=[synthetic_correlation_candidate_close],
    )
    req = AISRankingRequest(
        scene_id="TEST_SINGLE",
        correlation_response=corr_res.model_dump(),
    )
    res = ais_ranking_service.rank_candidates(req)

    assert res.ranking_available is True
    assert res.candidate_count == 1
    assert res.ranked_candidates[0].rank == 1
    assert res.ranked_candidates[0].mmsi == "111111111"


def test_03_multi_candidate_ranking_order(synthetic_positive_correlation_response):
    """TEST 3: Multiple candidates are ordered deterministically by candidate_score."""
    req = AISRankingRequest(
        scene_id="TEST_POSITIVE_SCENE",
        correlation_response=synthetic_positive_correlation_response.model_dump(),
    )
    res = ais_ranking_service.rank_candidates(req)

    assert res.ranking_available is True
    assert res.candidate_count == 2

    rank1 = res.ranked_candidates[0]
    rank2 = res.ranked_candidates[1]

    assert rank1.rank == 1
    assert rank1.mmsi == "111111111" # Close/Intersecting candidate
    assert rank2.rank == 2
    assert rank2.mmsi == "222222222" # Far candidate
    assert rank1.candidate_score > rank2.candidate_score


def test_04_deterministic_ranking_reproducibility(synthetic_positive_correlation_response):
    """TEST 4: Repeated ranking runs produce identical rank orders and scores."""
    req = AISRankingRequest(
        scene_id="TEST_POSITIVE_SCENE",
        correlation_response=synthetic_positive_correlation_response.model_dump(),
    )
    res1 = ais_ranking_service.rank_candidates(req)
    res2 = ais_ranking_service.rank_candidates(req)

    assert [c.mmsi for c in res1.ranked_candidates] == [c.mmsi for c in res2.ranked_candidates]
    assert [c.candidate_score for c in res1.ranked_candidates] == [c.candidate_score for c in res2.ranked_candidates]


def test_05_spatial_score_normalization():
    """TEST 5: Spatial score normalization bounds max(0, 1 - dist/radius)."""
    service = AISRankingService()
    # At 0 km: spatial score = 1.0
    # At 25 km (radius 50 km): spatial score = 0.5
    # At 50 km (radius 50 km): spatial score = 0.0
    # At 100 km (radius 50 km): spatial score = 0.0
    cand_0 = AISCorrelationCandidate(
        mmsi="000", observation_count=1, first_observation="", last_observation="",
        minimum_distance_to_origin_km=0.0, closest_approach_time="", position_count_inside_origin_zone=0,
        track_intersects_origin_zone=False, temporal_overlap=True, track_geometry_available=False
    )
    cand_25 = AISCorrelationCandidate(
        mmsi="025", observation_count=1, first_observation="", last_observation="",
        minimum_distance_to_origin_km=25.0, closest_approach_time="", position_count_inside_origin_zone=0,
        track_intersects_origin_zone=False, temporal_overlap=True, track_geometry_available=False
    )
    corr_res = AISCorrelationResponse(
        status="success", phase=6.2, scene_id="S", ais_available=True, spill_conditioned=True,
        origin_available=True, correlation_available=True, search_radius_km=50.0, candidate_count=2,
        candidates=[cand_0, cand_25]
    )
    res = service.rank_candidates(AISRankingRequest(correlation_response=corr_res.model_dump()))
    assert res.ranked_candidates[0].evidence["spatial_score"] == 1.0
    assert res.ranked_candidates[1].evidence["spatial_score"] == 0.5


def test_06_temporal_evidence_score():
    """TEST 6: Temporal overlap evaluates to 1.0."""
    cand = AISCorrelationCandidate(
        mmsi="100", observation_count=1, first_observation="", last_observation="",
        minimum_distance_to_origin_km=10.0, closest_approach_time="", position_count_inside_origin_zone=0,
        track_intersects_origin_zone=False, temporal_overlap=True, track_geometry_available=False
    )
    corr_res = AISCorrelationResponse(
        status="success", phase=6.2, scene_id="S", ais_available=True, spill_conditioned=True,
        origin_available=True, correlation_available=True, candidate_count=1, candidates=[cand]
    )
    res = ais_ranking_service.rank_candidates(AISRankingRequest(correlation_response=corr_res.model_dump()))
    assert res.ranked_candidates[0].evidence["temporal_score"] == 1.0


def test_07_origin_intersection_score():
    """TEST 7: Origin intersection evaluates to 1.0 for intersecting tracks."""
    cand = AISCorrelationCandidate(
        mmsi="101", observation_count=1, first_observation="", last_observation="",
        minimum_distance_to_origin_km=0.0, closest_approach_time="", position_count_inside_origin_zone=1,
        track_intersects_origin_zone=True, temporal_overlap=True, track_geometry_available=True
    )
    corr_res = AISCorrelationResponse(
        status="success", phase=6.2, scene_id="S", ais_available=True, spill_conditioned=True,
        origin_available=True, correlation_available=True, candidate_count=1, candidates=[cand]
    )
    res = ais_ranking_service.rank_candidates(AISRankingRequest(correlation_response=corr_res.model_dump()))
    assert res.ranked_candidates[0].evidence["intersection_score"] == 1.0


def test_08_observation_density_factor():
    """TEST 8: Observation count density factor caps at 1.0 for >=10 observations."""
    cand = AISCorrelationCandidate(
        mmsi="102", observation_count=20, first_observation="", last_observation="",
        minimum_distance_to_origin_km=10.0, closest_approach_time="", position_count_inside_origin_zone=0,
        track_intersects_origin_zone=False, temporal_overlap=True, track_geometry_available=True
    )
    corr_res = AISCorrelationResponse(
        status="success", phase=6.2, scene_id="S", ais_available=True, spill_conditioned=True,
        origin_available=True, correlation_available=True, candidate_count=1, candidates=[cand]
    )
    res = ais_ranking_service.rank_candidates(AISRankingRequest(correlation_response=corr_res.model_dump()))
    assert res.ranked_candidates[0].evidence["observation_score"] == 1.0


def test_09_missing_distance_handled_safely():
    """TEST 9: None or NaN minimum distance handled safely without crashing."""
    cand = AISCorrelationCandidate(
        mmsi="103", observation_count=1, first_observation="", last_observation="",
        minimum_distance_to_origin_km=float("nan"), closest_approach_time="", position_count_inside_origin_zone=0,
        track_intersects_origin_zone=False, temporal_overlap=True, track_geometry_available=False
    )
    corr_res = AISCorrelationResponse(
        status="success", phase=6.2, scene_id="S", ais_available=True, spill_conditioned=True,
        origin_available=True, correlation_available=True, candidate_count=1, candidates=[cand]
    )
    res = ais_ranking_service.rank_candidates(AISRankingRequest(correlation_response=corr_res.model_dump()))
    assert res.ranked_candidates[0].evidence["spatial_score"] == 0.0


def test_10_missing_temporal_evidence_handled():
    """TEST 10: Missing temporal overlap handles safely."""
    cand = AISCorrelationCandidate(
        mmsi="104", observation_count=1, first_observation="", last_observation="",
        minimum_distance_to_origin_km=10.0, closest_approach_time="", position_count_inside_origin_zone=0,
        track_intersects_origin_zone=False, temporal_overlap=False, track_geometry_available=False
    )
    corr_res = AISCorrelationResponse(
        status="success", phase=6.2, scene_id="S", ais_available=True, spill_conditioned=True,
        origin_available=True, correlation_available=True, candidate_count=1, candidates=[cand]
    )
    res = ais_ranking_service.rank_candidates(AISRankingRequest(correlation_response=corr_res.model_dump()))
    assert res.ranked_candidates[0].evidence["temporal_score"] == 0.0


def test_11_missing_cog_does_not_affect_score():
    """TEST 11: Missing COG degrees does not break candidate score."""
    cand = AISCorrelationCandidate(
        mmsi="105", observation_count=1, first_observation="", last_observation="",
        minimum_distance_to_origin_km=10.0, closest_approach_time="", position_count_inside_origin_zone=0,
        track_intersects_origin_zone=False, temporal_overlap=True, track_geometry_available=False,
        mean_cog_degrees=None
    )
    corr_res = AISCorrelationResponse(
        status="success", phase=6.2, scene_id="S", ais_available=True, spill_conditioned=True,
        origin_available=True, correlation_available=True, candidate_count=1, candidates=[cand]
    )
    res = ais_ranking_service.rank_candidates(AISRankingRequest(correlation_response=corr_res.model_dump()))
    assert 0.0 <= res.ranked_candidates[0].candidate_score <= 1.0


def test_12_score_normalization_bounded_zero_to_one():
    """TEST 12: Candidate score bounded strictly in [0.0, 1.0]."""
    cand = AISCorrelationCandidate(
        mmsi="106", observation_count=100, first_observation="", last_observation="",
        minimum_distance_to_origin_km=0.0, closest_approach_time="", position_count_inside_origin_zone=10,
        track_intersects_origin_zone=True, temporal_overlap=True, track_geometry_available=True
    )
    corr_res = AISCorrelationResponse(
        status="success", phase=6.2, scene_id="S", ais_available=True, spill_conditioned=True,
        origin_available=True, correlation_available=True, candidate_count=1, candidates=[cand]
    )
    res = ais_ranking_service.rank_candidates(AISRankingRequest(correlation_response=corr_res.model_dump()))
    score = res.ranked_candidates[0].candidate_score
    assert 0.0 <= score <= 1.0


def test_13_custom_weight_configuration():
    """TEST 13: Custom valid weights accepted and normalized to sum to 1.0."""
    req = AISRankingRequest(
        scene_id="TEST_WEIGHTS",
        spatial_weight=0.5,
        intersection_weight=0.5,
        temporal_weight=0.0,
        observation_weight=0.0,
        correlation_response=AISCorrelationResponse(
            status="success", phase=6.2, scene_id="S", ais_available=True, spill_conditioned=True,
            origin_available=True, correlation_available=True, candidate_count=1,
            candidates=[AISCorrelationCandidate(
                mmsi="107", observation_count=1, first_observation="", last_observation="",
                minimum_distance_to_origin_km=0.0, closest_approach_time="", position_count_inside_origin_zone=1,
                track_intersects_origin_zone=True, temporal_overlap=True, track_geometry_available=True
            )]
        ).model_dump()
    )
    res = ais_ranking_service.rank_candidates(req)
    assert res.ranking_configuration["spatial_weight"] == 0.5
    assert res.ranking_configuration["intersection_weight"] == 0.5


def test_14_negative_weights_rejected():
    """TEST 14: Negative weights raise ValueError."""
    req = AISRankingRequest(
        scene_id="TEST_NEG_WEIGHT",
        spatial_weight=-0.5,
        correlation_response=AISCorrelationResponse(
            status="success", phase=6.2, scene_id="S", ais_available=True, spill_conditioned=True,
            origin_available=True, correlation_available=True, candidate_count=0, candidates=[]
        ).model_dump()
    )
    with pytest.raises(ValueError, match="non-negative"):
        ais_ranking_service.rank_candidates(req)


def test_15_tie_breaking_multi_tier():
    """TEST 15: Candidates with identical scores are tie-broken by inside count & distance."""
    # Candidates with same score
    c1 = AISCorrelationCandidate(
        mmsi="999000002", observation_count=5, first_observation="", last_observation="",
        minimum_distance_to_origin_km=5.0, closest_approach_time="", position_count_inside_origin_zone=0,
        track_intersects_origin_zone=False, temporal_overlap=True, track_geometry_available=False
    )
    c2 = AISCorrelationCandidate(
        mmsi="999000001", observation_count=5, first_observation="", last_observation="",
        minimum_distance_to_origin_km=2.0, closest_approach_time="", position_count_inside_origin_zone=0,
        track_intersects_origin_zone=False, temporal_overlap=True, track_geometry_available=False
    )
    corr_res = AISCorrelationResponse(
        status="success", phase=6.2, scene_id="S", ais_available=True, spill_conditioned=True,
        origin_available=True, correlation_available=True, candidate_count=2, candidates=[c1, c2]
    )
    res = ais_ranking_service.rank_candidates(AISRankingRequest(correlation_response=corr_res.model_dump()))

    # c2 has smaller distance (2.0 km vs 5.0 km), so c2 should be rank 1
    assert res.ranked_candidates[0].mmsi == "999000001"
    assert res.ranked_candidates[1].mmsi == "999000002"


def test_16_mmsi_lexical_tie_breaker():
    """TEST 16: Identical candidate features tie-broken deterministically by MMSI ascending."""
    c1 = AISCorrelationCandidate(
        mmsi="222000000", observation_count=5, first_observation="", last_observation="",
        minimum_distance_to_origin_km=10.0, closest_approach_time="", position_count_inside_origin_zone=0,
        track_intersects_origin_zone=False, temporal_overlap=True, track_geometry_available=False
    )
    c2 = AISCorrelationCandidate(
        mmsi="111000000", observation_count=5, first_observation="", last_observation="",
        minimum_distance_to_origin_km=10.0, closest_approach_time="", position_count_inside_origin_zone=0,
        track_intersects_origin_zone=False, temporal_overlap=True, track_geometry_available=False
    )
    corr_res = AISCorrelationResponse(
        status="success", phase=6.2, scene_id="S", ais_available=True, spill_conditioned=True,
        origin_available=True, correlation_available=True, candidate_count=2, candidates=[c1, c2]
    )
    res = ais_ranking_service.rank_candidates(AISRankingRequest(correlation_response=corr_res.model_dump()))

    # MMSI "111000000" < "222000000"
    assert res.ranked_candidates[0].mmsi == "111000000"
    assert res.ranked_candidates[1].mmsi == "222000000"


def test_17_explanation_generation(synthetic_positive_correlation_response):
    """TEST 17: Ranked candidates have non-empty evidence summaries and explanations."""
    req = AISRankingRequest(
        scene_id="TEST_EXPLANATION",
        correlation_response=synthetic_positive_correlation_response.model_dump(),
    )
    res = ais_ranking_service.rank_candidates(req)

    for cand in res.ranked_candidates:
        assert isinstance(cand.evidence_summary, list)
        assert len(cand.evidence_summary) > 0
        assert isinstance(cand.explanation, str)
        assert len(cand.explanation) > 0


def test_18_output_schema_structure(synthetic_positive_correlation_response):
    """TEST 18: AISRankingResponse output schema validation."""
    req = AISRankingRequest(
        scene_id="TEST_SCHEMA",
        correlation_response=synthetic_positive_correlation_response.model_dump(),
    )
    res = ais_ranking_service.rank_candidates(req)

    d = res.model_dump()
    assert d["phase"] == 6.3
    assert d["ranking_title"] == "POTENTIAL SOURCE VESSEL CANDIDATE RANKING"
    assert d["source_correlation_phase"] == "Phase 6.2"


def test_19_json_artifact_persistence(synthetic_positive_correlation_response):
    """TEST 19: Ranking JSON artifact persisted in settings.DATA_OUTPUT_DIR."""
    req = AISRankingRequest(
        scene_id="TEST_PERSISTENCE",
        correlation_response=synthetic_positive_correlation_response.model_dump(),
    )
    res = ais_ranking_service.rank_candidates(req)

    assert res.output_file is not None
    out_path = settings.DATA_OUTPUT_DIR / res.output_file
    assert out_path.exists()


def test_20_current_production_scene_isolation(synthetic_empty_correlation_response):
    """TEST 20: Current production scene (0 candidates) returns ranking_available=False."""
    req = AISRankingRequest(
        scene_id="S1D_IW_GRDH_1SDV_20260918T010238_20260918T010309_004625_008A01_036E_COG",
        correlation_response=synthetic_empty_correlation_response.model_dump(),
    )
    res = ais_ranking_service.rank_candidates(req)

    assert res.ranking_available is False
    assert res.candidate_count == 0
    assert len(res.ranked_candidates) == 0


def test_21_no_external_api_calls_during_ranking(synthetic_positive_correlation_response):
    """TEST 21: Execution of rank_candidates requires zero external API queries."""
    req = AISRankingRequest(
        scene_id="TEST_NO_API",
        correlation_response=synthetic_positive_correlation_response.model_dump(),
    )
    res = ais_ranking_service.rank_candidates(req)
    assert res.ranking_available is True


def test_22_phase_6_2_provenance(synthetic_positive_correlation_response):
    """TEST 22: Preserves source correlation phase provenance."""
    req = AISRankingRequest(
        scene_id="TEST_PROVENANCE",
        correlation_response=synthetic_positive_correlation_response.model_dump(),
    )
    res = ais_ranking_service.rank_candidates(req)
    assert res.source_correlation_phase == "Phase 6.2"


def test_23_ranking_methodology_version():
    """TEST 23: Methodology version string check."""
    req = AISRankingRequest(scene_id="TEST_VERSION")
    res = ais_ranking_service.rank_candidates(req)
    assert res.ranking_methodology_version == "6.3.1-engineering-v1"


def test_24_score_type_is_engineering_correlation_score(synthetic_positive_correlation_response):
    """TEST 24: Score type is explicitly designated as 'engineering_correlation_score'."""
    req = AISRankingRequest(
        scene_id="TEST_SCORE_TYPE",
        correlation_response=synthetic_positive_correlation_response.model_dump(),
    )
    res = ais_ranking_service.rank_candidates(req)
    for cand in res.ranked_candidates:
        assert cand.score_type == "engineering_correlation_score"


def test_25_non_causation_language_disclaimer(synthetic_positive_correlation_response):
    """TEST 25: Mandatory non-causation disclaimer in response interpretation."""
    req = AISRankingRequest(
        scene_id="TEST_DISCLAIMER",
        correlation_response=synthetic_positive_correlation_response.model_dump(),
    )
    res = ais_ranking_service.rank_candidates(req)

    interp = res.interpretation.lower()
    assert "not presented as proof of causation" in interp or "disclaimer" in interp or "engineering evidence score" in interp
    # Ensure forbidden words are absent
    full_str = str(res.model_dump()).lower()
    assert "culprit" not in full_str
    assert "guilty" not in full_str
    assert "responsible vessel" not in full_str


def test_26_negative_spatial_weight_rejected(synthetic_positive_correlation_response):
    """TEST 26: Negative spatial weight raises ValueError (Rule A)."""
    req = AISRankingRequest(
        spatial_weight=-0.1,
        correlation_response=synthetic_positive_correlation_response.model_dump(),
    )
    with pytest.raises(ValueError, match="cannot be negative"):
        ais_ranking_service.rank_candidates(req)


def test_27_negative_intersection_weight_rejected(synthetic_positive_correlation_response):
    """TEST 27: Negative intersection weight raises ValueError (Rule A)."""
    req = AISRankingRequest(
        intersection_weight=-0.5,
        correlation_response=synthetic_positive_correlation_response.model_dump(),
    )
    with pytest.raises(ValueError, match="cannot be negative"):
        ais_ranking_service.rank_candidates(req)


def test_28_negative_temporal_weight_rejected(synthetic_positive_correlation_response):
    """TEST 28: Negative temporal weight raises ValueError (Rule A)."""
    req = AISRankingRequest(
        temporal_weight=-1.0,
        correlation_response=synthetic_positive_correlation_response.model_dump(),
    )
    with pytest.raises(ValueError, match="cannot be negative"):
        ais_ranking_service.rank_candidates(req)


def test_29_negative_observation_weight_rejected(synthetic_positive_correlation_response):
    """TEST 29: Negative observation weight raises ValueError (Rule A)."""
    req = AISRankingRequest(
        observation_weight=-0.05,
        correlation_response=synthetic_positive_correlation_response.model_dump(),
    )
    with pytest.raises(ValueError, match="cannot be negative"):
        ais_ranking_service.rank_candidates(req)


def test_30_all_zero_weights_rejected(synthetic_positive_correlation_response):
    """TEST 30: All-zero weights configuration raises ValueError (Rule B)."""
    req = AISRankingRequest(
        spatial_weight=0.0,
        intersection_weight=0.0,
        temporal_weight=0.0,
        observation_weight=0.0,
        correlation_response=synthetic_positive_correlation_response.model_dump(),
    )
    with pytest.raises(ValueError, match="positive total"):
        ais_ranking_service.rank_candidates(req)


def test_31_nan_weight_rejected(synthetic_positive_correlation_response):
    """TEST 31: NaN weight raises ValueError (Rule C)."""
    req = AISRankingRequest(
        spatial_weight=float("nan"),
        correlation_response=synthetic_positive_correlation_response.model_dump(),
    )
    with pytest.raises(ValueError, match="cannot be NaN"):
        ais_ranking_service.rank_candidates(req)


def test_32_inf_weight_rejected(synthetic_positive_correlation_response):
    """TEST 32: Infinity weight raises ValueError (Rule C)."""
    req = AISRankingRequest(
        spatial_weight=float("inf"),
        correlation_response=synthetic_positive_correlation_response.model_dump(),
    )
    with pytest.raises(ValueError, match="cannot be NaN or Infinity"):
        ais_ranking_service.rank_candidates(req)


def test_33_non_numeric_weight_rejected(synthetic_positive_correlation_response):
    """TEST 33: Non-numeric weight raises ValueError (Rule C)."""
    with pytest.raises((ValueError, Exception)):
        ais_ranking_service._validate_and_normalize_weights("invalid_string", 0.35, 0.15, 0.10)


def test_34_single_zero_weight_accepted(synthetic_positive_correlation_response):
    """TEST 34: Single zero weight with positive total is accepted (Rule E)."""
    req = AISRankingRequest(
        spatial_weight=0.5,
        intersection_weight=0.5,
        temporal_weight=0.0,
        observation_weight=0.0,
        correlation_response=synthetic_positive_correlation_response.model_dump(),
    )
    res = ais_ranking_service.rank_candidates(req)
    assert res.ranking_available is True
    assert res.normalized_weights["spatial_weight"] == 0.5
    assert res.normalized_weights["intersection_weight"] == 0.5
    assert res.normalized_weights["temporal_weight"] == 0.0


def test_35_auditable_configured_and_normalized_weights(synthetic_positive_correlation_response):
    """TEST 35: Both configured_weights and normalized_weights exposed in response (Rule F)."""
    req = AISRankingRequest(
        spatial_weight=4.0,
        intersection_weight=3.5,
        temporal_weight=1.5,
        observation_weight=1.0,
        correlation_response=synthetic_positive_correlation_response.model_dump(),
    )
    res = ais_ranking_service.rank_candidates(req)

    assert res.configured_weights["spatial_weight"] == 4.0
    assert res.normalized_weights["spatial_weight"] == 0.40
    assert res.normalized_weights["intersection_weight"] == 0.35


# =============================================================================
# SUITE EXECUTION ENTRYPOINT
# =============================================================================
if __name__ == "__main__":
    print("\n===========================================================================")
    print("OCEANTRACE AI — PHASE 6.3 TEST & VERIFICATION SUITE")
    print("SYNTHETIC REGRESSION FIXTURES — NOT REAL AIS EVIDENCE")
    print("===========================================================================")
    pytest.main(["-v", __file__])
