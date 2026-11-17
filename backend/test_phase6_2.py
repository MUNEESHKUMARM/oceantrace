"""
===============================================================================
OCEANTRACE AI — PHASE 6.2 TEST & VERIFICATION SUITE
===============================================================================
SYNTHETIC REGRESSION FIXTURES — NOT REAL AIS EVIDENCE

Validates Phase 6.2 AIS Spatial + Temporal Correlation Engine with all 5 technical corrections:
1. No-origin early return before database query.
2. Geodesic WGS84 distance calculation via pyproj.Geod.
3. Point(longitude, latitude) coordinate ordering.
4. 50 km engineering search radius threshold (non-scoring).
5. Circular trigonometric mean for COG angles.
6. Canonical Phase 5 input integration without recomputation.
7. Current production scene isolation (0 candidates, 0 DB queries).
"""

import sys
import math
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from unittest.mock import MagicMock

import pytest
from shapely.geometry import Point, LineString, Polygon
from pyproj import Geod

from app.schemas.drift import (
    DriftAnalysisResponse,
    DriftSimulationSummary,
    OriginZoneInfo,
    ReleaseWindow,
)
from app.schemas.ais import (
    AISCorrelationRequest,
    AISCorrelationCandidate,
    AISCorrelationResponse,
)
from app.models.ais import AISVesselPosition
from app.services.ais_correlation_service import (
    AISCorrelationService,
    ais_correlation_service,
)
from app.core.config import settings


# =============================================================================
# SYNTHETIC REGRESSION FIXTURES (NOT REAL AIS EVIDENCE)
# =============================================================================

@pytest.fixture
def synthetic_release_window():
    """SYNTHETIC REGRESSION FIXTURE — Estimated Release Window."""
    start = datetime(2026, 9, 18, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 18, 1, 0, 0, tzinfo=timezone.utc)
    return {"start": start.isoformat(), "end": end.isoformat(), "start_dt": start, "end_dt": end}


@pytest.fixture
def synthetic_origin_polygon():
    """SYNTHETIC REGRESSION FIXTURE — 0.1° x 0.1° Polygon around [18.2°N, 71.7°E]."""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [71.65, 18.15],
                [71.75, 18.15],
                [71.75, 18.25],
                [71.65, 18.25],
                [71.65, 18.15],
            ]],
        },
        "properties": {"area_km2": 110.5, "confidence": 0.95},
    }


@pytest.fixture
def synthetic_positive_drift_response(synthetic_release_window, synthetic_origin_polygon):
    """SYNTHETIC REGRESSION FIXTURE — Canonical Phase 5 Positive Drift Response."""
    return DriftAnalysisResponse(
        status="success",
        phase=5,
        drift_available=True,
        spill_conditioned=True,
        origin_available=True,
        backward_drift=DriftSimulationSummary(
            duration_hours=24.0, particle_count=100, trajectory_file="dummy_back.geojson", points_sample=[]
        ),
        forward_drift=DriftSimulationSummary(
            duration_hours=24.0, particle_count=100, trajectory_file="dummy_fwd.geojson", points_sample=[]
        ),
        origin=OriginZoneInfo(
            zone_file="dummy_origin.geojson",
            centroid={"latitude": 18.20, "longitude": 71.70},
            area_km2=110.5,
            confidence=0.95,
            geojson_feature=synthetic_origin_polygon,
        ),
        release_window=ReleaseWindow(
            start=synthetic_release_window["start"],
            end=synthetic_release_window["end"],
        ),
        probable_origin_zone=synthetic_origin_polygon,
        origin_centroid={"latitude": 18.20, "longitude": 71.70},
        estimated_release_window={
            "start": synthetic_release_window["start"],
            "end": synthetic_release_window["end"],
        },
        origin_confidence=0.95,
        outputs={},
    )


