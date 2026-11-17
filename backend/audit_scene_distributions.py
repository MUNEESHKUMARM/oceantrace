import os
import glob
import rasterio
import numpy as np

p1_files = sorted(glob.glob("g:/SIH/oceantrace-ai/backend/data/output/*.tif"))
print(f"Total TIF files: {len(p1_files)}")

for p in p1_files:
    fname = os.path.basename(p)
    if not fname.startswith("sar_mask_") and not fname.startswith("spill_mask_") and not fname.startswith("test_"):
        with rasterio.open(p) as src:
            arr = src.read(1)
            valid = arr[np.isfinite(arr) & (arr != -9999)]
            if valid.size > 0:
                below_m32 = float(np.mean(valid < -32.0) * 100.0)
                btw_m32_0 = float(np.mean((valid >= -32.0) & (valid <= 0.0)) * 100.0)
                above_0 = float(np.mean(valid > 0.0) * 100.0)
                p2 = float(np.percentile(valid, 2.0))
                p98 = float(np.percentile(valid, 98.0))
                print(f"{fname:<45} | min={valid.min():.2f} max={valid.max():.2f} mean={valid.mean():.2f} p2={p2:.2f} p98={p98:.2f} | [-32,0]: {btw_m32_0:.1f}% >0dB: {above_0:.1f}%")
