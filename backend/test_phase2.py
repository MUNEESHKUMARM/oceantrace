"""
OceanTrace AI - Phase 2 Comprehensive Verification Test Suite
Verifies binary U-Net architecture, trained checkpoint integrity, dynamic Phase 1 scene resolution,
input compatibility audit, real PyTorch model inference, georeferenced binary mask generation,
and Phase 3 vector mapping compatibility.
"""

import sys
import os
import json
import torch
import numpy as np
import rasterio
from pathlib import Path

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.segmentation_unet import UNet
from app.services.oil_detection_service import oil_detection_service
from app.core.config import settings

def test_phase2_all():
    print("=======================================================================")
    print("OCEANTRACE AI — PHASE 2 VERIFICATION TEST SUITE (DYNAMIC U-NET)")
    print("=======================================================================")

    passed_tests = 0
    total_tests = 16

    # 1. Architecture Check
    try:
        model = UNet(in_channels=1, num_classes=1, base_c=16)
        x = torch.randn(1, 1, 256, 256)
        out = model(x)
        assert out.shape == (1, 1, 256, 256), f"Unexpected shape {out.shape}"
        print("[CHECK 1/16] Binary U-Net model architecture and output tensor shape: [PASS]")
        passed_tests += 1
    except Exception as e:
        print(f"[CHECK 1/16] Architecture Check: [FAIL] {e}")

    # 2. Checkpoint Existence and Loading
    ckpt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "checkpoints", "unet_oil_spill_real_vv.pth")
    if not os.path.exists(ckpt_path):
        ckpt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "checkpoints", "unet_oil_spill.pth")
    try:
        assert os.path.exists(ckpt_path), f"Checkpoint not found at {ckpt_path}"
        ckpt = torch.load(ckpt_path, map_location="cpu")
        state_dict = ckpt["model_state_dict"] if (isinstance(ckpt, dict) and "model_state_dict" in ckpt) else (ckpt["state_dict"] if (isinstance(ckpt, dict) and "state_dict" in ckpt) else ckpt)
        try:
            model = UNet(in_channels=1, num_classes=1, base_c=16)
            model.load_state_dict(state_dict)
        except Exception:
            model = UNet(in_channels=1, num_classes=1, base_c=64)
            model.load_state_dict(state_dict)
        print("[CHECK 2/16] Trained checkpoint exists and loads into UNet model cleanly: [PASS]")
        passed_tests += 1
    except Exception as e:
        print(f"[CHECK 2/16] Checkpoint Loading: [FAIL] {e}")

    # 3. Metadata Verification
    meta_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "checkpoints", "model_metadata.json")
    if not os.path.exists(meta_path):
        meta_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "checkpoints", "unet_oil_spill_metadata.json")
    try:
        assert os.path.exists(meta_path), f"Metadata JSON not found at {meta_path}"
        with open(meta_path, 'r') as f:
            meta = json.load(f)
        assert meta.get("num_classes") == 1 or meta.get("in_channels") == 1, "Metadata class definition invalid"
        print(f"[CHECK 3/16] Training metadata valid ({meta.get('model_name', 'U-Net')}): [PASS]")
        passed_tests += 1
    except Exception as e:
        print(f"[CHECK 3/16] Metadata Verification: [FAIL] {e}")

    # 4. Visual Validation Output Verification
    val_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "output")
    try:
        assert os.path.exists(val_dir), f"Validation output directory not found at {val_dir}"
        val_files = os.listdir(val_dir)
        assert len(val_files) > 0, "No visual validation files found in output"
        print(f"[CHECK 4/16] Visual validation output directory exists with {len(val_files)} artifacts: [PASS]")
        passed_tests += 1
    except Exception as e:
        print(f"[CHECK 4/16] Validation Artifacts: [FAIL] {e}")

    # 5. Dynamic Latest Phase 1 Scene Resolution
    latest_tif = None
    try:
        latest_tif = oil_detection_service.resolve_latest_phase1_geotiff()
        assert latest_tif.exists(), f"Resolved GeoTIFF path does not exist: {latest_tif}"
        print(f"[CHECK 5/16] Dynamic resolution of latest Phase 1 scientific GeoTIFF ({latest_tif.name}): [PASS]")
        passed_tests += 1
    except Exception as e:
        print(f"[CHECK 5/16] Dynamic Latest Scene Resolution: [FAIL] {e}")

    # 6. Scientific Input Raster Integrity Check
    try:
        with rasterio.open(latest_tif) as src:
            w, h = src.width, src.height
            crs = src.crs
            transform = src.transform
            raw_sar = src.read(1)
            finite_cnt = int(np.count_nonzero(np.isfinite(raw_sar) & (raw_sar != -9999.0)))
            total_cnt = int(raw_sar.size)

        assert finite_cnt > 0, "Input SAR raster contains 0 finite pixels"
        assert crs is not None and transform is not None, "Raster missing CRS or transform"
        print(f"[CHECK 6/16] Input scientific TIFF readability & finite pixel validation ({finite_cnt}/{total_cnt} finite): [PASS]")
        passed_tests += 1
    except Exception as e:
        print(f"[CHECK 6/16] Input Raster Integrity: [FAIL] {e}")

    # 7. Preprocessing Normalization Contract Validation
    try:
        from app.services.sar_normalization import normalize_sar_db
        norm_sar = normalize_sar_db(raw_sar)
        assert norm_sar.min() >= 0.0 and norm_sar.max() <= 1.0, f"Norm out of range: [{norm_sar.min()}, {norm_sar.max()}]"
        print("[CHECK 7/16] Preprocessing normalization contract (dB [-32, 0] -> [0.0, 1.0]): [PASS]")
        passed_tests += 1
    except Exception as e:
        print(f"[CHECK 7/16] Normalization Contract: [FAIL] {e}")

    # 8. Dynamic Domain-Shift Input Compatibility Diagnostic
    compat_info = None
    try:
        compat_info = oil_detection_service.audit_input_compatibility(raw_sar)
        status = compat_info["compatibility_status"]
        assert status in ["COMPATIBLE", "PARTIALLY_COMPATIBLE"], f"Unexpected status: {status}"
        assert "normalization_breakdown" in compat_info, "Missing normalization_breakdown"
        assert "normalized_stats" in compat_info, "Missing normalized_stats"
        bk = compat_info["normalization_breakdown"]
        print(f"[CHECK 8/16] Dynamic domain-shift input compatibility status: '{status}' ({compat_info['reason']}): [PASS]")
        print(f"    - Breakdown: < -32dB: {bk.get('below_m32_db_pct', 0)}%, [-32, 0]dB: {bk.get('between_m32_0_db_pct', 0)}%, > 0dB: {bk.get('above_0_db_pct', 0)}%")
        print(f"    - Clipping: to 0: {bk.get('clipped_to_0_pct', 0)}%, to 1: {bk.get('clipped_to_1_pct', 0)}%")
        passed_tests += 1
    except Exception as e:
        print(f"[CHECK 8/16] Compatibility Diagnostic: [FAIL] {e}")

    # 9. Real PyTorch Model Inference Execution
    res = None
    try:
        res = oil_detection_service.run_detection(str(latest_tif))
        assert "detected" in res and "confidence" in res, "Missing response fields"
        print(f"[CHECK 9/16] Real PyTorch U-Net inference executed (detected={res['detected']}, conf={res['confidence']:.4f}): [PASS]")
        passed_tests += 1
    except Exception as e:
        print(f"[CHECK 9/16] Model Inference: [FAIL] {e}")

    # 10. Prediction Mask Binary Integrity (Strictly {0, 1})
    try:
        with rasterio.open(res["mask_file"]) as m_ds:
            mask_arr = m_ds.read(1)
            u_vals = set(np.unique(mask_arr))
            assert u_vals.issubset({0, 1}), f"Non-binary mask values found: {u_vals}"
            assert not np.isnan(mask_arr).any() and not np.isinf(mask_arr).any(), "NaN/Inf in mask"
        print(f"[CHECK 10/16] Prediction mask contains binary values strictly in {{0, 1}}: [PASS]")
        passed_tests += 1
    except Exception as e:
        print(f"[CHECK 10/16] Binary Mask Verification: [FAIL] {e}")

    # 11. Prediction Mask Georeferencing Preservation (CRS & Transform)
    try:
        with rasterio.open(res["mask_file"]) as m_ds:
            assert str(m_ds.crs) == str(crs), f"CRS mismatch: {m_ds.crs} vs {crs}"
            assert m_ds.transform == transform, f"Transform mismatch: {m_ds.transform} vs {transform}"
            assert m_ds.width == w and m_ds.height == h, "Dimension mismatch"
        print(f"[CHECK 11/16] Prediction mask preserved geospatial CRS ({crs}) and transform: [PASS]")
        passed_tests += 1
    except Exception as e:
        print(f"[CHECK 11/16] Georeferencing Preservation: [FAIL] {e}")

    # 12. Detection Statistics Calculation
    try:
        bg_cnt = res["class_distribution"]["background_pixels"]
        oil_cnt = res["class_distribution"]["oil_spill_pixels"]
        oil_pct = res.get("oil_pixel_percentage", 0.0)
        assert bg_cnt + oil_cnt == total_cnt, f"Pixel count mismatch: {bg_cnt}+{oil_cnt} != {total_cnt}"
        print(f"[CHECK 12/16] Detection statistics: oil_pixels={oil_cnt}, bg_pixels={bg_cnt}, oil_pct={oil_pct:.4f}%: [PASS]")
        passed_tests += 1
    except Exception as e:
        print(f"[CHECK 12/16] Statistics Calculation: [FAIL] {e}")

    # 13. Non-Destructive SAR + Overlay Visualization Check
    try:
        overlay_path = Path(res["overlay_file"])
        assert overlay_path.exists() and overlay_path.stat().st_size > 0, "Overlay file missing or 0 bytes"
        from PIL import Image
        with Image.open(overlay_path) as img:
            ow, oh = img.size
            assert (ow, oh) == (w, h), f"Overlay size mismatch ({ow},{oh}) vs ({w},{h})"
        print(f"[CHECK 13/16] Non-destructive SAR overlay visualization artifact verified ({overlay_path.name}): [PASS]")
        passed_tests += 1
    except Exception as e:
        print(f"[CHECK 13/16] Overlay Visualization Check: [FAIL] {e}")

    # 14. Unlabeled Real-Scene Rules (No Fabricated Ground-Truth Metrics)
    try:
        assert "test_iou" not in res and "test_dice" not in res, "Live result must NOT report fabricated IoU/Dice"
        assert "accuracy" not in res, "Live result must NOT report fabricated accuracy"
        assert "disclaimer" in res, "Missing scientific disclaimer in response"
        print("[CHECK 14/14] Unlabeled real-scene rules: No fabricated ground-truth IoU/Dice/Accuracy metrics: [PASS]")
        passed_tests += 1
    except Exception as e:
        print(f"[CHECK 14/16] Unlabeled Scene Rules: [FAIL] {e}")

    # 15. Phase 3 Vector Mapping Service Compatibility
    try:
        from app.services.spill_mapping_service import spill_mapping_service
        p3_res = spill_mapping_service.run_spill_mapping(
            mask_path=res["mask_file"],
            confidence_path=res["confidence_file"],
            source_geotiff_path=str(latest_tif),
            min_region_pixels=10
        )
        assert "spill_detected" in p3_res and "geojson_file" in p3_res, "Phase 3 execution failed on generated mask"
        print(f"[CHECK 15/16] Phase 3 Vector Spill Mapping compatibility verified (detected={p3_res['spill_detected']}): [PASS]")
        passed_tests += 1
    except Exception as e:
        print(f"[CHECK 15/16] Phase 3 Compatibility: [FAIL] {e}")

    # 16. Isolated Real Scene Integration Verification
    print("\n-----------------------------------------------------------------------")
    print("REAL LATEST SENTINEL-1 SCENE INFERENCE INTEGRATION (ISOLATED)")
    print("-----------------------------------------------------------------------")
    try:
        # Run detection without specifying a path -> resolves latest scene dynamically
        live_inference_res = oil_detection_service.run_detection()
        print(f"  [REAL INFERENCE] STATUS: VERIFIED")
        print(f"  [REAL INFERENCE] Input Scene: {Path(live_inference_res['mask_file']).stem.replace('sar_mask_', '')}")
        print(f"  [REAL INFERENCE] Compatibility Status: {live_inference_res['compatibility']['compatibility_status']}")
        print(f"  [REAL INFERENCE] Oil Detected: {live_inference_res['detected']}")
        print(f"  [REAL INFERENCE] Oil Percentage: {live_inference_res['oil_pixel_percentage']}%")
        print(f"  [REAL INFERENCE] Model Score/Confidence: {live_inference_res['confidence']}")
        print(f"  [REAL INFERENCE] Mask File: {live_inference_res['mask_file']}")
        print(f"  [REAL INFERENCE] Overlay File: {live_inference_res['overlay_file']}")
        passed_tests += 1
    except Exception as e:
        print(f"  [REAL INFERENCE] STATUS: BLOCKED ({e})")

    print("\n=======================================================================")
    print(f"PHASE 2 VERIFICATION SUMMARY: {passed_tests}/{total_tests} TESTS PASSED")
    print("=======================================================================")

    if passed_tests == total_tests:
        print("PHASE 2 COMPLETE — READY FOR PHASE 3 COMPATIBILITY")
        return True
    else:
        print("PHASE 2 FAILED VERIFICATION")
        return False

if __name__ == "__main__":
    success = test_phase2_all()
    sys.exit(0 if success else 1)
