import os
import glob
import rasterio
import numpy as np
from app.services.sar_normalization import audit_db_clipping_gate, normalize_sar_db

print("=== OCEANTRACE AI — PHASE 2.4 MANDATORY PRE-TRAINING GATE CHECK ===")

p1_files = sorted(glob.glob("g:/SIH/oceantrace-ai/backend/data/output/*.tif"))
valid_tifs = [f for f in p1_files if not os.path.basename(f).startswith("sar_mask_") and not os.path.basename(f).startswith("spill_mask_") and not os.path.basename(f).startswith("test_")]

all_db_pixels = []
for p in valid_tifs:
    with rasterio.open(p) as src:
        arr = src.read(1)
        valid = arr[np.isfinite(arr) & (arr != -9999.0)]
        if valid.size > 0:
            all_db_pixels.append(valid)

if all_db_pixels:
    combined_db = np.concatenate(all_db_pixels)
    gate_results = audit_db_clipping_gate(combined_db)
    print("\n--- Gate Check Results on Physical Sentinel-1 SAR Dataset ---")
    print(f"Total Pixels Audited: {combined_db.size:,}")
    print(f"% Pixels below -32 dB : {gate_results['pct_below_m32_db']:.2f}%")
    print(f"% Pixels inside [-32, 0] dB: {gate_results['pct_inside_m32_0_db']:.2f}%")
    print(f"% Pixels above 0 dB  : {gate_results['pct_above_0_db']:.2f}%")
    print("Normalized Pixel Stats:")
    print(f"  Min : {gate_results['normalized_stats']['min']}")
    print(f"  Max : {gate_results['normalized_stats']['max']}")
    print(f"  Mean: {gate_results['normalized_stats']['mean']}")
    print(f"  p2  : {gate_results['normalized_stats']['p2']}")
    print(f"  p98 : {gate_results['normalized_stats']['p98']}")
    print(f"GATE PASSED STATUS  : {gate_results['gate_passed']}")
    
    if gate_results['gate_passed']:
        print("\nSUCCESS: Clipping level is acceptable (>= 90% inside [-32, 0] dB). PROCEED TO MODEL TRAINING.")
    else:
        print("\nWARNING: Clipping gate flag triggered!")
else:
    print("No physical SAR files found to audit.")
