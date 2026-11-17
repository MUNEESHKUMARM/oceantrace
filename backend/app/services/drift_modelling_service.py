import os
import math
import time
import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple

import numpy as np
import shapely.geometry as sg
from shapely.ops import unary_union
from shapely import make_valid
import pyproj
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.schemas.drift import (
    DriftAnalysisRequest,
    DriftAnalysisResponse,
    DriftSimulationSummary,
    OriginZoneInfo,
    ReleaseWindow,
    TrajectoryPoint,
)

logger = logging.getLogger("oceantrace.drift_service")
logger.setLevel(logging.INFO)

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "output"))
os.makedirs(OUTPUT_DIR, exist_ok=True)


class DriftModellingService:
    """
    Phase 5 Lagrangian Particle Drift Modelling & Probable Origin Estimation Service.
    Integrates particle transport under real surface currents + 10m wind leeway factor.
    Calculates backward historical drift, probable origin zone, release window, and forward drift trajectories.
    """

    @staticmethod
    def parse_iso_datetime(dt_str: str) -> datetime:
        clean_str = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    @staticmethod
    def meters_to_degree_deltas(lat: float, dx_m: float, dy_m: float) -> Tuple[float, float]:
        """Convert metric displacement (dx, dy) in meters into WGS84 degree increments (dlon, dlat)."""
        dlat = dy_m / 111320.0
        rad_lat = math.radians(lat)
        cos_lat = max(0.0001, math.cos(rad_lat))
        dlon = dx_m / (111320.0 * cos_lat)
        return round(dlon, 7), round(dlat, 7)

    def initialize_particles(
        self,
        centroid: Dict[str, float],
        bbox: Dict[str, float],
        spill_polygon: Dict[str, Any],
        n_particles: int = 100,
        seed: int = 42,
    ) -> List[Tuple[float, float]]:
        """Initialize N particles distributed within the detected spill polygon / centroid area."""
        np.random.seed(seed)
        c_lat = centroid.get("latitude", 18.648)
        c_lon = centroid.get("longitude", 71.851)

        min_lat = bbox.get("min_lat", c_lat - 0.05)
        max_lat = bbox.get("max_lat", c_lat + 0.05)
        min_lon = bbox.get("min_lon", c_lon - 0.05)
        max_lon = bbox.get("max_lon", c_lon + 0.05)

        poly_geom = None
        if spill_polygon:
            try:
                if spill_polygon.get("type") == "Feature":
                    poly_geom = sg.shape(spill_polygon.get("geometry"))
                elif spill_polygon.get("type") in ["Polygon", "MultiPolygon"]:
                    poly_geom = sg.shape(spill_polygon)
            except Exception as e:
                logger.warning(f"Could not parse spill polygon geometry: {e}")

        particles = []
        attempts = 0
        max_attempts = n_particles * 20

        while len(particles) < n_particles and attempts < max_attempts:
            attempts += 1
            lat = np.random.uniform(min_lat, max_lat)
            lon = np.random.uniform(min_lon, max_lon)

            if poly_geom and poly_geom.is_valid:
                pt = sg.Point(lon, lat)
                if poly_geom.contains(pt) or poly_geom.distance(pt) < 0.01:
                    particles.append((lat, lon))
            else:
                # Gaussian cluster around centroid
                lat_g = float(np.random.normal(c_lat, (max_lat - min_lat) / 4.0))
                lon_g = float(np.random.normal(c_lon, (max_lon - min_lon) / 4.0))
                particles.append((lat_g, lon_g))

        # Fallback if needed
        while len(particles) < n_particles:
            lat_g = float(np.random.normal(c_lat, 0.01))
            lon_g = float(np.random.normal(c_lon, 0.01))
            particles.append((lat_g, lon_g))

        return particles

    def run_drift_simulation(
        self,
        req: DriftAnalysisRequest,
    ) -> DriftAnalysisResponse:
        """
        Executes Lagrangian Backward and Forward Drift Simulations, estimates the Probable Origin Zone,
        calculates estimated release window, and generates output GeoJSONs and visual map PNG.
        """
        # Step 1: Check if this request represents an empty scene (no detected spill region)
        is_empty = False
        if req.spill_conditioned is False and req.spill_regions_count == 0 and req.spill_polygon is None:
            is_empty = True

        c_lat = req.centroid.get("latitude") if req.centroid else None
        c_lon = req.centroid.get("longitude") if req.centroid else None

        if (c_lat is None or c_lon is None or not math.isfinite(c_lat) or not math.isfinite(c_lon) or (c_lat == 0.0 and c_lon == 0.0)) and req.spill_polygon is None:
            is_empty = True

        if is_empty:
            logger.info("Empty scene detected (0 predicted oil pixels / 0 spill regions). Returning inactive drift analysis response.")
            return DriftAnalysisResponse(
                status="success",
                phase=5,
                drift_available=False,
                spill_conditioned=False,
                origin_available=False,
                backward_drift=DriftSimulationSummary(
                    duration_hours=0.0,
                    particle_count=0,
                    trajectory_file="",
                    points_sample=[],
                ),
                forward_drift=DriftSimulationSummary(
                    duration_hours=0.0,
                    particle_count=0,
                    trajectory_file="",
                    points_sample=[],
                ),
                origin=OriginZoneInfo(
                    zone_file="",
                    centroid={"latitude": 0.0, "longitude": 0.0},
                    area_km2=0.0,
                    confidence=0.0,
                    geojson_feature={},
                ),
                release_window=ReleaseWindow(
                    start="",
                    end="",
                ),
                probable_origin_zone=None,
                origin_centroid=None,
                estimated_release_window=None,
                origin_confidence=None,
                outputs={},
            )

        acq_dt = self.parse_iso_datetime(req.acquisition_time)
        timestamp_str = str(int(acq_dt.timestamp()))

        # Extract Phase 4 environmental velocities
        curr_u = float(req.ocean_current.get("u_mean", 0.0))
        curr_v = float(req.ocean_current.get("v_mean", 0.0))
        wind_u = float(req.wind.get("u10_mean", 0.0))
        wind_v = float(req.wind.get("v10_mean", 0.0))

        alpha_wind = float(req.wind_drift_coeff)
        diff_k = float(req.diffusion_coeff)

        # Net Transport Velocity (m/s)
        u_net = curr_u + alpha_wind * wind_u
        v_net = curr_v + alpha_wind * wind_v

        n_particles = max(10, min(req.particle_count, 500))
        dt_mins = max(5, min(req.time_step_mins, 60))
        dt_secs = dt_mins * 60
        duration_hrs = max(1.0, min(req.duration_hours, 72.0))
        n_steps = int((duration_hrs * 3600) / dt_secs)

        # Initialize particles
        init_particles = self.initialize_particles(
            centroid=req.centroid,
            bbox=req.bbox,
            spill_polygon=req.spill_polygon,
            n_particles=n_particles,
            seed=42,
        )

        # ---------------------------------------------------------------------
        # 1. BACKWARD DRIFT SIMULATION (Reverse Time Transport)
        # ---------------------------------------------------------------------
        logger.info(f"Running Lagrangian Backward Drift Simulation ({duration_hrs}h, {n_particles} particles)...")
        np.random.seed(101)

        backward_trajectories: List[List[Dict[str, Any]]] = []
        final_backward_pts: List[Tuple[float, float]] = []

        for pid, (start_lat, start_lon) in enumerate(init_particles):
            traj = []
            curr_lat, curr_lon = start_lat, start_lon
            t_current = acq_dt

            traj.append({
                "particle_id": pid,
                "timestamp": t_current.isoformat(),
                "latitude": round(curr_lat, 6),
                "longitude": round(curr_lon, 6),
            })

            for step in range(1, n_steps + 1):
                t_current = acq_dt - timedelta(seconds=step * dt_secs)

                # Stochastic turbulent diffusion
                diff_scale = math.sqrt(2.0 * diff_k * dt_secs) if diff_k > 0 else 0.0
                stoch_x = np.random.normal(0, diff_scale)
                stoch_y = np.random.normal(0, diff_scale)

                # Reverse time displacement (negative dt)
                dx_m = -u_net * dt_secs + stoch_x
                dy_m = -v_net * dt_secs + stoch_y

                dlon, dlat = self.meters_to_degree_deltas(curr_lat, dx_m, dy_m)
                curr_lat += dlat
                curr_lon += dlon

                traj.append({
                    "particle_id": pid,
                    "timestamp": t_current.isoformat(),
                    "latitude": round(curr_lat, 6),
                    "longitude": round(curr_lon, 6),
                })

            backward_trajectories.append(traj)
            final_backward_pts.append((curr_lat, curr_lon))

        # ---------------------------------------------------------------------
        # 2. FORWARD DRIFT SIMULATION (Forward Time Transport)
        # ---------------------------------------------------------------------
        logger.info(f"Running Lagrangian Forward Drift Simulation ({duration_hrs}h, {n_particles} particles)...")
        np.random.seed(202)

        forward_trajectories: List[List[Dict[str, Any]]] = []

        for pid, (start_lat, start_lon) in enumerate(init_particles):
            traj = []
            curr_lat, curr_lon = start_lat, start_lon
            t_current = acq_dt

            traj.append({
                "particle_id": pid,
                "timestamp": t_current.isoformat(),
                "latitude": round(curr_lat, 6),
                "longitude": round(curr_lon, 6),
            })

            for step in range(1, n_steps + 1):
                t_current = acq_dt + timedelta(seconds=step * dt_secs)

                diff_scale = math.sqrt(2.0 * diff_k * dt_secs) if diff_k > 0 else 0.0
                stoch_x = np.random.normal(0, diff_scale)
                stoch_y = np.random.normal(0, diff_scale)

                # Forward time displacement (positive dt)
                dx_m = u_net * dt_secs + stoch_x
                dy_m = v_net * dt_secs + stoch_y

                dlon, dlat = self.meters_to_degree_deltas(curr_lat, dx_m, dy_m)
                curr_lat += dlat
                curr_lon += dlon

                traj.append({
                    "particle_id": pid,
                    "timestamp": t_current.isoformat(),
                    "latitude": round(curr_lat, 6),
                    "longitude": round(curr_lon, 6),
                })

            forward_trajectories.append(traj)

        # ---------------------------------------------------------------------
        # 3. PROBABLE ORIGIN ZONE ESTIMATION & DENSITY CONVERGENCE
        # ---------------------------------------------------------------------
        back_lats = [pt[0] for pt in final_backward_pts]
        back_lons = [pt[1] for pt in final_backward_pts]

        origin_lat = float(np.mean(back_lats))
        origin_lon = float(np.mean(back_lons))

        # Build Probable Origin Zone Polygon (Convex Hull of backward particle cluster with buffer)
        pts_shapely = [sg.Point(lon, lat) for lat, lon in final_backward_pts]
        multi_pt = sg.MultiPoint(pts_shapely)

        if len(pts_shapely) >= 3:
            origin_hull = multi_pt.convex_hull.buffer(0.015) # ~1.5 km buffer
        else:
            origin_hull = sg.Point(origin_lon, origin_lat).buffer(0.02)

        origin_hull = make_valid(origin_hull)

        # Compute Geodesic Ground Area in sq km using WGS84 ellipsoid
        geod = pyproj.Geod(ellps="WGS84")
        area_m2, _ = geod.geometry_area_perimeter(origin_hull)
        origin_area_km2 = round(abs(area_m2) / 1e6, 4)

        # Compute Non-random Origin Confidence Score
        lat_var = float(np.var(back_lats))
        lon_var = float(np.var(back_lons))
        dispersion_deg = math.sqrt(lat_var + lon_var)
        # Higher convergence (lower dispersion) yields higher confidence
        confidence_score = round(max(0.35, min(0.95, 1.0 - dispersion_deg * 4.0)), 4)

        # Derived Estimated Historical Release Window
        release_start_dt = acq_dt - timedelta(hours=duration_hrs)
        release_end_dt = acq_dt

        rel_start_str = release_start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        rel_end_str = release_end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        origin_feature = {
            "type": "Feature",
            "properties": {
                "name": "Probable Origin Zone",
                "area_km2": origin_area_km2,
                "confidence": confidence_score,
                "release_start": rel_start_str,
                "release_end": rel_end_str,
            },
            "geometry": sg.mapping(origin_hull),
        }

        # ---------------------------------------------------------------------
        # 4. EXPORT GEOJSON ARTIFACTS
        # ---------------------------------------------------------------------
        back_geojson_path = os.path.join(OUTPUT_DIR, f"backward_drift_{timestamp_str}.geojson")
        fwd_geojson_path = os.path.join(OUTPUT_DIR, f"forward_drift_{timestamp_str}.geojson")
        origin_geojson_path = os.path.join(OUTPUT_DIR, f"origin_zone_{timestamp_str}.geojson")
        viz_png_path = os.path.join(OUTPUT_DIR, f"drift_map_{timestamp_str}.png")

        # Save Backward Drift GeoJSON
        back_features = []
        for pid, traj in enumerate(backward_trajectories):
            coords = [[pt["longitude"], pt["latitude"]] for pt in traj]
            back_features.append({
                "type": "Feature",
                "properties": {"particle_id": pid, "direction": "backward"},
                "geometry": {"type": "LineString", "coordinates": coords},
            })
        with open(back_geojson_path, "w") as f:
            json.dump({"type": "FeatureCollection", "features": back_features}, f, indent=2)

        # Save Forward Drift GeoJSON
        fwd_features = []
        for pid, traj in enumerate(forward_trajectories):
            coords = [[pt["longitude"], pt["latitude"]] for pt in traj]
            fwd_features.append({
                "type": "Feature",
                "properties": {"particle_id": pid, "direction": "forward"},
                "geometry": {"type": "LineString", "coordinates": coords},
            })
        with open(fwd_geojson_path, "w") as f:
            json.dump({"type": "FeatureCollection", "features": fwd_features}, f, indent=2)

        # Save Origin Zone GeoJSON
        with open(origin_geojson_path, "w") as f:
            json.dump(origin_feature, f, indent=2)

        # ---------------------------------------------------------------------
        # 5. GENERATE VISUALIZATION PNG (Matplotlib Drift Map)
        # ---------------------------------------------------------------------
        fig, ax = plt.subplots(figsize=(8, 8), dpi=150)
        ax.set_facecolor("#030d18")
        fig.patch.set_facecolor("#030d18")

        # Plot backward trajectories (Amber/Gold lines)
        for traj in backward_trajectories[:40]:
            lons = [p["longitude"] for p in traj]
            lats = [p["latitude"] for p in traj]
            ax.plot(lons, lats, color="#f59e0b", alpha=0.35, linewidth=0.8, linestyle="--")

        # Plot forward trajectories (Cyan lines)
        for traj in forward_trajectories[:40]:
            lons = [p["longitude"] for p in traj]
            lats = [p["latitude"] for p in traj]
            ax.plot(lons, lats, color="#22d3ee", alpha=0.35, linewidth=0.8, linestyle="-.")

        # Plot Origin Zone (Gold Polygon)
        if origin_hull.geom_type == "Polygon":
            hx, hy = origin_hull.exterior.xy
            ax.fill(hx, hy, color="#f59e0b", alpha=0.25, label="Probable Origin Zone")
            ax.plot(hx, hy, color="#f59e0b", linewidth=1.8, linestyle="--")

        # Plot Origin Centroid
        ax.scatter([origin_lon], [origin_lat], color="#f59e0b", s=60, marker="*", zorder=10, label="Estimated Origin Centroid")

        # Plot Observed Spill Centroid
        ax.scatter([c_lon], [c_lat], color="#ef4444", s=50, marker="o", zorder=10, label="Observed Spill Location")

        ax.set_title(
            f"OceanTrace AI — Drift Simulation & Probable Origin\nAcquisition: {req.acquisition_time}",
            color="#22d3ee",
            fontsize=10,
            fontweight="bold",
            pad=12,
        )
        ax.set_xlabel("Longitude (°E)", color="#94a3b8", fontsize=8)
        ax.set_ylabel("Latitude (°N)", color="#94a3b8", fontsize=8)
        ax.tick_params(colors="#64748b", labelsize=7)
        ax.grid(True, color="#1e293b", linestyle=":", linewidth=0.5)

        legend = ax.legend(loc="upper right", facecolor="#06111f", edgecolor="#334155", fontsize=7)
        for text in legend.get_texts():
            text.set_color("#94a3b8")

        plt.tight_layout()
        fig.savefig(viz_png_path, bbox_inches="tight")
        plt.close(fig)

        # ---------------------------------------------------------------------
        # 6. CONSTRUCT RESPONSE MODEL
        # ---------------------------------------------------------------------
        back_sample = [
            TrajectoryPoint(
                particle_id=t["particle_id"],
                timestamp=t["timestamp"],
                latitude=t["latitude"],
                longitude=t["longitude"],
            )
            for traj in backward_trajectories[:5]
            for t in traj[::max(1, len(traj) // 4)]
        ]

        fwd_sample = [
            TrajectoryPoint(
                particle_id=t["particle_id"],
                timestamp=t["timestamp"],
                latitude=t["latitude"],
                longitude=t["longitude"],
            )
            for traj in forward_trajectories[:5]
            for t in traj[::max(1, len(traj) // 4)]
        ]

        return DriftAnalysisResponse(
            status="success",
            phase=5,
            drift_available=True,
            spill_conditioned=True,
            origin_available=True,
            backward_drift=DriftSimulationSummary(
                duration_hours=duration_hrs,
                particle_count=n_particles,
                trajectory_file=back_geojson_path,
                points_sample=back_sample,
            ),
            forward_drift=DriftSimulationSummary(
                duration_hours=duration_hrs,
                particle_count=n_particles,
                trajectory_file=fwd_geojson_path,
                points_sample=fwd_sample,
            ),
            origin=OriginZoneInfo(
                zone_file=origin_geojson_path,
                centroid={"latitude": round(origin_lat, 6), "longitude": round(origin_lon, 6)},
                area_km2=origin_area_km2,
                confidence=confidence_score,
                geojson_feature=origin_feature,
            ),
            release_window=ReleaseWindow(
                start=rel_start_str,
                end=rel_end_str,
            ),
            probable_origin_zone=origin_feature,
            origin_centroid={"latitude": round(origin_lat, 6), "longitude": round(origin_lon, 6)},
            estimated_release_window={"start": rel_start_str, "end": rel_end_str},
            origin_confidence=confidence_score,
            outputs={
                "backward_drift_geojson": os.path.basename(back_geojson_path),
                "forward_drift_geojson": os.path.basename(fwd_geojson_path),
                "origin_zone_geojson": os.path.basename(origin_geojson_path),
                "drift_map_png": os.path.basename(viz_png_path),
            },
        )


# Global singleton instance
drift_modelling_service = DriftModellingService()
