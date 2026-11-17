import os
import json
import logging
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger("oceantrace.scene_state_service")


class SceneStateService:
    """
    Manages persistent backend scene processing state and environmental metadata lineage.
    Persists state to data/output/scene_state.json.
    """

    def __init__(self, state_file_path: Optional[Path] = None):
        if state_file_path:
            self.state_file = state_file_path
        else:
            self.state_file = settings.DATA_OUTPUT_DIR / "scene_state.json"
        
        self._lock = threading.Lock()
        self._ensure_state_file()

    def _ensure_state_file(self):
        """Initializes empty state file if non-existent."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            initial_state = {
                "last_processed_product_id": None,
                "last_processed_acquisition_datetime": None,
                "last_updated": None,
                "processing_status": "IDLE",
                "phase4_status": "IDLE",
                "wind_data_time": None,
                "wind_offset_seconds": 0.0,
                "current_data_time": None,
                "current_offset_seconds": 0.0,
                "spill_conditioned": False,
                "spill_regions_count": 0,
                "scene_history": [],
            }
            self._write_state_unlocked(initial_state)

    def _read_state_unlocked(self) -> Dict[str, Any]:
        """Reads state JSON without acquiring lock."""
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read scene state file ({str(e)}), resetting to default.")
            return {
                "last_processed_product_id": None,
                "last_processed_acquisition_datetime": None,
                "last_updated": None,
                "processing_status": "IDLE",
                "phase4_status": "IDLE",
                "wind_data_time": None,
                "wind_offset_seconds": 0.0,
                "current_data_time": None,
                "current_offset_seconds": 0.0,
                "spill_conditioned": False,
                "spill_regions_count": 0,
                "scene_history": [],
            }

    def _write_state_unlocked(self, state: Dict[str, Any]):
        """Writes state JSON without acquiring lock."""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write scene state file: {str(e)}")

    def get_state(self) -> Dict[str, Any]:
        """Thread-safe retrieval of current scene state."""
        with self._lock:
            return self._read_state_unlocked()

    def update_state(self, updates: Dict[str, Any]):
        """Thread-safe state update."""
        with self._lock:
            current = self._read_state_unlocked()
            current.update(updates)
            current["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            self._write_state_unlocked(current)

    def record_successful_scene(
        self,
        product_id: str,
        acquisition_datetime: str,
        wind_data_time: str,
        wind_offset: float,
        current_data_time: str,
        current_offset: float,
        phase4_status: str = "VALID",
        spill_conditioned: bool = False,
        spill_regions_count: int = 0,
    ):
        """
        Records a fully processed Sentinel-1 scene and updates lineage history.
        """
        with self._lock:
            state = self._read_state_unlocked()
            state["last_processed_product_id"] = product_id
            state["last_processed_acquisition_datetime"] = acquisition_datetime
            state["wind_data_time"] = wind_data_time
            state["wind_offset_seconds"] = round(wind_offset, 2)
            state["current_data_time"] = current_data_time
            state["current_offset_seconds"] = round(current_offset, 2)
            state["processing_status"] = "SUCCESS"
            state["phase4_status"] = phase4_status
            state["spill_conditioned"] = spill_conditioned
            state["spill_regions_count"] = spill_regions_count
            state["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            # Maintain history list (max 50 recent entries)
            history = state.get("scene_history", [])
            history.insert(0, {
                "product_id": product_id,
                "acquisition_datetime": acquisition_datetime,
                "processed_time": state["last_updated"],
                "phase4_status": phase4_status,
                "wind_offset": round(wind_offset, 2),
                "current_offset": round(current_offset, 2),
            })
            state["scene_history"] = history[:50]

            self._write_state_unlocked(state)
            logger.info(f"[SCENE_STATE] Saved successful scene processing state for {product_id}")


scene_state_service = SceneStateService()