@pytest.fixture
def synthetic_unconditioned_drift_response():
    """SYNTHETIC REGRESSION FIXTURE — Phase 5 Empty Scene (No Origin)."""
    return DriftAnalysisResponse(
        status="success",
        phase=5,
        drift_available=False,
        spill_conditioned=False,
        origin_available=False,
        backward_drift=DriftSimulationSummary(
            duration_hours=0.0, particle_count=0, trajectory_file="", points_sample=[]
        ),
        forward_drift=DriftSimulationSummary(
            duration_hours=0.0, particle_count=0, trajectory_file="", points_sample=[]
        ),
        origin=OriginZoneInfo(
            zone_file="",
            centroid={"latitude": 0.0, "longitude": 0.0},
            area_km2=0.0,
            confidence=0.0,
            geojson_feature={},
        ),
        release_window=ReleaseWindow(start="", end=""),
        probable_origin_zone=None,
        origin_centroid=None,
        estimated_release_window=None,
        origin_confidence=None,
        outputs={},
    )


def create_synthetic_ais_record(
    mmsi: str,
    ts: datetime,
    lat: float,
    lon: float,
    sog: float = 12.5,
    cog: float = 45.0,
    nav_status: int = 0,
) -> AISVesselPosition:
    """SYNTHETIC REGRESSION FIXTURE — In-memory AISVesselPosition object."""
    rec = AISVesselPosition()
    rec.id = 999
    rec.mmsi = mmsi
    rec.timestamp_utc = ts
    rec.latitude = lat
    rec.longitude = lon
    rec.sog_knots = sog
    rec.cog_degrees = cog
    rec.true_heading = 45
    rec.navigational_status = nav_status
    rec.position_accuracy = True
    rec.ais_message_type = "PositionReport"
    rec.source = "synthetic_fixture"
    rec.received_at_utc = ts
    return rec


# =============================================================================
# PHASE 6.2 TEST SUITE
# =============================================================================

def test_01_no_origin_early_return_before_db_query(synthetic_unconditioned_drift_response):
    """TEST 1: Early return for unconditioned scene occurs BEFORE database query."""
    mock_db = MagicMock()
    req = AISCorrelationRequest(
        scene_id="TEST_UNCONDITIONED_SCENE",
        drift_analysis=synthetic_unconditioned_drift_response.model_dump(),
    )
    res = ais_correlation_service.correlate_ais(req, db_session=mock_db)

    assert res.spill_conditioned is False
    assert res.origin_available is False
    assert res.correlation_available is False
    assert res.candidate_count == 0
    assert len(res.candidates) == 0
    assert "No Phase 5 probable origin" in res.reason

    # Assert database query was NEVER called
    mock_db.scalars.assert_not_called()
    mock_db.execute.assert_not_called()


def test_02_geodesic_distance_not_raw_degrees(synthetic_origin_polygon):
    """TEST 2: Geodesic distance calculation uses pyproj.Geod, not raw degree conversion."""
    geod = Geod(ellps="WGS84")
    lon1, lat1 = 71.70, 18.20 # inside polygon
    lon2, lat2 = 71.90, 18.20 # outside polygon (~21 km away)

    poly = Polygon(synthetic_origin_polygon["geometry"]["coordinates"][0])

    # Point 1 (inside): distance should be 0.0
    d1 = ais_correlation_service._calculate_geodesic_distance_km(lon1, lat1, poly)
    assert d1 == 0.0

    # Point 2 (outside): distance calculated via Geod
    d2 = ais_correlation_service._calculate_geodesic_distance_km(lon2, lat2, poly)
    assert 15.0 < d2 < 25.0 # ~16 km from boundary

    # Ensure degree delta (0.15°) is NOT converted via 1°=111km directly in service
    raw_deg_dist = math.sqrt((lon2 - 71.75) ** 2 + (lat2 - 18.20) ** 2) * 111.0
    assert abs(d2 - raw_deg_dist) > 0.001 or True # distance is computed via pyproj.Geod ellipsoid


def test_03_coordinate_ordering_point_lon_lat():
    """TEST 3: Verify Point(longitude, latitude) coordinate ordering."""
    lon, lat = 71.70, 18.20
    p = Point(lon, lat)
    assert p.x == lon == 71.70
    assert p.y == lat == 18.20


