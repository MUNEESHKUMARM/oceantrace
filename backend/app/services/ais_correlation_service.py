import os
import json
import math
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

import shapely.geometry
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import nearest_points
from pyproj import Geod
from sqlalchemy import select, and_

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.ais import AISVesselPosition
from app.schemas.drift import DriftAnalysisResponse
from app.schemas.ais import (
    AISCorrelationRequest,
    AISCorrelationCandidate,
    AISCorrelationResponse,
)
from app.services.drift_modelling_service import drift_modelling_service

logger = logging.getLogger("oceantrace.ais_correlation_service")


class AISCorrelationService:
    """
    Phase 6.2 AIS Spatial + Temporal Correlation Engine.

    Correlates stored Phase 6.1 AIS vessel observations with Phase 5 probable origin zones
    and estimated release windows.

    Strict Behavioral & Mathematical Rules:
    1. Single Canonical Phase 5 Source: Consumes DriftAnalysisResponse strictly.
    2. No-Origin Early Return: Immediately exits with 0 candidates BEFORE performing
       database queries when origin_available or spill_conditioned is False.
    3. Geodesic Distance: Calculates minimum spatial distances using pyproj.Geod(ellps="WGS84")
       in explicit kilometers. Geographic degree differences are NEVER converted directly to km.
       Shapely coordinates use Point(longitude, latitude).
    4. Search Radius Semantics: AIS_CORRELATION_SEARCH_RADIUS_KM (50.0 km) is strictly an
       engineering candidate-retrieval threshold and is never converted to a score/rank.
    5. COG Circular Mean: Course Over Ground averages use atan2(mean(sin), mean(cos)) in [0, 360).
       Missing/NULL COG values are ignored and never replaced with 0.
    6. Unordered Evidence Only: Returns raw spatial and temporal evidence without scores,
       rankings, or culpability claims.
    """

    def __init__(self, search_radius_km: Optional[float] = None):
        self.search_radius_km = (
            search_radius_km
            if search_radius_km is not None
            else settings.AIS_CORRELATION_SEARCH_RADIUS_KM
        )
        self.geod = Geod(ellps="WGS84")

    def _compute_circular_mean_cog(self, cog_list: List[Optional[float]]) -> Optional[float]:
        """
        Calculates trigonometric circular mean Course Over Ground in degrees [0, 360).
        Ignores None and non-finite values. Returns None if no valid COG values exist.
        """
        valid_cogs = [c for c in cog_list if c is not None and math.isfinite(c) and 0.0 <= c <= 360.0]
        if not valid_cogs:
            return None
        
        sin_sum = sum(math.sin(math.radians(c)) for c in valid_cogs)
        cos_sum = sum(math.cos(math.radians(c)) for c in valid_cogs)

        if abs(sin_sum) < 1e-9 and abs(cos_sum) < 1e-9:
            return None

        mean_rad = math.atan2(sin_sum, cos_sum)
        mean_deg = math.degrees(mean_rad) % 360.0
        return round(mean_deg, 2)

    def _calculate_geodesic_distance_km(
        self,
        point_lon: float,
        point_lat: float,
        origin_shape: shapely.geometry.base.BaseGeometry,
    ) -> float:
        """
        Calculates the minimum geodesic distance in kilometers between a Point(lon, lat)
        and an origin geometry using WGS84 ellipsoid geometry.
        Returns 0.0 km if the point lies inside or intersects the origin geometry.
        """
        p_shape = Point(point_lon, point_lat)

        if origin_shape.contains(p_shape) or origin_shape.intersects(p_shape):
            return 0.0

        try:
            nearest_geom = nearest_points(p_shape, origin_shape)[1]
            nearest_lon, nearest_lat = nearest_geom.x, nearest_geom.y
            _, _, dist_m = self.geod.inv(point_lon, point_lat, nearest_lon, nearest_lat)
            return round(max(0.0, dist_m / 1000.0), 3)
        except Exception as e:
            logger.warning(f"Geodesic distance calculation fallback for point ({point_lon}, {point_lat}): {e}")
            return 0.0

    def correlate_ais(
        self,
        request: AISCorrelationRequest,
        db_session=None,
    ) -> AISCorrelationResponse:
        """
        Executes Phase 6.2 AIS Correlation Engine.
        """
        search_radius = request.search_radius_km or self.search_radius_km
        scene_id = request.scene_id or "CURRENT_SCENE"

        # ---------------------------------------------------------------------
        # 1. RESOLVE CANONICAL PHASE 5 RESULT
        # ---------------------------------------------------------------------
        drift_res: Optional[DriftAnalysisResponse] = None

        if request.drift_analysis:
            try:
                drift_res = DriftAnalysisResponse.model_validate(request.drift_analysis)
            except Exception as e:
                logger.error(f"Failed to parse provided drift_analysis dict: {e}")
                drift_res = None

        if drift_res is None:
            # Fallback to calling canonical Phase 5 drift modelling service for scene
            logger.info("Resolving canonical Phase 5 drift simulation result...")
            try:
                from app.schemas.drift import DriftAnalysisRequest
                from app.services.sentinel1_service import sentinel1_service
                from app.services.environment_service import environment_service
                
                acq_time = "2026-09-18T01:02:38Z" # default baseline acquisition
                metadata = sentinel1_service.get_latest_acquisition()
                if metadata and "acquisition_datetime" in metadata:
                    acq_time = metadata["acquisition_datetime"]
                    scene_id = metadata.get("product_id", scene_id)

                env_req = environment_service.analyze_environment()
                drift_req = DriftAnalysisRequest(
                    acquisition_time=acq_time,
                    wind=env_req.wind.model_dump(),
                    ocean_current=env_req.ocean_current.model_dump(),
                    vector_field=env_req.vector_field.model_dump(),
                )
                drift_res = drift_modelling_service.run_drift_simulation(drift_req)
            except Exception as e:
                logger.error(f"Failed to resolve Phase 5 drift analysis for correlation: {e}")
                drift_res = None

        if drift_res is None:
            return AISCorrelationResponse(
                scene_id=scene_id,
                ais_available=True,
                spill_conditioned=False,
                origin_available=False,
                correlation_available=False,
                search_radius_km=search_radius,
                candidate_count=0,
                candidates=[],
                reason="Phase 5 drift analysis response could not be resolved.",
            )

        # ---------------------------------------------------------------------
        # 2. EARLY RETURN CHECK FOR NO ORIGIN (MANDATORY CORRECTION 5)
        # ---------------------------------------------------------------------
        if (
            not drift_res.spill_conditioned
            or not drift_res.origin_available
            or not drift_res.probable_origin_zone
            or not drift_res.release_window
        ):
            logger.info(
                f"[PHASE 6.2] Early return triggered for scene {scene_id}: "
                f"spill_conditioned={drift_res.spill_conditioned}, "
                f"origin_available={drift_res.origin_available}. "
                f"NO AIS database queries executed."
            )
            return AISCorrelationResponse(
                scene_id=scene_id,
                ais_available=True,
                spill_conditioned=drift_res.spill_conditioned,
                origin_available=drift_res.origin_available,
                correlation_available=False,
                release_window_start=None,
                release_window_end=None,
                origin_centroid=drift_res.origin_centroid,
                origin_area_km2=drift_res.origin.area_km2 if drift_res.origin else 0.0,
                search_radius_km=search_radius,
                candidate_count=0,
                candidates=[],
                reason="No Phase 5 probable origin is available for this scene.",
            )

        # Check AIS DB availability ONLY if origin is available
        ais_available = True
        try:
            temp_db = db_session or SessionLocal()
            temp_db.execute(select(1)).first()
            if not db_session:
                temp_db.close()
        except Exception:
            ais_available = False

        # ---------------------------------------------------------------------
        # 3. PARSE ORIGIN GEOMETRY & RELEASE WINDOW
        # ---------------------------------------------------------------------
        origin_geojson = drift_res.probable_origin_zone
        if isinstance(origin_geojson, dict) and "geometry" in origin_geojson:
            origin_geom_dict = origin_geojson["geometry"]
        else:
            origin_geom_dict = origin_geojson

        try:
            origin_shape = shapely.geometry.shape(origin_geom_dict)
        except Exception as e:
            logger.error(f"Failed to parse Phase 5 probable origin polygon geometry: {e}")
            return AISCorrelationResponse(
                scene_id=scene_id,
                ais_available=ais_available,
                spill_conditioned=drift_res.spill_conditioned,
                origin_available=drift_res.origin_available,
                correlation_available=False,
                search_radius_km=search_radius,
                candidate_count=0,
                candidates=[],
                reason=f"Failed to parse Phase 5 origin geometry: {e}",
            )

        rel_start_str = drift_res.release_window.start
        rel_end_str = drift_res.release_window.end

        try:
            rel_start_dt = datetime.fromisoformat(rel_start_str.replace("Z", "+00:00"))
            rel_end_dt = datetime.fromisoformat(rel_end_str.replace("Z", "+00:00"))
        except Exception as e:
            logger.error(f"Failed to parse release window datetimes ({rel_start_str}, {rel_end_str}): {e}")
            return AISCorrelationResponse(
                scene_id=scene_id,
                ais_available=ais_available,
                spill_conditioned=drift_res.spill_conditioned,
                origin_available=drift_res.origin_available,
                correlation_available=False,
                search_radius_km=search_radius,
                candidate_count=0,
                candidates=[],
                reason=f"Malformed Phase 5 release window timestamp format: {e}",
            )

        # Ensure UTC timezone awareness
        if rel_start_dt.tzinfo is None:
            rel_start_dt = rel_start_dt.replace(tzinfo=timezone.utc)
        if rel_end_dt.tzinfo is None:
            rel_end_dt = rel_end_dt.replace(tzinfo=timezone.utc)

        # ---------------------------------------------------------------------
        # 4. QUERY STORED AIS POSITIONS FROM LOCAL DATABASE (PHASE 6.1 DATA)
        # ---------------------------------------------------------------------
        close_session = False
        db = db_session
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            stmt = (
                select(AISVesselPosition)
                .where(
                    and_(
                        AISVesselPosition.timestamp_utc >= rel_start_dt,
                        AISVesselPosition.timestamp_utc <= rel_end_dt,
                    )
                )
                .order_by(AISVesselPosition.mmsi.asc(), AISVesselPosition.timestamp_utc.asc())
            )
            records = db.scalars(stmt).all()
        except Exception as e:
            logger.error(f"Database query for AIS positions failed: {e}")
            if close_session:
                db.close()
            return AISCorrelationResponse(
                scene_id=scene_id,
                ais_available=False,
                spill_conditioned=drift_res.spill_conditioned,
                origin_available=drift_res.origin_available,
                correlation_available=False,
                release_window_start=rel_start_str,
                release_window_end=rel_end_str,
                origin_centroid=drift_res.origin_centroid,
                origin_area_km2=drift_res.origin.area_km2 if drift_res.origin else 0.0,
                search_radius_km=search_radius,
                candidate_count=0,
                candidates=[],
                reason=f"AIS database query failed: {str(e)}",
            )
        finally:
            if close_session:
                db.close()

        if not records:
            logger.info(f"No stored AIS observations found for release window [{rel_start_str} to {rel_end_str}].")
            return AISCorrelationResponse(
                scene_id=scene_id,
                ais_available=ais_available,
                spill_conditioned=drift_res.spill_conditioned,
                origin_available=drift_res.origin_available,
                correlation_available=True,
                release_window_start=rel_start_str,
                release_window_end=rel_end_str,
                origin_centroid=drift_res.origin_centroid,
                origin_area_km2=drift_res.origin.area_km2 if drift_res.origin else 0.0,
                search_radius_km=search_radius,
                candidate_count=0,
                candidates=[],
                reason="No stored AIS observations matched the release window",
            )

        # ---------------------------------------------------------------------
        # 5. GROUP BY MMSI AND PERFORM SPATIAL CORRELATION
        # ---------------------------------------------------------------------
        mmsi_groups: Dict[str, List[AISVesselPosition]] = {}
        for r in records:
            if not r.mmsi or not math.isfinite(r.latitude) or not math.isfinite(r.longitude):
                continue
            if not (-90.0 <= r.latitude <= 90.0) or not (-180.0 <= r.longitude <= 180.0):
                continue
            mmsi_groups.setdefault(r.mmsi, []).append(r)

        candidates: List[AISCorrelationCandidate] = []

        for mmsi, pos_list in mmsi_groups.items():
            if not pos_list:
                continue

            pos_list.sort(key=lambda x: x.timestamp_utc)

            obs_count = len(pos_list)
            first_obs_iso = pos_list[0].timestamp_utc.isoformat()
            last_obs_iso = pos_list[-1].timestamp_utc.isoformat()

            point_distances: List[Tuple[float, AISVesselPosition]] = []
            inside_count = 0

            for p in pos_list:
                d_km = self._calculate_geodesic_distance_km(p.longitude, p.latitude, origin_shape)
                point_distances.append((d_km, p))
                if d_km == 0.0:
                    inside_count += 1

            point_distances.sort(key=lambda x: x[0])
            min_dist_km, closest_pos = point_distances[0]
            closest_time_iso = closest_pos.timestamp_utc.isoformat()

            track_intersects = False
            track_geometry_available = False

            if obs_count >= 2:
                try:
                    coords = [(p.longitude, p.latitude) for p in pos_list]
                    track_line = LineString(coords)
                    track_intersects = bool(origin_shape.intersects(track_line) or origin_shape.contains(track_line))
                    track_geometry_available = True
                except Exception as e:
                    logger.warning(f"Failed to construct Track LineString for MMSI {mmsi}: {e}")
                    track_geometry_available = False
            else:
                p_single = Point(pos_list[0].longitude, pos_list[0].latitude)
                track_intersects = bool(origin_shape.contains(p_single) or origin_shape.intersects(p_single))
                track_geometry_available = False

            if min_dist_km <= search_radius or track_intersects or inside_count > 0:
                sog_vals = [p.sog_knots for p in pos_list if p.sog_knots is not None and math.isfinite(p.sog_knots)]
                mean_sog = round(sum(sog_vals) / len(sog_vals), 2) if sog_vals else None
                max_sog = round(max(sog_vals), 2) if sog_vals else None
                min_sog = round(min(sog_vals), 2) if sog_vals else None

                cog_vals = [p.cog_degrees for p in pos_list]
                mean_cog = self._compute_circular_mean_cog(cog_vals)

                nav_statuses = sorted(list({p.navigational_status for p in pos_list if p.navigational_status is not None}))

                candidate = AISCorrelationCandidate(
                    mmsi=mmsi,
                    observation_count=obs_count,
                    first_observation=first_obs_iso,
                    last_observation=last_obs_iso,
                    minimum_distance_to_origin_km=min_dist_km,
                    closest_approach_time=closest_time_iso,
                    position_count_inside_origin_zone=inside_count,
                    track_intersects_origin_zone=track_intersects,
                    temporal_overlap=True,
                    track_geometry_available=track_geometry_available,
                    mean_sog_knots=mean_sog,
                    max_sog_knots=max_sog,
                    min_sog_knots=min_sog,
                    mean_cog_degrees=mean_cog,
                    navigation_status_values=nav_statuses,
                )
                candidates.append(candidate)

        out_filename = f"ais_correlation_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        out_path = settings.DATA_OUTPUT_DIR / out_filename

        response = AISCorrelationResponse(
            status="success",
            phase=6.2,
            scene_id=scene_id,
            ais_available=ais_available,
            spill_conditioned=drift_res.spill_conditioned,
            origin_available=drift_res.origin_available,
            correlation_available=True,
            release_window_start=rel_start_str,
            release_window_end=rel_end_str,
            origin_centroid=drift_res.origin_centroid,
            origin_area_km2=drift_res.origin.area_km2 if drift_res.origin else 0.0,
            search_radius_km=search_radius,
            candidate_count=len(candidates),
            candidates=candidates,
            output_file=out_filename,
            reason=f"Successfully correlated {len(candidates)} candidates for release window",
        )

        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(response.model_dump(), f, indent=2)
            logger.info(f"[PHASE 6.2] Persisted correlation artifact to {out_path}")
        except Exception as e:
            logger.error(f"Failed to persist correlation artifact JSON: {e}")

        return response


# Global singleton instance
ais_correlation_service = AISCorrelationService()
