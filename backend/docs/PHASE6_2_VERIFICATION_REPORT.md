# OCEANTRACE AI — PHASE 6.2 VERIFICATION REPORT

## A. Files Created
1. `backend/app/services/ais_correlation_service.py` — Phase 6.2 AIS Correlation Engine service.
2. `backend/docs/PHASE6_2_AIS_CORRELATION.md` — Phase 6.2 architectural and mathematical documentation.
3. `backend/test_phase6_2.py` — 20 synthetic unit and integration test suite.
4. `backend/docs/PHASE6_2_VERIFICATION_REPORT.md` — This verification report.

---

## B. Files Modified
1. `backend/app/core/config.py` — Added `AIS_CORRELATION_SEARCH_RADIUS_KM = 50.0`.
2. `backend/app/schemas/ais.py` — Added `AISCorrelationCandidate`, `AISCorrelationRequest`, `AISCorrelationResponse`.
3. `backend/app/api/ais.py` — Registered `POST /correlate` API endpoint.

---

## C. Files Unchanged
- U-Net architecture & weights (`app/models/segmentation_unet.py`) — UNTOUCHED.
- Phase 1 pre-processing (`app/services/sar_preprocessing.py`, `sentinel1_service.py`) — UNTOUCHED.
- Phase 2 oil detection (`app/services/oil_detection_service.py`) — UNTOUCHED.
- Phase 3 spill mapping (`app/services/spill_mapping_service.py`) — UNTOUCHED.
- Phase 4 NRT environmental service (`app/services/environment_service.py`) — UNTOUCHED.
- Phase 5 Lagrangian drift simulator (`app/services/drift_modelling_service.py`) — UNTOUCHED.
- Phase 6.1 live AISStream ingestion (`app/services/ais_stream_service.py`) — UNTOUCHED.
- Frontend Next.js components & UI layouts — UNTOUCHED.

---

## D. Database Changes
- Reused existing MySQL 8.0 / SQLite table `ais_vessel_positions` created in Phase 6.1.
- No schema migrations or DB structure changes required.

---

## E. API Endpoints
- `POST /api/ais/correlate` (and `/api/v1/ais/correlate`)
  - Request Body: `{"scene_id": "...", "search_radius_km": 50.0}`
  - Response: `AISCorrelationResponse` (contains `candidate_count`, `candidates`, `spill_conditioned`, `origin_available`, `reason`, `output_file`).

---

## F. Phase 5 Integration Result
- Successfully consumes canonical Phase 5 `DriftAnalysisResponse` without recomputing probable origin geometries or release windows.
- Verified that Phase 5 release window `start` and `end` timestamps dictate the SQL query range.

---

## G. AIS Records Queried
- Current empty production scene: 0 records queried (early exit triggered before DB query).
- Synthetic positive test suite: Query executed over `timestamp_utc >= release_start AND timestamp_utc <= release_end`.

---

## H. AIS Records Used
- 0 records used for empty production scene.
- Valid records filtered for coordinate validity ($-90 \le \text{lat} \le 90$, $-180 \le \text{lon} \le 180$) and assigned to candidate vessel tracks.

---

## I. Number of MMSIs Evaluated
- Current production scene: 0 MMSIs evaluated.
- Synthetic regression suite: Multi-MMSI evaluation verified cleanly.

---

## J. Candidate Count
- Current production scene: `candidate_count = 0` (`candidates = []`).
- Synthetic positive regression test: `candidate_count = 1` (MMSI `999999999`).

---

## K. Spatial Correlation Result
- Minimum spatial distances calculated via `pyproj.Geod(ellps="WGS84")` in explicit kilometers (`minimum_distance_to_origin_km`).
- Track intersection tested via Shapely `LineString` intersection with Phase 5 origin polygon.
- Points inside origin polygon accurately counted (`position_count_inside_origin_zone`).

---

## L. Temporal Correlation Result
- Release window parsed into UTC timezone-aware datetimes.
- Temporal overlap verified for candidate observations.

---

## M. Historical AIS Availability
- Live AISStream collector persists real-time 2026 data.
- Historical release windows without stored AIS data return `correlation_available = True` with `candidate_count = 0` and reason: `"No stored AIS observations matched the release window"`.

---

## N. Current Production Scene Result
- Product: `S1D_IW_GRDH_1SDV_20260918T010238_20260918T010309_004625_008A01_036E_COG`
- Phase 2: 0 oil pixels
- Phase 3: 0 spill regions
- Phase 5: `spill_conditioned = False`, `origin_available = False`
- Phase 6.2 Output:
```json
{
  "status": "success",
  "phase": 6.2,
  "scene_id": "S1D_IW_GRDH_1SDV_20260918T010238_20260918T010309_004625_008A01_036E_COG",
  "ais_available": true,
  "spill_conditioned": false,
  "origin_available": false,
  "correlation_available": false,
  "candidate_count": 0,
  "candidates": [],
  "reason": "No Phase 5 probable origin is available for this scene."
}
```

---

## O. Test Results
- `test_phase6_2.py`: `20/20 PASSED` (1.21s)
- `test_phase2.py`: `PASSED`
- `test_phase4.py`: `PASSED`
- `test_phase5.py`: `PASSED`
- `test_phase6_1.py`: `PASSED`

---

## P. Frontend Build Result
- `npm run build`: `SUCCESS` (Compiled in 14.2s, 0 TypeScript / Next.js errors).

---

## Q. Limitations
- Phase 6.2 relies strictly on stored AIS positions in the local database. It does not perform live AISStream web queries during correlation execution.
- If no AIS observations are present in the local database for historical release windows, no candidate vessels will be retrieved.

---

## R. Scientific Interpretation
"Phase 6.2 identifies AIS vessels whose observed positions and tracks show spatial and/or temporal correlation with the Phase 5-derived probable origin zone during the estimated release window. Phase 6.2 produces AIS correlation evidence only. It does not establish spill causation, legal responsibility, or the identity of a responsible vessel."
