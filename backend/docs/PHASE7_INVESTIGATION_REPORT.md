# OCEANTRACE AI — PHASE 7 AUTOMATED INVESTIGATION REPORT & OPERATIONAL ALERT ENGINE

## 1. Executive Summary & Objective

Phase 7 forms the final aggregation, orchestration, and reporting tier of OceanTrace AI. It synthesizes verified outputs from Phase 1 through Phase 6.3 into structured, machine-readable JSON investigation reports (`data/output/investigation_report_<scene_id>.json`), human-readable Markdown reports (`data/output/investigation_report_<scene_id>.md`), and a deterministic operational attention classification.

### Core Guiding Principles
1. **Decision Support Only**: Reports provide operational decision support for maritime domain awareness and oil spill response. They do **NOT** constitute legal attribution, proof of spill causation, or proof of vessel responsibility.
2. **Single Source of Truth**: Phase 7 reads immutable upstream outputs from Phases 1–6.3 without recomputing SAR detection, polygonization, drift modeling, or AIS candidate ranking.
3. **Deterministic Operational Attention**: Attention levels (`NO_EVENT`, `LOW_ATTENTION`, `MEDIUM_ATTENTION`, `HIGH_ATTENTION`, `CRITICAL_ATTENTION`) are evaluated using explicit, explainable engineering rules.
4. **Mandatory Human Review**: Every genuine alert (`alert_available = True`) automatically requires independent human review (`requires_human_review = True`).

---

## 2. Upstream Phase Inputs & Provenance

Phase 7 consumes canonical outputs from upstream phases:

| Phase | System Component | Primary Consumed Inputs | Source Layer |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Sentinel-1 Ingestion | Product ID, acquisition timestamp, platform, scene metadata | Real Satellite Acquisition |
| **Phase 2** | PyTorch U-Net | Detection status, predicted oil pixel count, predicted oil %, checkpoint ref | Model-Derived Detection |
| **Phase 3** | Spill Mapping | Spill region count, total area (km²), severity, GeoJSON reference | Model-Derived Geometry |
| **Phase 4** | NRT Environment | ECMWF wind U/V & speed, CMEMS ocean current U/V & speed, timestamps | Operational Model Fields |
| **Phase 5** | Drift Modelling | Forward/backward drift GeoJSON, probable origin centroid/area, release window | Model-Derived Drift |
| **Phase 6.1** | Live AIS Collector | Collector status, AIS source, persisted vessel observation availability | Real AIS Observations |
| **Phase 6.2** | AIS Correlation | Candidate count, spatial/temporal evidence, track intersection | Engineering Correlation |
| **Phase 6.3** | AIS Candidate Ranking | Ranked candidate list, engineering correlation score, weights, explanations | Engineering Ranking |

---

## 3. Configurable Operational Attention Thresholds & Semantics

All Phase 7 attention evaluation parameters are transparently defined in system configuration (`Settings`) and subject to strict numeric validation (rejecting negative, NaN, or infinite values):

- `SPILL_ATTENTION_AREA_THRESHOLD_KM2` (Default: `1.0` km²): Spill area threshold separating low and medium operational attention when origin is unavailable.
- `ORIGIN_HIGH_ATTENTION_THRESHOLD` (Default: `0.7` heuristic score): Origin score threshold escalating spill + origin events to high operational attention.
- `AIS_HIGH_CORRELATION_THRESHOLD` (Default: `0.8` engineering score): Candidate score threshold escalating candidate events to critical operational attention.
- `ATTENTION_RULE_VERSION` (Default: `"7.0.0-deterministic-v1"`): Version tag for rule traceability.

> **Threshold Semantics Statement**:
> *Phase 7 attention thresholds are configurable engineering rules used for operational escalation. They are not calibrated probabilities and do not establish spill causation or vessel responsibility.*

---

## 4. Deterministic Precedence Rule Engine & Operational Escalation

Attention levels are evaluated in strict order of precedence:

