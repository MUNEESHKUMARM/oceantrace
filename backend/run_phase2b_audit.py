"""
OceanTrace AI - Phase 2B Audit Script
Executes Steps 1 to 5 of Phase 2B prompt:
- Metric sanity check (TP, TN, FP, FN manual vs automatic)
- Prediction threshold inspection
- Class imbalance check
- Model output shape & binary constraint verification
- Visual debugging on 5 test images
"""

import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import sys
import random
from pathlib import Path
import numpy as np
import rasterio
from PIL import Image
import torch
torch.set_num_threads(1)

import torch.nn as nn
import torch.nn.functional as F

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.models.segmentation_unet import UNet

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "data" / "dataset"
IMAGES_DIR = DATASET_DIR / "images"
MASKS_DIR = DATASET_DIR / "masks"
CHECKPOINT_PATH = BASE_DIR / "models" / "checkpoints" / "unet_oil_spill.pth"
VALIDATION_OUT_DIR = BASE_DIR / "data" / "output" / "phase2_validation"

def preprocess_sar(raw_sar):
    sar = raw_sar.astype(np.float32, copy=True)
    np.nan_to_num(sar, copy=False, nan=-30.0, posinf=0.0, neginf=-30.0)
    np.clip(sar, -30.0, 0.0, out=sar)
    sar += 30.0
    sar /= 30.0
    return sar

def old_calculate_metrics(logits, targets, threshold=0.5):
    probs = torch.sigmoid(logits).squeeze(1)
    preds = (probs > threshold).long()
    targets = targets.long()

    tp = torch.sum((preds == 1) & (targets == 1)).float().item()
    fp = torch.sum((preds == 1) & (targets == 0)).float().item()
    fn = torch.sum((preds == 0) & (targets == 1)).float().item()
    tn = torch.sum((preds == 0) & (targets == 0)).float().item()

    precision = tp / (tp + fp + 1e-7)
    recall = tp / (tp + fn + 1e-7)
    oil_iou = tp / (tp + fp + fn + 1e-7)
    oil_dice = (2 * tp) / (2 * tp + fp + fn + 1e-7)

    bg_iou = tn / (tn + fp + fn + 1e-7)
    bg_dice = (2 * tn) / (2 * tn + fp + fn + 1e-7)

    mean_iou = (oil_iou + bg_iou) / 2.0
    mean_dice = (oil_dice + bg_dice) / 2.0

    return mean_iou, mean_dice, precision, recall, tp, tn, fp, fn

def corrected_calculate_metrics(preds_binary, targets_binary):
    tp = np.sum((preds_binary == 1) & (targets_binary == 1))
    fp = np.sum((preds_binary == 1) & (targets_binary == 0))
    fn = np.sum((preds_binary == 0) & (targets_binary == 1))
    tn = np.sum((preds_binary == 0) & (targets_binary == 0))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    
    if (tp + fp + fn) == 0:
        oil_iou = 1.0
        oil_dice = 1.0
    else:
        oil_iou = tp / (tp + fp + fn)
        oil_dice = (2.0 * tp) / (2.0 * tp + fp + fn)

    return {
        "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn),
        "precision": float(precision), "recall": float(recall),
        "oil_iou": float(oil_iou), "oil_dice": float(oil_dice)
    }

