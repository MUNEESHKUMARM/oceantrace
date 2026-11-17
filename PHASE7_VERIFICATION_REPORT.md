# OCEANTRACE AI — PHASE 7 VERIFICATION REPORT
## Automated Investigation Report + Risk / Attention Alert Engine

---

## A. Files Created
1. `backend/app/schemas/investigation.py` — Pydantic v2 schemas for Sections 1–8, OperationalAlert, and API request/response.
2. `backend/app/services/investigation_report_service.py` — Phase 7 service orchestrating upstream phase aggregation, report generation, and deterministic operational attention evaluation.
3. `backend/app/api/investigation.py` — FastAPI router exposing `POST /api/investigation/report`, `GET /api/investigation/report/{scene_id}`, and `GET /api/investigation/status`.
4. `backend/test_phase7.py` — Phase 7 test suite containing 45 unit, integration, schema validation, and rule precedence tests.
5. `backend/docs/PHASE7_INVESTIGATION_REPORT.md` — Detailed technical specification documentation for Phase 7.
6. `PHASE7_VERIFICATION_REPORT.md` — Final verification report (this document).
7. `data/output/investigation_report_S1D_IW_GRDH_1SDV_20260918T010238_20260918T010309_004625_008A01_036E_COG.json` — Persisted JSON report artifact.
8. `data/output/investigation_report_S1D_IW_GRDH_1SDV_20260918T010238_20260918T010309_004625_008A01_036E_COG.md` — Persisted Markdown report artifact.

---

## B. Files Modified
1. `backend/app/core/config.py` — Added configurable operational attention parameters (`SPILL_ATTENTION_AREA_THRESHOLD_KM2`, `ORIGIN_HIGH_ATTENTION_THRESHOLD`, `AIS_HIGH_CORRELATION_THRESHOLD`, `ATTENTION_RULE_VERSION`).
2. `backend/app/main.py` — Registered `investigation.router` under `/api` and `/api/v1`.

---

## C. Files Unchanged
- `app/services/sentinel1_service.py` (Phase 1)
- `app/services/oil_detection_service.py` (Phase 2)
- `app/services/spill_mapping_service.py` (Phase 3)
- `app/services/environment_service.py` (Phase 4)
- `app/services/drift_modelling_service.py` (Phase 5)
- `app/services/ais_stream_service.py` (Phase 6.1)
- `app/services/ais_correlation_service.py` (Phase 6.2)
- `app/services/ais_ranking_service.py` (Phase 6.3)
- PyTorch U-Net architecture & checkpoint weights (0 modifications)
- MySQL database schema & connection logic (0 modifications)

---

## D. Report Schema & Sections
Reports structure canonical outputs into 8 dedicated sections:
- **Section 1**: Incident Identification (Report ID, Scene ID, Product ID, Acquisition Time, System Version, Methodology Versions, Provenance).
- **Section 2**: SAR Detection (PyTorch U-Net status, oil pixels, oil %, checkpoint ref, normalization).
- **Section 3**: Spill Mapping (Region count, total area km²/m², severity, GeoJSON reference, centroid/bbox).
- **Section 4**: Environmental Conditions (ECMWF wind & CMEMS current components, speed, direction, source, timestamps, offsets).
- **Section 5**: Drift Analysis (Lagrangian simulation parameters, backward/forward GeoJSON references, origin centroid/area, release window, heuristic confidence score).
- **Section 6**: AIS Correlation (Collector status, observations considered, candidate count, spatial/temporal evidence).
- **Section 7**: Vessel Candidate Ranking (Ranking title, methodology version, configured/normalized weights, candidate list with engineering scores & explanations).
- **Section 8**: Risk / Attention Classification & Operational Alert Metadata.

---

## E. Upstream Phase Provenance
- `Sentinel-1 SAR`: Real Copernicus STAC Satellite Acquisition
- `ECMWF Wind`: Operational Model Field (ERA5 Reanalysis)
- `CMEMS Current`: Operational Numerical Model Field
- `PyTorch U-Net`: Model-Derived Oil Pixel Detection
- `Spill Mapping`: Model-Derived Polygon Geometry
- `Drift Simulation`: Model-Derived Lagrangian Trajectories
- `AIS Data`: Real AIS Vessel Position Observations
- `AIS Ranking`: Engineering Correlation Score Order
- `Investigation Report`: Operational Decision-Support Aggregation

---

## F. Configurable Attention-Level Methodology & Thresholds
Actual Configured Parameters (`Settings`):
- `SPILL_ATTENTION_AREA_THRESHOLD_KM2` = `1.0` km²
- `ORIGIN_HIGH_ATTENTION_THRESHOLD` = `0.7` (heuristic score)
- `AIS_HIGH_CORRELATION_THRESHOLD` = `0.8` (engineering score)
- `ATTENTION_RULE_VERSION` = `"7.0.0-deterministic-v1"`