```
                          ┌───────────────────────────┐
                          │    Is Oil Detected?       │
                          │ (pixels > 0 & regions > 0)│
                          └─────────────┬─────────────┘
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
                      [ NO ]                         [ YES ]
                         │                             │
               ┌─────────┴─────────┐         ┌─────────┴─────────┐
               │     NO_EVENT      │         │ Is Origin Zone    │
               │ alert_available=F │         │    Available?     │
               │ human_review=F    │         └────┬─────────┬────┘
               └───────────────────┘              │         │
                                           [ NO ] │         │ [ YES ]
                                                  ▼         ▼
                                          LOW/MEDIUM       Is Candidate Score >= 0.8
                                          ATTENTION        or Track Intersecting?
                                          alert_avail=T     │               │
                                          human_rev=T[ NO ] │               │ [ YES ]
                                                            ▼               ▼
                                                     HIGH_ATTENTION  CRITICAL_ATTENTION
                                                     alert_avail=T   alert_avail=T
                                                     human_rev=T     human_rev=T
```

### Operational Attention Level Definitions
1. **`NO_EVENT`**: 0 predicted oil pixels or 0 spill regions. `alert_available = False`, `requires_human_review = False`.
2. **`LOW_ATTENTION`**: Oil spill detected but area < `1.0` km² and origin zone unavailable.
3. **`MEDIUM_ATTENTION`**: Oil spill detected with area $\ge$ `1.0` km² (no origin) OR origin zone available with heuristic score < `0.7`.
4. **`HIGH_ATTENTION`**: Oil spill detected with valid origin zone (score $\ge$ `0.7`) and candidate scores < `0.8`.
5. **`CRITICAL_ATTENTION`**: Operational escalation state indicating oil spill, valid origin zone, and a candidate vessel with track intersection or engineering score $\ge$ `0.8`. *Does NOT establish confirmed causation or legal responsibility.*

---

## 5. Structured Report Structure (Sections 1–8)

Each investigation report contains 8 structured sections:

1. **Section 1 — Incident Identification**: Report ID, scene ID, Sentinel product ID, acquisition timestamp, generation timestamp, system version, methodology versions, and source provenance.
2. **Section 2 — SAR Detection**: Oil detection status, predicted oil pixels/percentage, PyTorch U-Net checkpoint, preprocessing normalization, mask path.
3. **Section 3 — Spill Mapping**: Spill region count, total area (km² & m²), severity classification, GeoJSON reference, centroid & bounding box.
4. **Section 4 — Environmental Conditions**: ECMWF wind speed/direction/components, CMEMS ocean current speed/direction/components, timestamps, and temporal offsets.
5. **Section 5 — Drift Analysis**: Simulation settings, wind leeway & diffusion coefficients, backward/forward drift GeoJSON references, origin centroid/area, release window, and origin heuristic confidence score.
6. **Section 6 — AIS Correlation**: AIS source, collector status, correlation availability, observations considered, candidate count, spatial/temporal evidence.
7. **Section 7 — Vessel Candidate Ranking**: Ranking title, methodology version, configured/normalized weights, ordered candidate list with engineering correlation scores and explanations.
8. **Section 8 — Risk / Attention Classification & Alert Metadata**: Operational attention level, alert availability flag, human review flag, rule version, trigger evidence, and operational disclaimer.

---

## 6. API Usage & Idempotency

### `POST /api/investigation/report` (and `/api/v1/investigation/report`)
Generates or deterministically regenerates the investigation report JSON/MD for the requested scene.

**Request Body**:
```json
{
  "scene_id": "S1D_IW_GRDH_1SDV_20260918T010238_20260918T010309_004625_008A01_036E_COG"
}
```

### `GET /api/investigation/report/{scene_id}`
Retrieves existing persisted investigation report for `scene_id`.

### `GET /api/investigation/status`
Returns concise status response containing operational attention level, report availability, and alert metadata.

---

## 7. Mandatory Scientific Limitations Statement

> **OceanTrace AI produces model-derived decision-support information. Predicted spill regions, drift trajectories, probable origin zones, AIS correlations, candidate rankings, and operational attention levels require independent validation and do not independently establish spill causation, legal responsibility, or the identity of a responsible vessel.**