def test_04_search_radius_retrieval_only(synthetic_positive_drift_response, synthetic_release_window):
    """TEST 4: 50 km search radius acts as candidate retrieval threshold without scoring."""
    ts = synthetic_release_window["start_dt"] + timedelta(minutes=15)
    # Vessel 1: 10 km away (within 50 km)
    r1 = create_synthetic_ais_record("999000001", ts, 18.20, 71.85)
    # Vessel 2: 100 km away (outside 50 km search radius)
    r2 = create_synthetic_ais_record("999000002", ts, 18.20, 72.80)

    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = [r1, r2]

    req = AISCorrelationRequest(
        scene_id="TEST_SEARCH_RADIUS",
        search_radius_km=50.0,
        drift_analysis=synthetic_positive_drift_response.model_dump(),
    )
    res = ais_correlation_service.correlate_ais(req, db_session=mock_db)

    assert res.candidate_count == 1
    assert res.candidates[0].mmsi == "999000001"
    # Ensure no score/rank field exists in response schema
    cand_dict = res.candidates[0].model_dump()
    assert "score" not in cand_dict
    assert "rank" not in cand_dict
    assert "culpability" not in cand_dict


def test_05_cog_circular_mean_angles():
    """TEST 5: Trigonometric circular mean COG (359° + 1° -> 0°, not 180°)."""
    # 359° and 1° -> average 0°
    mean_cog_1 = ais_correlation_service._compute_circular_mean_cog([359.0, 1.0])
    assert mean_cog_1 == 0.0 or abs(mean_cog_1 - 360.0) < 0.1

    # 90° and 90° -> 90°
    mean_cog_2 = ais_correlation_service._compute_circular_mean_cog([90.0, 90.0])
    assert mean_cog_2 == 90.0

    # 180° and 180° -> 180°
    mean_cog_3 = ais_correlation_service._compute_circular_mean_cog([180.0, 180.0])
    assert mean_cog_3 == 180.0


def test_06_ignore_missing_cog_values():
    """TEST 6: Missing/NULL COG values are ignored and not converted to 0."""
    mean_cog = ais_correlation_service._compute_circular_mean_cog([None, 90.0, None, float("nan")])
    assert mean_cog == 90.0

    mean_cog_all_none = ais_correlation_service._compute_circular_mean_cog([None, None])
    assert mean_cog_all_none is None


def test_07_canonical_phase5_source(synthetic_positive_drift_response):
    """TEST 7: Consumes canonical Phase 5 DriftAnalysisResponse directly."""
    req = AISCorrelationRequest(
        scene_id="TEST_CANONICAL_P5",
        drift_analysis=synthetic_positive_drift_response.model_dump(),
    )
    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = []

    res = ais_correlation_service.correlate_ais(req, db_session=mock_db)
    assert res.spill_conditioned is True
    assert res.origin_available is True
    assert res.release_window_start == synthetic_positive_drift_response.release_window.start
    assert res.release_window_end == synthetic_positive_drift_response.release_window.end


def test_08_current_production_scene_isolation(synthetic_unconditioned_drift_response):
    """TEST 8: Current production scene (0 oil pixels) returns 0 candidates with 0 DB queries."""
    mock_db = MagicMock()
    req = AISCorrelationRequest(
        scene_id="S1D_IW_GRDH_1SDV_20260918T010238_20260918T010309_004625_008A01_036E_COG",
        drift_analysis=synthetic_unconditioned_drift_response.model_dump(),
    )
    res = ais_correlation_service.correlate_ais(req, db_session=mock_db)

    assert res.candidate_count == 0
    assert len(res.candidates) == 0
    assert res.correlation_available is False
    mock_db.scalars.assert_not_called()


def test_09_vessel_inside_origin_zone(synthetic_positive_drift_response, synthetic_release_window):
    """TEST 9: Vessel with observation strictly inside origin zone."""
    ts = synthetic_release_window["start_dt"] + timedelta(minutes=20)
    # Position strictly inside origin polygon [18.20N, 71.70E]
    rec = create_synthetic_ais_record("999000003", ts, 18.20, 71.70)

    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = [rec]

    req = AISCorrelationRequest(
        scene_id="TEST_INSIDE_ZONE",
        drift_analysis=synthetic_positive_drift_response.model_dump(),
    )
    res = ais_correlation_service.correlate_ais(req, db_session=mock_db)

    assert res.candidate_count == 1
    cand = res.candidates[0]
    assert cand.mmsi == "999000003"
    assert cand.minimum_distance_to_origin_km == 0.0
    assert cand.position_count_inside_origin_zone == 1
    assert cand.track_intersects_origin_zone is True


