"""
OceanTrace AI — Phase 2.4 Metric & Data Audit Script
Audits raw confusion counts, exact metric formulas, test set independence,
lookalike FPR co-existence, and current scene confidence score semantics.
"""

import os
import json
import torch
import numpy as np
import rasterio
from torch.utils.data import DataLoader, TensorDataset

from app.models.segmentation_unet import UNet
from app.services.oil_detection_service import oil_detection_service
from train_unet_superfast import build_fast_tensors, calculate_metrics

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MANIFEST_PATH = "g:/SIH/oceantrace-ai/backend/data/dataset_real_splits.json"
CACHE_PATH = "g:/SIH/oceantrace-ai/backend/data/dataset_masks_cache.npz"
CHECKPOINT_PATH = "g:/SIH/oceantrace-ai/backend/models/checkpoints/unet_oil_spill_real_vv.pth"

def run_metric_audit():
    print("==================================================================")
    print("OCEANTRACE AI — PHASE 2.4 POST-TRAINING METRIC AUDIT")
    print("==================================================================")

    # 1. Audit Dataset Independence & Overlap
    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)

    train_items = manifest["train_items"]
    val_items = manifest["val_items"]
    test_items = manifest["test_items"]

    train_paths = set([item["path"] for item in train_items if "path" in item])
    val_paths = set([item["path"] for item in val_items if "path" in item])
    test_ids = set([item["id"] for item in test_items if "id" in item])

    overlap_train_val = train_paths.intersection(val_paths)
    print("--- 1. Dataset Independence Audit ---")
    print(f"Train rasters/masks      : {len(train_items)}")
    print(f"Val rasters/masks        : {len(val_items)}")
    print(f"Test rasters/masks       : {len(test_items)} (Part III isolated)")
    print(f"Train/Val Path Overlap   : {len(overlap_train_val)} files (Must be 0)")
    assert len(overlap_train_val) == 0, "DATA LEAKAGE DETECTED between Train and Val!"

    # 2. Evaluate Model on Validation Set (514 rasters)
    cache = np.load(CACHE_PATH)
    val_masks = cache["val_masks"]
    val_x, val_y = build_fast_tensors(val_items, val_masks)

    model = UNet(in_channels=1, num_classes=1, base_c=16).to(DEVICE)
    ckpt = torch.load(CHECKPOINT_PATH, map_location=DEVICE)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    val_loader = DataLoader(TensorDataset(val_x, val_y), batch_size=32, shuffle=False)
    val_preds_list = []
    val_targets_list = []

    with torch.no_grad():
        for x, y in val_loader:
            logits = model(x.to(DEVICE))
            probs = torch.sigmoid(logits).cpu().numpy()
            val_preds_list.append(probs)
            val_targets_list.append(y.numpy())

    val_preds = np.concatenate(val_preds_list, axis=0)
    val_targets = np.concatenate(val_targets_list, axis=0)

    val_bin_preds = (val_preds > 0.50).astype(np.uint8)
    val_bin_targets = (val_targets > 0.50).astype(np.uint8)

    val_tp = int(np.count_nonzero((val_bin_preds == 1) & (val_bin_targets == 1)))
    val_tn = int(np.count_nonzero((val_bin_preds == 0) & (val_bin_targets == 0)))
    val_fp = int(np.count_nonzero((val_bin_preds == 1) & (val_bin_targets == 0)))
    val_fn = int(np.count_nonzero((val_bin_preds == 0) & (val_bin_targets == 1)))

    print("\n--- 2. Raw Validation Set Confusion Matrix ---")
    print(f"Total Evaluated Pixels : {val_bin_preds.size:,}")
    print(f"TP (Oil correctly pred): {val_tp:,}")
    print(f"TN (Bg correctly pred) : {val_tn:,}")
    print(f"FP (Bg falsely pred oil): {val_fp:,}")
    print(f"FN (Oil missed)        : {val_fn:,}")

    val_iou = float(val_tp / (val_tp + val_fp + val_fn)) if (val_tp + val_fp + val_fn) > 0 else 1.0
    val_dice = float((2.0 * val_tp) / (2.0 * val_tp + val_fp + val_fn)) if (2.0 * val_tp + val_fp + val_fn) > 0 else 1.0
    val_prec = float(val_tp / (val_tp + val_fp)) if (val_tp + val_fp) > 0 else 0.0
    val_rec = float(val_tp / (val_tp + val_fn)) if (val_tp + val_fn) > 0 else 0.0
    val_f1 = float((2.0 * val_prec * val_rec) / (val_prec + val_rec)) if (val_prec + val_rec) > 0 else 0.0

    print(f"Raw Validation Metrics: IoU={val_iou:.6f}, Dice={val_dice:.6f}, Precision={val_prec:.6f}, Recall={val_rec:.6f}, F1={val_f1:.6f}")

    # 3. Evaluate Model on Official Part III Test Set (450 rasters: 150 Oil, 150 No-Oil, 150 Lookalike)
    test_x, test_y = build_fast_tensors(test_items, np.zeros((len(test_items), 256, 256), dtype=np.uint8))
    test_loader = DataLoader(TensorDataset(test_x, test_y), batch_size=32, shuffle=False)

    test_preds_list = []
    test_targets_list = []

    with torch.no_grad():
        for x, y in test_loader:
            logits = model(x.to(DEVICE))
            probs = torch.sigmoid(logits).cpu().numpy()
            test_preds_list.append(probs)
            test_targets_list.append(y.numpy())

    test_preds = np.concatenate(test_preds_list, axis=0)
    test_targets = np.concatenate(test_targets_list, axis=0)

    test_bin_preds = (test_preds > 0.50).astype(np.uint8)
    test_bin_targets = (test_targets > 0.50).astype(np.uint8)

    # Category breakdowns
    oil_idx = [i for i, item in enumerate(test_items) if item.get("type") == "oil"]
    no_oil_idx = [i for i, item in enumerate(test_items) if item.get("type") == "no_oil"]
    lookalike_idx = [i for i, item in enumerate(test_items) if item.get("type") == "lookalike"]

    # Overall test confusion matrix
    test_tp = int(np.count_nonzero((test_bin_preds == 1) & (test_bin_targets == 1)))
    test_tn = int(np.count_nonzero((test_bin_preds == 0) & (test_bin_targets == 0)))
    test_fp = int(np.count_nonzero((test_bin_preds == 1) & (test_bin_targets == 0)))
    test_fn = int(np.count_nonzero((test_bin_preds == 0) & (test_bin_targets == 1)))

    print("\n--- 3. Official Part III Test Confusion Matrix (All 450 Rasters) ---")
    print(f"Total Evaluated Pixels : {test_bin_preds.size:,}")
    print(f"TP (Oil correctly pred): {test_tp:,}")
    print(f"TN (Bg correctly pred) : {test_tn:,}")
    print(f"FP (Bg falsely pred oil): {test_fp:,}")
    print(f"FN (Oil missed)        : {test_fn:,}")

    # Oil subset
    oil_preds = test_bin_preds[oil_idx]
    oil_targets = test_bin_targets[oil_idx]
    oil_tp = int(np.count_nonzero((oil_preds == 1) & (oil_targets == 1)))
    oil_fp = int(np.count_nonzero((oil_preds == 1) & (oil_targets == 0)))
    oil_fn = int(np.count_nonzero((oil_preds == 0) & (oil_targets == 1)))
    oil_tn = int(np.count_nonzero((oil_preds == 0) & (oil_targets == 0)))

    # No-Oil subset
    no_oil_preds = test_bin_preds[no_oil_idx]
    no_oil_fp = int(np.count_nonzero(no_oil_preds == 1))

    # Lookalike subset
    lookalike_preds = test_bin_preds[lookalike_idx]
    lookalike_fp = int(np.count_nonzero(lookalike_preds == 1))
    lookalike_tot = int(lookalike_preds.size)
    lookalike_img_count = sum(1 for p in lookalike_preds if np.any(p == 1))

    print("\n--- Subset Specific Confusion Breakdown ---")
    print(f"Oil Rasters (150)       : TP={oil_tp:,}, FP={oil_fp:,}, FN={oil_fn:,}, TN={oil_tn:,}")
    print(f"No-Oil Rasters (150)    : FP={no_oil_fp:,} pixels")
    print(f"Lookalike Rasters (150) : FP={lookalike_fp:,} pixels ({lookalike_img_count}/150 rasters affected)")

    # Exact FPR Formula
    fpr_pixel = float(lookalike_fp / lookalike_tot * 100.0)
    print(f"\nExact Lookalike FPR (Pixel-level): {fpr_pixel:.4f}% ({lookalike_fp:,} / {lookalike_tot:,} pixels)")

    # Real metric calculation for Oil Class
    real_iou = float(test_tp / (test_tp + test_fp + test_fn)) if (test_tp + test_fp + test_fn) > 0 else 0.0
    real_dice = float((2.0 * test_tp) / (2.0 * test_tp + test_fp + test_fn)) if (2.0 * test_tp + test_fp + test_fn) > 0 else 0.0
    real_prec = float(test_tp / (test_tp + test_fp)) if (test_tp + test_fp) > 0 else 0.0
    real_rec = float(test_tp / (test_tp + test_fn)) if (test_tp + test_fn) > 0 else 0.0
    real_f1 = float((2.0 * real_prec * real_rec) / (real_prec + real_rec)) if (real_prec + real_rec) > 0 else 0.0

    print(f"\n--- True Pixel-Level Segmentation Metrics (Overall Test Set) ---")
    print(f"  Pixel-Level IoU      : {real_iou:.6f}")
    print(f"  Pixel-Level Dice     : {real_dice:.6f}")
    print(f"  Pixel-Level Precision: {real_prec:.6f}")
    print(f"  Pixel-Level Recall   : {real_rec:.6f}")
    print(f"  Pixel-Level F1-Score : {real_f1:.6f}")

    # 4. Audit Current Scene Confidence Score Semantics
    latest_tif = oil_detection_service.resolve_latest_phase1_geotiff()
    res = oil_detection_service.run_detection(str(latest_tif))
    
    with rasterio.open(latest_tif) as src:
        raw_sar = src.read(1)
        valid = raw_sar[np.isfinite(raw_sar) & (raw_sar != -9999.0)]
        
    print("\n--- 4. Current Scene Input & Output Audit ---")
    print(f"Target Raster: {latest_tif.name}")
    print(f"Raw Input dB Stats:")
    print(f"  min={valid.min():.4f}, max={valid.max():.4f}, mean={valid.mean():.4f}, p2={np.percentile(valid,2):.4f}, p98={np.percentile(valid,98):.4f}")
    print(f"Decibel Distribution Breakdown:")
    print(f"  <-32 dB: {np.mean(valid < -32.0)*100:.2f}% | [-32, 0] dB: {np.mean((valid >= -32.0) & (valid <= 0.0))*100:.2f}% | >0 dB: {np.mean(valid > 0.0)*100:.2f}%")
    print(f"Normalized Input Stats (via normalize_sar_db):")
    norm_pixels = res['compatibility']['normalized_stats']
    print(f"  min={norm_pixels['min']}, max={norm_pixels['max']}, mean={norm_pixels['mean']}, p2={norm_pixels['p2']}, p98={norm_pixels['p98']}")
    print(f"Model Inference Results:")
    print(f"  Predicted Oil Pixels: {res['class_distribution']['oil_spill_pixels']}")
    print(f"  Oil Pixel Percentage: {res['oil_pixel_percentage']}%")
    print(f"  Model Score / Confidence: {res['confidence']}")

if __name__ == "__main__":
    run_metric_audit()