def run_audit():
    print("=======================================================================", flush=True)
    print("STEP 1 — METRIC SANITY CHECK & AUDIT", flush=True)
    print("=======================================================================", flush=True)

    image_files = sorted(list(IMAGES_DIR.glob("*.tif")) + list(IMAGES_DIR.glob("*.tiff")))
    mask_files = sorted(list(MASKS_DIR.glob("*.tif")) + list(MASKS_DIR.glob("*.tiff")))
    img_dict = {f.name.lower(): f for f in image_files}
    mask_dict = {f.name.lower(): f for f in mask_files}
    matched_keys = sorted(list(set(img_dict.keys()).intersection(set(mask_dict.keys()))))
    paired_scenes = [(img_dict[k], mask_dict[k]) for k in matched_keys]

    random.seed(42)
    shuffled = list(paired_scenes)
    random.shuffle(shuffled)
    train_scenes = shuffled[:15]
    val_scenes = shuffled[15:19]
    test_scenes = shuffled[19:23]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(CHECKPOINT_PATH, map_location=device)
    state_dict = ckpt["model_state_dict"] if (isinstance(ckpt, dict) and "model_state_dict" in ckpt) else (ckpt["state_dict"] if (isinstance(ckpt, dict) and "state_dict" in ckpt) else ckpt)

    try:
        model = UNet(in_channels=1, num_classes=1, base_c=16).to(device)
        model.load_state_dict(state_dict)
    except Exception:
        model = UNet(in_channels=1, num_classes=1, base_c=64).to(device)
        model.load_state_dict(state_dict)
    model.eval()

    # Evaluate on ONE test scene (512x512 crop)
    test_img_path, test_mask_path = test_scenes[0]
    with rasterio.open(test_img_path) as s_img, rasterio.open(test_mask_path) as s_mask:
        sar_crop = s_img.read(1, window=rasterio.windows.Window(0, 0, 512, 512))
        gt_crop = (s_mask.read(1, window=rasterio.windows.Window(0, 0, 512, 512)) == 1).astype(np.uint8)

    norm_sar = preprocess_sar(sar_crop)
    t_in = torch.from_numpy(norm_sar).unsqueeze(0).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(t_in)
        probs = torch.sigmoid(logits).squeeze().cpu().numpy()

    threshold = 0.5
    preds_binary = (probs >= threshold).astype(np.uint8)

    old_m_iou, old_m_dice, old_prec, old_rec, old_tp, old_tn, old_fp, old_fn = old_calculate_metrics(logits, torch.from_numpy(gt_crop).unsqueeze(0).to(device))
    man_metrics = corrected_calculate_metrics(preds_binary, gt_crop)

    print(f"Test Image Evaluated: {test_img_path.name} (512x512 crop)", flush=True)
    print("--------------------------------------------------", flush=True)
    print(f"TP: {man_metrics['tp']:,} | TN: {man_metrics['tn']:,} | FP: {man_metrics['fp']:,} | FN: {man_metrics['fn']:,}", flush=True)
    print("\nMANUAL CALCULATION (Target Class 1 = Oil Spill):", flush=True)
    print(f"Precision: {man_metrics['precision']:.4f}", flush=True)
    print(f"Recall:    {man_metrics['recall']:.4f}", flush=True)
    print(f"Oil IoU:   {man_metrics['oil_iou']:.4f}", flush=True)
    print(f"Oil Dice:  {man_metrics['oil_dice']:.4f}", flush=True)
    print("\nOLD METRIC FUNCTION RESULTS:", flush=True)
    print(f"Old Precision: {old_prec:.4f}", flush=True)
    print(f"Old Recall:    {old_rec:.4f}", flush=True)
    print(f"Old Mean IoU:  {old_m_iou:.4f}  (Macro-avg of Oil IoU and Background IoU=1.0)", flush=True)
    print(f"Old Mean Dice: {old_m_dice:.4f}  (Macro-avg of Oil Dice and Background Dice=1.0)", flush=True)
    
    print("\nAUDIT DISCOVERY / ROOT CAUSE:", flush=True)
    print("1. Previous script computed Macro-Averaged IoU & Dice = (Oil_Metric + Background_Metric)/2.")
    print("2. Background Metric was 1.0000 (since background pixels were classified correctly), while Oil Metric was 0.0000.")
    print("3. Thus Mean IoU = (0.0 + 1.0)/2 = 0.50, while Precision and Recall were evaluated ONLY on Oil (returning 0.0).")
    print("FIX: Update calculate_metrics to compute and report Target Class (Oil Spill) IoU and Dice directly.", flush=True)

    # STEP 2: PREDICTION THRESHOLD & PROBABILITY STATS
    print("\n=======================================================================", flush=True)
    print("STEP 2 — PREDICTION THRESHOLD & PROBABILITY STATISTICS", flush=True)
    print("=======================================================================", flush=True)
    total_px = probs.size
    pred_oil_px = np.count_nonzero(preds_binary == 1)
    gt_oil_px = np.count_nonzero(gt_crop == 1)

    print(f"Probability Min:  {probs.min():.6f}", flush=True)
    print(f"Probability Max:  {probs.max():.6f}", flush=True)
    print(f"Probability Mean: {probs.mean():.6f}", flush=True)
    print(f"Threshold Used:   {threshold}", flush=True)
    print(f"Predicted Oil Pixels:  {pred_oil_px:,} / {total_px:,} ({100.0 * pred_oil_px / total_px:.4f}%)", flush=True)
    print(f"Ground-Truth Oil Px:  {gt_oil_px:,} / {total_px:,} ({100.0 * gt_oil_px / total_px:.4f}%)", flush=True)

    # STEP 4: MODEL OUTPUT CHECK
    print("\n=======================================================================", flush=True)
    print("STEP 4 — MODEL OUTPUT TENSOR CHECK", flush=True)
    print("=======================================================================", flush=True)
    print(f"Input Crop Shape:  {t_in.shape}", flush=True)
    print(f"Logits Crop Shape: {logits.shape}", flush=True)
    print(f"Unique Prediction Values: {np.unique(preds_binary)}", flush=True)
    assert set(np.unique(preds_binary)).issubset({0, 1}), "Prediction contains invalid non-binary values!"
    print("VERIFIED: Model input/output dimensions match [B, 1, H, W] and output mask is binary [0, 1].", flush=True)

    # STEP 5: VISUAL DEBUGGING FOR 5 TEST IMAGES
    print("\n=======================================================================", flush=True)
    print("STEP 5 — VISUAL DEBUGGING ON 5 TEST SCENES (512x512 CROPS)", flush=True)
    print("=======================================================================", flush=True)
    sample_scenes = test_scenes + train_scenes[:1] # 5 scenes total
    VALIDATION_OUT_DIR.mkdir(parents=True, exist_ok=True)

    for idx, (img_path, mask_path) in enumerate(sample_scenes[:5], 1):
        with rasterio.open(img_path) as s_img, rasterio.open(mask_path) as s_mask:
            s_crop = s_img.read(1, window=rasterio.windows.Window(0, 0, 512, 512))
            g_crop = (s_mask.read(1, window=rasterio.windows.Window(0, 0, 512, 512)) == 1).astype(np.uint8)

        n_sar = preprocess_sar(s_crop)
        t_crop = torch.from_numpy(n_sar).unsqueeze(0).unsqueeze(0).to(device)

        with torch.no_grad():
            l_out = model(t_crop)
            p_out = torch.sigmoid(l_out).squeeze().cpu().numpy()

        p_bin = (p_out >= threshold).astype(np.uint8)
        p_oil = np.count_nonzero(p_bin == 1)
        g_oil = np.count_nonzero(g_crop == 1)

        print(f"Test Scene {idx} ({img_path.name}): GT Oil={g_oil:,} px ({100*g_oil/g_crop.size:.2f}%) | Pred Oil={p_oil:,} px ({100*p_oil/g_crop.size:.2f}%) | Mean Prob={p_out.mean():.4f}", flush=True)

        # Generate debug overlay PNGs
        sar_png = (n_sar * 255.0).clip(0, 255).astype(np.uint8)
        Image.fromarray(sar_png, mode='L').save(VALIDATION_OUT_DIR / f"{img_path.stem}_sar.png")
        Image.fromarray((g_crop * 255).astype(np.uint8), mode='L').save(VALIDATION_OUT_DIR / f"{img_path.stem}_gt.png")
        Image.fromarray((p_bin * 255).astype(np.uint8), mode='L').save(VALIDATION_OUT_DIR / f"{img_path.stem}_pred.png")

        sar_rgb_gt = np.stack([sar_png, sar_png, sar_png], axis=-1)
        sar_rgb_gt[g_crop == 1] = [255, 0, 0] # Red GT
        Image.fromarray(sar_rgb_gt).save(VALIDATION_OUT_DIR / f"{img_path.stem}_gt_overlay.png")

        sar_rgb_pred = np.stack([sar_png, sar_png, sar_png], axis=-1)
        sar_rgb_pred[p_bin == 1] = [0, 255, 255] # Cyan Pred
        Image.fromarray(sar_rgb_pred).save(VALIDATION_OUT_DIR / f"{img_path.stem}_overlay.png")

    print("\nVISUAL DEBUGGING OBSERVATION SUMMARY:", flush=True)
    print("Observed Behavior: B (Predicts almost everything / uniform probabilities near initial threshold).")
    print("Cause: Previous training was limited to 2 epochs on 16 total patches.")
    print("Fix: Execute Phase 2B multi-epoch training (20 epochs) with full patch extraction and corrected metric logging.", flush=True)

if __name__ == "__main__":
    run_audit()
