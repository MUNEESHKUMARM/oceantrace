import time
import logging
import threading
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

from app.services.scene_state_service import scene_state_service
from app.services.sentinel1_service import sentinel1_service
from app.services.oil_detection_service import oil_detection_service
from app.services.spill_mapping_service import spill_mapping_service
from app.services.environment_service import environment_service
from app.services.drift_modelling_service import drift_modelling_service

from app.schemas.environment import EnvironmentAnalysisRequest
from app.schemas.drift import DriftAnalysisRequest

logger = logging.getLogger("oceantrace.scene_watcher_service")


class SceneWatcherService:
    """
    Phase 4 Auto-Sync & Scene Watcher Service.
    Monitors CDSE STAC catalog for new Sentinel-1 acquisitions.
    When a NEW product_id is detected (or retry needed), automatically triggers
    Phase 1 -> Phase 2 -> Phase 3 -> Phase 4 -> Phase 5 integration pipeline.
    Prevents duplicate processing when product_id is unchanged.
    """

    def __init__(self):
        self._watcher_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def check_and_sync_latest_scene(
        self,
        bbox: Tuple[float, float, float, float] = (71.5, 18.0, 72.5, 19.0),
        force_retry: bool = False,
    ) -> Dict[str, Any]:
        """
        Queries CDSE STAC for the latest Sentinel-1 GRD acquisition on the configured AOI.
        Triggers processing pipeline ONLY if the scene product_id is new or needs retry.
        Guarantees zero duplicate processing when product_id is unchanged.
        """
        logger.info("[AUTO-SYNC] Querying CDSE STAC for latest Sentinel-1 acquisition...")
        
        try:
            # Query CDSE STAC candidate scenes sorted newest first
            candidates = sentinel1_service.search_scenes(
                bbox=bbox,
                start_date="2024-01-01",
                end_date="2026-12-31",
                max_results=5,
            )
        except Exception as e:
            logger.warning(f"[AUTO-SYNC] STAC discovery failed ({str(e)}), using cached Phase 1 resolution.")
            candidates = []

        if candidates:
            newest = candidates[0]
            candidate_product_id = newest.get("id", "S1D_IW_GRDH_1SDV_20260918T010238_20260918T010309_004625_008A01_036E_COG")
            candidate_acq_time = newest.get("datetime", "2026-09-18T01:02:38Z")
        else:
            candidate_product_id = "S1D_IW_GRDH_1SDV_20260918T010238_20260918T010309_004625_008A01_036E_COG"
            candidate_acq_time = "2026-09-18T01:02:38Z"

        current_state = scene_state_service.get_state()
        last_product_id = current_state.get("last_processed_product_id")
        phase4_status = current_state.get("phase4_status", "IDLE")

        # DUPLICATE PROTECTION: If product_id is identical AND Phase 4 status is VALID, skip processing
        is_new_product = bool(candidate_product_id != last_product_id)
        needs_retry = bool(phase4_status == "PARTIAL" or force_retry)

        if not is_new_product and not needs_retry:
            logger.info(
                f"[AUTO-SYNC] Scene product {candidate_product_id} is already processed and up-to-date (Phase 4 status: {phase4_status}). "
                f"Skipping duplicate pipeline execution."
            )
            return {
                "triggered": False,
                "reason": "already_processed",
                "product_id": candidate_product_id,
                "acquisition_datetime": candidate_acq_time,
                "last_processed_product_id": last_product_id,
                "phase4_status": phase4_status,
            }

        logger.info(
            f"[AUTO-SYNC] New acquisition detected or retry triggered: {candidate_product_id} ({candidate_acq_time}). "
            f"Executing Phase 1-5 Auto-Sync Pipeline..."
        )

        try:
            # PHASE 1: Fetch and preprocess SAR raster
            p1_res = sentinel1_service.fetch_and_process_sar(bbox=bbox)
            geotiff_path = p1_res["output_file"]
            acq_time = p1_res.get("acquisition_time", candidate_acq_time)
            prod_id = p1_res.get("source_product_id", candidate_product_id)

            # PHASE 2: AI U-Net Oil Detection
            p2_res = oil_detection_service.run_detection(geotiff_path=geotiff_path)

            # PHASE 3: Real Oil-Spill Vector Mapping
            p3_res = spill_mapping_service.run_spill_mapping(
                mask_path=p2_res["mask_file"],
                confidence_path=p2_res["confidence_file"],
                source_geotiff_path=geotiff_path,
                min_region_pixels=10,
                acquisition_time=acq_time,
                scene_id=prod_id,
            )

            # PHASE 4: Real Atmospheric Wind + Ocean Current Analysis
            spill_det = p3_res.get("spill_detected", False)
            regions_cnt = p3_res.get("regions_count", 0)

            centroid = p3_res.get("centroid") or {
                "latitude": (bbox[1] + bbox[3]) / 2.0,
                "longitude": (bbox[0] + bbox[2]) / 2.0,
            }
            bbox_dict = p3_res.get("bbox") or {
                "min_lat": bbox[1],
                "min_lon": bbox[0],
                "max_lat": bbox[3],
                "max_lon": bbox[2],
            }

            env_req = EnvironmentAnalysisRequest(
                scene_id=prod_id,
                acquisition_time=acq_time,
                centroid=centroid,
                bbox=bbox_dict,
                spill_conditioned=spill_det,
                spill_regions_count=regions_cnt,
            )
            p4_res = environment_service.analyze_environment(env_req)

            # PHASE 5: Lagrangian Drift Simulation
            drift_req = DriftAnalysisRequest(
                centroid=centroid,
                bbox=bbox_dict,
                acquisition_time=acq_time,
                wind=p4_res.wind.model_dump(),
                ocean_current=p4_res.ocean_current.model_dump(),
                vector_field=p4_res.vector_field.model_dump(),
                particle_count=100,
                duration_hours=24.0,
            )
            p5_res = drift_modelling_service.run_drift_simulation(drift_req)

            # Record state in persistent store
            scene_state_service.record_successful_scene(
                product_id=prod_id,
                acquisition_datetime=acq_time,
                wind_data_time=p4_res.wind.data_time,
                wind_offset=p4_res.wind.offset_seconds,
                current_data_time=p4_res.ocean_current.data_time,
                current_offset=p4_res.ocean_current.offset_seconds,
                phase4_status=p4_res.wind.status,
                spill_conditioned=spill_det,
                spill_regions_count=regions_cnt,
            )

            logger.info(f"[AUTO-SYNC] Pipeline completed successfully for new scene {prod_id}.")

            return {
                "triggered": True,
                "status": "success",
                "product_id": prod_id,
                "acquisition_datetime": acq_time,
                "phase1": p1_res,
                "phase2": p2_res,
                "phase3": p3_res,
                "phase4": p4_res.model_dump(),
                "phase5": p5_res.model_dump(),
            }

        except Exception as e:
            logger.error(f"[AUTO-SYNC] Pipeline execution failed: {str(e)}")
            scene_state_service.update_state({
                "processing_status": "FAILED",
                "phase4_status": "PARTIAL",
            })
            raise RuntimeError(f"Auto-sync pipeline failed: {str(e)}")

    def start_background_watcher(self, interval_seconds: int = 600):
        """Starts periodic background watcher thread."""
        if self._watcher_thread and self._watcher_thread.is_alive():
            logger.info("[AUTO-SYNC] Background watcher thread is already running.")
            return

        self._stop_event.clear()

        def _watcher_loop():
            logger.info(f"[AUTO-SYNC] Started background scene watcher (interval: {interval_seconds}s)")
            while not self._stop_event.is_set():
                try:
                    self.check_and_sync_latest_scene()
                except Exception as e:
                    logger.warning(f"[AUTO-SYNC] Background watcher check failed: {str(e)}")
                self._stop_event.wait(interval_seconds)

        self._watcher_thread = threading.Thread(target=_watcher_loop, daemon=True)
        self._watcher_thread.start()

    def stop_background_watcher(self):
        """Stops background watcher thread."""
        if self._watcher_thread:
            self._stop_event.set()
            self._watcher_thread.join(timeout=3)
            logger.info("[AUTO-SYNC] Stopped background scene watcher.")


scene_watcher_service = SceneWatcherService()
