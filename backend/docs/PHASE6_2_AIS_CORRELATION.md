# OCEANTRACE AI — PHASE 6.2: REAL AIS ↔ PROBABLE ORIGIN CORRELATION ENGINE

## 1. Primary Objective

Phase 6.2 implements spatial and temporal correlation between Phase 5 estimated probable origin zones and stored Phase 6.1 real AIS vessel tracks (`ais_vessel_positions` table).

> [!IMPORTANT]
> **No-Ranking & No-Causation Rule**:
> Phase 6.2 produces AIS correlation evidence only. It does not establish spill causation, legal responsibility, or the identity of a responsible vessel. Candidate ranking and scoring belong strictly to Phase 6.3.

---

## 2. Canonical Phase 5 Source of Truth

"Phase 6.2 consumes the canonical persisted Phase 5 scene result as its single source of truth. It does not recompute or override Phase 5 outputs."

The correlation engine extracts:
- `spill_conditioned`
- `origin_available`
- `probable_origin_zone` (GeoJSON Feature)
- `origin_centroid` (`latitude`, `longitude`)
- `estimated_release_window` (`start`, `end` ISO UTC timestamps)
- `origin_confidence`

If `spill_conditioned` or `origin_available` is `False` (such as for unconditioned scenes or scenes with 0 detected oil pixels), Phase 6.2 returns immediately with `candidate_count = 0` **before** performing any SQL database queries on `ais_vessel_positions`.

---

## 3. Geodesic WGS84 Spatial Distance Methodology

"Minimum spatial distances are calculated using a metric/geodesic-safe method and reported in kilometers. Geographic degree differences are never interpreted directly as linear distance."

- Source AIS coordinates and Phase 5 geometry are maintained in WGS84 (`EPSG:4326`).
- Shapely point geometries use `Point(longitude, latitude)`.
- Minimum distances are calculated using `pyproj.Geod(ellps="WGS84")`.
- If an observation or track lies inside or intersects the origin polygon, `minimum_distance_to_origin_km = 0.0`.
- Otherwise, the distance from `Point(longitude, latitude)` to the nearest point on the origin polygon boundary is calculated via `geod.inv()`.

---

## 4. Engineering Search Radius Threshold

"50 km is an engineering candidate retrieval/search radius used to limit the AIS observations considered for correlation. It is not a scientific attribution threshold and does not imply vessel relevance."

- Configured via `AIS_CORRELATION_SEARCH_RADIUS_KM` (default `50.0` km).
- Used solely for candidate prefiltering.
- It is never converted into probabilities, scores, ranks, or confidence metrics.

---

## 5. Course Over Ground (COG) Circular Mean Math

Course Over Ground is circular angular data in $[0^\circ, 360^\circ)$. Averages are computed using trigonometric vector components:

$$\text{mean\_angle} = \text{atan2}\left(\frac{1}{N}\sum \sin(\theta), \frac{1}{N}\sum \cos(\theta)\right) \pmod{360^\circ}$$

- $359^\circ$ and $1^\circ$ yield $0^\circ$ (not $180^\circ$).
- Missing / NULL / non-finite COG values are ignored and never replaced with 0.

---

## 6. Output Schemas & API Endpoints

### API Endpoints
- `POST /api/ais/correlate`
- `POST /api/v1/ais/correlate`

### Candidate Evidence Structure (`AISCorrelationCandidate`)
- `mmsi`: Vessel identifier string
- `observation_count`: Total valid observations in window
- `first_observation`, `last_observation`: UTC ISO timestamps
- `minimum_distance_to_origin_km`: Geodesic distance in km
- `closest_approach_time`: Timestamp of closest approach
- `position_count_inside_origin_zone`: Integer count inside origin polygon
- `track_intersects_origin_zone`: Boolean
- `temporal_overlap`: Boolean
- `track_geometry_available`: Boolean ($\ge 2$ points)
- `mean_sog_knots`, `max_sog_knots`, `min_sog_knots`: SOG metrics
- `mean_cog_degrees`: Trigonometric circular mean COG
- `navigation_status_values`: List of observed status codes

---

## 7. Historical AIS Limitation

Live AISStream Phase 6.1 ingests real-time events. For historical release windows where no stored AIS observations exist in the local database, Phase 6.2 returns `correlation_available = True` (or `False` if DB unavailable) with `candidate_count = 0` and an explicit reason string: `"No stored AIS observations matched the release window"`. Live AIS data is never fabricated to match historical scenes.
