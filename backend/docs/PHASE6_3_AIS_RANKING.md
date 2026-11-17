# OCEANTRACE AI — PHASE 6.3: EXPLAINABLE AIS CANDIDATE RANKING ENGINE

## 1. Primary Objective

Phase 6.3 implements a transparent, explainable engineering candidate ranking engine that consumes Phase 6.2 correlation evidence (`AISCorrelationResponse`) and orders potential source vessel candidates.

> [!IMPORTANT]
> **Mandatory Non-Causation & Non-Guilt Disclaimer**:
> Phase 6.3 produces an evidence-based engineering ranking of AIS candidates. The ranking is not a calibrated probability and does not independently establish spill causation, legal responsibility, or the identity of a responsible vessel. Output is titled strictly as **"POTENTIAL SOURCE VESSEL CANDIDATE RANKING"**.

---

## 2. Provenance & Input Source

- **Input Source**: Consumes Phase 6.2 output (`AISCorrelationResponse`) directly.
- **No Raw Data Re-querying**: Does not independently re-query the raw AIS database or external APIs during ranking execution.
- **Empty Scene Isolation**: When Phase 6.2 reports `candidate_count = 0` or `correlation_available = False` (e.g., current production scene with 0 oil pixels), Phase 6.3 returns immediately with `ranking_available = False`, `candidate_count = 0`, and `ranked_candidates = []`.

---

## 3. Strict Ranking Weight Validation & Normalization (Rules A – G)

The composite engineering correlation score ($S_{\text{candidate}} \in [0.0, 1.0]$) is computed via a transparent, bounded, linear combination of 4 normalized evidence dimensions:

$$S_{\text{candidate}} = w_{\text{spatial}} \cdot S_{\text{spatial}} + w_{\text{intersect}} \cdot S_{\text{intersect}} + w_{\text{temporal}} \cdot S_{\text{temporal}} + w_{\text{obs}} \cdot S_{\text{obs}}$$

### Configured vs. Normalized Weights
- **Rule A (Negative Weights Rejected)**: Any input weight $< 0.0$ is strictly rejected with `ValueError`.
- **Rule B (All-Zero Weights Rejected)**: Inputs where $\sum w_i \le 0.0$ are strictly rejected with `ValueError("Ranking weights must have a positive total.")`.
- **Rule C (Invalid Numeric Values Rejected)**: `NaN`, `Infinity`, `-Infinity`, and non-numeric types are rejected before calculation.
- **Rule D (Validation Before Normalization)**: All input weights undergo strict type and range checks before total calculation and normalization.
- **Rule E (Zero Individual Weight Allowed)**: An individual dimension weight may legitimately be `0.0` as long as the total $> 0$.
- **Rule F & G (Auditable Exposition & Precision)**: Double-precision floating point calculations are maintained. Both `configured_weights` and `normalized_weights` are exposed in the JSON response artifact.

### Default Configured Weights
- `AIS_RANKING_SPATIAL_WEIGHT` ($w_{\text{spatial}} = 0.40$)
- `AIS_RANKING_INTERSECTION_WEIGHT` ($w_{\text{intersect}} = 0.35$)
- `AIS_RANKING_TEMPORAL_WEIGHT` ($w_{\text{temporal}} = 0.15$)
- `AIS_RANKING_OBSERVATION_WEIGHT` ($w_{\text{obs}} = 0.10$)

### Feature Normalization
1. **Spatial Proximity**: $S_{\text{spatial}} = \max(0.0, 1.0 - d_{\text{min\_km}} / d_{\text{search\_km}})$
2. **Origin Intersection**: $S_{\text{intersect}} = 1.0$ if track line intersects origin polygon or $\ge 1$ point is inside, else $0.0$.
3. **Temporal Match**: $S_{\text{temporal}} = 1.0$ if temporal overlap is True, else $0.0$.
4. **Observation Density**: $S_{\text{obs}} = \min(1.0, N_{\text{obs}} / 10.0)$.

---

## 4. Deterministic Tie-Breaking Rules

If two candidates yield identical composite scores, ties are broken deterministically in order:
1. `position_count_inside_origin_zone` DESC
2. `minimum_distance_to_origin_km` ASC
3. `track_intersects_origin_zone` DESC (True before False)
4. `observation_count` DESC
5. `mmsi` ASC (lexical string ascending)

---

## 5. Output Schemas & API Endpoints

### API Endpoints
- `POST /api/ais/rank`
- `POST /api/v1/ais/rank`

### Response Structure (`AISRankingResponse`)
- `ranking_title`: `"POTENTIAL SOURCE VESSEL CANDIDATE RANKING"`
- `score_type`: `"engineering_correlation_score"`
- `configured_weights`: Raw input weights
- `normalized_weights`: Double-precision normalized weights
- `ranked_candidates`: List of `AISRankedCandidate` objects

---

## 6. Verification Scope and Limitations

> [!NOTE]
> Phase 6.3 engineering functionality is verified through deterministic automated regression tests. The current production scene contains no Phase 5 probable origin and therefore produces no ranked candidates. Real positive AIS ranking was not independently verified because no matching real AIS records were available for the historical release window.

---

## 7. Current Production Scene Result
- Product: `S1D_IW_GRDH_1SDV_20260918T010238_20260918T010309_004625_008A01_036E_COG`
- Phase 2: 0 oil pixels
- Phase 3: 0 spill regions
- Phase 5: `origin_available = False`
- Phase 6.2: `candidate_count = 0`
- Phase 6.3 Output:
```json
{
  "status": "success",
  "phase": 6.3,
  "scene_id": "S1D_IW_GRDH_1SDV_20260918T010238_20260918T010309_004625_008A01_036E_COG",
  "ranking_title": "POTENTIAL SOURCE VESSEL CANDIDATE RANKING",
  "ranking_available": false,
  "candidate_count": 0,
  "ranked_candidates": [],
  "reason": "No Phase 6.2 correlation candidates are available for this scene."
}
```