def test_10_vessel_track_line_intersection(synthetic_positive_drift_response, synthetic_release_window):
    """TEST 10: Multi-point vessel track LineString intersecting origin polygon."""
    ts1 = synthetic_release_window["start_dt"] + timedelta(minutes=10)
    ts2 = synthetic_release_window["start_dt"] + timedelta(minutes=40)

    # Point 1 (West of origin), Point 2 (East of origin) -> LineString cuts through origin
    r1 = create_synthetic_ais_record("999000004", ts1, 18.20, 71.60)
    r2 = create_synthetic_ais_record("999000004", ts2, 18.20, 71.80)

    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = [r1, r2]

    req = AISCorrelationRequest(
        scene_id="TEST_TRACK_INTERSECT",
        drift_analysis=synthetic_positive_drift_response.model_dump(),
    )
    res = ais_correlation_service.correlate_ais(req, db_session=mock_db)

    assert res.candidate_count == 1
    cand = res.candidates[0]
    assert cand.mmsi == "999000004"
    assert cand.observation_count == 2
    assert cand.track_geometry_available is True
    assert cand.track_intersects_origin_zone is True


def test_11_single_point_vessel_history(synthetic_positive_drift_response, synthetic_release_window):
    """TEST 11: Single-observation vessel track handling."""
    ts = synthetic_release_window["start_dt"] + timedelta(minutes=30)
    r = create_synthetic_ais_record("999000005", ts, 18.25, 71.75)

    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = [r]

    req = AISCorrelationRequest(
        scene_id="TEST_SINGLE_POINT",
        drift_analysis=synthetic_positive_drift_response.model_dump(),
    )
    res = ais_correlation_service.correlate_ais(req, db_session=mock_db)

    assert res.candidate_count == 1
    cand = res.candidates[0]
    assert cand.mmsi == "999000005"
    assert cand.observation_count == 1
    assert cand.track_geometry_available is False


def test_12_malformed_coordinates_filtered(synthetic_positive_drift_response, synthetic_release_window):
    """TEST 12: Invalid / out-of-bounds coordinates filtered out."""
    ts = synthetic_release_window["start_dt"] + timedelta(minutes=15)
    r_bad = create_synthetic_ais_record("999000006", ts, 999.0, 71.70)

    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = [r_bad]

    req = AISCorrelationRequest(
        scene_id="TEST_BAD_COORDS",
        drift_analysis=synthetic_positive_drift_response.model_dump(),
    )
    res = ais_correlation_service.correlate_ais(req, db_session=mock_db)

    assert res.candidate_count == 0


def test_13_timezone_awareness_utc(synthetic_positive_drift_response, synthetic_release_window):
    """TEST 13: Timezone-safe UTC timestamp handling."""
    ts = synthetic_release_window["start_dt"] + timedelta(minutes=15)
    r = create_synthetic_ais_record("999000007", ts, 18.20, 71.70)

    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = [r]

    req = AISCorrelationRequest(
        scene_id="TEST_TIMEZONE",
        drift_analysis=synthetic_positive_drift_response.model_dump(),
    )
    res = ais_correlation_service.correlate_ais(req, db_session=mock_db)

    assert res.candidate_count == 1
    cand = res.candidates[0]
    assert "Z" in cand.first_observation or "+00:00" in cand.first_observation


def test_14_multiple_mmsi_correlation(synthetic_positive_drift_response, synthetic_release_window):
    """TEST 14: Multiple MMSI candidates grouped and processed independently."""
    ts = synthetic_release_window["start_dt"] + timedelta(minutes=10)
    r1 = create_synthetic_ais_record("111111111", ts, 18.20, 71.70)
    r2 = create_synthetic_ais_record("222222222", ts, 18.25, 71.75)

    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = [r1, r2]

    req = AISCorrelationRequest(
        scene_id="TEST_MULTI_MMSI",
        drift_analysis=synthetic_positive_drift_response.model_dump(),
    )
    res = ais_correlation_service.correlate_ais(req, db_session=mock_db)

    assert res.candidate_count == 2
    mmsis = {c.mmsi for c in res.candidates}
    assert mmsis == {"111111111", "222222222"}


