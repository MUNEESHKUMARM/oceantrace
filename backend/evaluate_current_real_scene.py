"""
OceanTrace AI — Current Real-Scene Re-Evaluation (Phase 2.4)
Runs production OilDetectionService with new physical unet_oil_spill_real_vv.pth model
on the latest real Sentinel-1 acquisition from Phase 1.
Applies strict scientific reporting guidelines (unlabeled scene diagnostics only).
"""

import os
import json
import numpy as np
import rasterio

from app.services.oil_detection_service import oil_detection_service

OUTPUT_JSON_PATH = "g:/SIH/oceantrace-ai/backend/data/current_scene_detection_result.json"

def evaluate_current_scene():
    print("=== OCEANTRACE AI — CURRENT REAL SENTINEL-1 SCENE INFERENCE ===")
    
    # 1. Resolve latest Phase 1 scientific GeoTIFF
    latest_tif = oil_detection_service.resolve_latest_phase1_geotiff()
    print(f"Target Sentinel-1 Acquisition Raster: {latest_tif.name}")

    # 2. Execute AI detection using new physical model checkpoint
    res = oil_detection_service.run_detection(str(latest_tif))

    print("\n--- Current Scene AI Detection Results ---")
    print(f"  Target Raster File  : {latest_tif.name}")
    print(f"  Compatibility Status: {res['compatibility']['compatibility_status']}")
    print(f"  Model-Predicted Oil : {res['detected']}")
    print(f"  Model Confidence    : {res['confidence']}")
    print(f"  Oil Pixel Percentage: {res['oil_pixel_percentage']}%")
    print(f"  Oil Pixel Count     : {res['class_distribution']['oil_spill_pixels']}")
    print(f"  Background Pixels   : {res['class_distribution']['background_pixels']}")
    print(f"  Prediction Mask File: {res['mask_file']}")
    print(f"  Confidence Map File : {res['confidence_file']}")
    print(f"  Overlay Image File  : {res['overlay_file']}")
    print(f"  Frozen Threshold    : {res['threshold']}")
    print(f"  Scientific Status   : {res['disclaimer']}")

    # Save structured JSON manifest
    with open(OUTPUT_JSON_PATH, "w") as f:
        json.dump(res, f, indent=2)

    print(f"\nSaved current scene detection result to {OUTPUT_JSON_PATH}")
    return res

if __name__ == "__main__":
    evaluate_current_scene()