### Deterministic Rule Precedence Order:
1. **Rule 1 (NO-SPILL Guard Rule)**: If `predicted_oil_pixels == 0` or `region_count == 0` $\rightarrow$ `NO_EVENT` (`alert_available = False`, `requires_human_review = False`).
2. **Rule 2 (Spill-Only)**: If origin unavailable $\rightarrow$ `LOW_ATTENTION` (area < 1.0 km²) or `MEDIUM_ATTENTION` (area $\ge$ 1.0 km²).
3. **Rule 3 (Origin Evidence)**: If origin zone available $\rightarrow$ `MEDIUM_ATTENTION` (score < 0.7) or `HIGH_ATTENTION` (score $\ge$ 0.7).
4. **Rule 4 (AIS Correlation & Ranking)**: If candidate vessels exist $\rightarrow$ `CRITICAL_ATTENTION` (top candidate score $\ge$ 0.8 or track intersects origin) or `HIGH_ATTENTION` (score < 0.8).

---

## G. Operational Alert & Human Review Methodology
- Schema-enforced compliance: If `alert_available == True`, `requires_human_review` MUST be `True`.
- For `NO_EVENT`: `alert_available = False`, `requires_human_review = False`.

---

## H. Current Production Scene Verification
**Scene ID**: `S1D_IW_GRDH_1SDV_20260918T010238_20260918T010309_004625_008A01_036E_COG`

**Measured Runtime Results**:
```json
{
  "attention_level": "NO_EVENT",
  "alert_available": false,
  "requires_human_review": false,
  "predicted_oil_pixels": 0,
  "region_count": 0,
  "origin_available": false,
  "candidate_count": 0,
  "ranking_available": false
}
```
*Interpretation Statement*: No predicted oil spill was identified for this scene; therefore no spill-origin-based vessel attribution or alert was generated.

---

## I. Test Results
- Phase 7 Test Suite (`python -m pytest test_phase7.py -q`): **45 passed in 4.87s** (100% success).

---

## J. Full Regression Result
- Complete Pipeline Regression (`python -m pytest test_phase1.py test_phase2.py test_phase3.py test_phase4.py test_phase5.py test_phase6_1.py test_phase6_2.py test_phase6_3.py test_phase7.py -q`): **106 passed in 102.17s** (100% success across all 7 phases).

---

## K. Frontend Build Verification
- `npm run build`: **SUCCESS** (Compiled in 9.3s with Next.js Turbopack; 0 TypeScript errors).

---

## L. Backend Startup Verification
- FastAPI Backend loaded cleanly with `uvicorn app.main:app`. Routers `/api` and `/api/v1` registered for all endpoints including `/investigation/report` and `/investigation/status`.

---

## M. Generated Report Artifacts
- JSON Report: `data/output/investigation_report_S1D_IW_GRDH_1SDV_20260918T010238_20260918T010309_004625_008A01_036E_COG.json`
- Markdown Report: `data/output/investigation_report_S1D_IW_GRDH_1SDV_20260918T010238_20260918T010309_004625_008A01_036E_COG.md`

---

## N. Synthetic Positive Test Status
- Tested and verified via synthetic regression fixtures in `test_phase7.py` (labeled strictly as `SYNTHETIC REGRESSION FIXTURE — NOT REAL INCIDENT EVIDENCE`). No synthetic records were inserted into the production database.

---

## O. Real Positive Incident Status
- The current verified production scene contains 0 predicted oil pixels; thus, `NO_EVENT` was generated cleanly. End-to-end positive real-world reporting will execute automatically when a scene with detected oil pixels is ingested.

---

## P. Mandatory Scientific Limitations Statement
> **OceanTrace AI produces model-derived decision-support information. Predicted spill regions, drift trajectories, probable origin zones, AIS correlations, candidate rankings, and operational attention levels require independent validation and do not independently establish spill causation, legal responsibility, or the identity of a responsible vessel.**

---

## Q. Final Acceptance Criteria Checklist
- [x] Phase 7 only aggregates existing upstream outputs
- [x] No upstream phase is modified
- [x] No U-Net changes or retraining
- [x] Report is 100% deterministic and auditable
- [x] Provenance is preserved for every section
- [x] All timestamps are UTC-consistent
- [x] Model outputs are clearly distinguished from observations
- [x] No-spill scenes generate NO_EVENT and alert_available = False
- [x] Missing origin prevents vessel attribution
- [x] Missing AIS does not imply no vessels existed
- [x] Ranking is not re-created or overridden
- [x] Causation is never claimed
- [x] Responsibility is never claimed
- [x] Human review is required for genuine alerts
- [x] Synthetic fixtures are clearly labeled
- [x] No fake production data
- [x] JSON artifact generated
- [x] Markdown artifact generated
- [x] API works (`POST /api/investigation/report` & `GET /api/investigation/status`)
- [x] All 45 Phase 7 tests pass
- [x] Full regression (106 tests) passes
- [x] Frontend build succeeds
- [x] Backend starts cleanly
- [x] Technical documentation generated (`backend/docs/PHASE7_INVESTIGATION_REPORT.md`)