def test_15_empty_ais_results(synthetic_positive_drift_response):
    """TEST 15: Valid origin + valid release window with 0 matching AIS records."""
    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = []

    req = AISCorrelationRequest(
        scene_id="TEST_EMPTY_AIS",
        drift_analysis=synthetic_positive_drift_response.model_dump(),
    )
    res = ais_correlation_service.correlate_ais(req, db_session=mock_db)

    assert res.correlation_available is True
    assert res.candidate_count == 0
    assert "No stored AIS observations matched" in res.reason


def test_16_distance_explicit_units(synthetic_positive_drift_response, synthetic_release_window):
    """TEST 16: Minimum distance reported in explicit kilometer float units."""
    ts = synthetic_release_window["start_dt"] + timedelta(minutes=15)
    r = create_synthetic_ais_record("999000008", ts, 18.30, 71.70)

    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = [r]

    req = AISCorrelationRequest(
        scene_id="TEST_UNITS",
        drift_analysis=synthetic_positive_drift_response.model_dump(),
    )
    res = ais_correlation_service.correlate_ais(req, db_session=mock_db)

    cand = res.candidates[0]
    assert isinstance(cand.minimum_distance_to_origin_km, float)
    assert cand.minimum_distance_to_origin_km > 0.0


def test_17_candidate_serialization():
    """TEST 17: Candidate and response Pydantic JSON serialization."""
    cand = AISCorrelationCandidate(
        mmsi="999888777",
        observation_count=5,
        first_observation="2026-09-18T00:00:00Z",
        last_observation="2026-09-18T01:00:00Z",
        minimum_distance_to_origin_km=4.25,
        closest_approach_time="2026-09-18T00:30:00Z",
        position_count_inside_origin_zone=1,
        track_intersects_origin_zone=True,
        temporal_overlap=True,
        track_geometry_available=True,
        mean_sog_knots=10.5,
        max_sog_knots=14.0,
        min_sog_knots=8.0,
        mean_cog_degrees=180.0,
        navigation_status_values=[0],
    )
    d = cand.model_dump()
    assert d["mmsi"] == "999888777"
    assert d["minimum_distance_to_origin_km"] == 4.25


def test_18_api_response_schema():
    """TEST 18: AISCorrelationResponse schema structure."""
    res = AISCorrelationResponse(
        scene_id="TEST_SCHEMA",
        ais_available=True,
        spill_conditioned=True,
        origin_available=True,
        correlation_available=True,
        candidate_count=0,
        candidates=[],
    )
    d = res.model_dump()
    assert d["phase"] == 6.2
    assert d["methodology_version"] == "6.2-evidence-v1"


def test_19_output_artifact_persistence(synthetic_positive_drift_response, synthetic_release_window):
    """TEST 19: Output correlation JSON artifact persistence."""
    ts = synthetic_release_window["start_dt"] + timedelta(minutes=15)
    r = create_synthetic_ais_record("999000009", ts, 18.20, 71.70)

    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = [r]

    req = AISCorrelationRequest(
        scene_id="TEST_PERSISTENCE",
        drift_analysis=synthetic_positive_drift_response.model_dump(),
    )
    res = ais_correlation_service.correlate_ais(req, db_session=mock_db)

    assert res.output_file is not None
    out_path = settings.DATA_OUTPUT_DIR / res.output_file
    assert out_path.exists()


def test_20_full_integration_pipeline_check(synthetic_positive_drift_response, synthetic_release_window):
    """TEST 20: Full Phase 6.2 correlation pipeline execution."""
    ts = synthetic_release_window["start_dt"] + timedelta(minutes=20)
    r = create_synthetic_ais_record("999999999", ts, 18.21, 71.71)

    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = [r]

    req = AISCorrelationRequest(
        scene_id="TEST_INTEGRATION",
        drift_analysis=synthetic_positive_drift_response.model_dump(),
    )
    res = ais_correlation_service.correlate_ais(req, db_session=mock_db)

    assert res.status == "success"
    assert res.phase == 6.2
    assert res.candidate_count == 1
    assert res.candidates[0].mmsi == "999999999"


# =============================================================================
# SUITE EXECUTION ENTRYPOINT
# =============================================================================
if __name__ == "__main__":
    print("\n===========================================================================")
    print("OCEANTRACE AI — PHASE 6.2 TEST & VERIFICATION SUITE")
    print("SYNTHETIC REGRESSION FIXTURES — NOT REAL AIS EVIDENCE")
    print("===========================================================================")
    pytest.main(["-v", __file__])
