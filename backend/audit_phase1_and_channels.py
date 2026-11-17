import os
import glob
import rasterio
import numpy as np

print("=== 1. Inspecting Dataset Raster Channels ===")
# Check extracted masks / sample files or local tifs if any
sample_files = glob.glob("g:/SIH/oceantrace-ai/backend/data/dataset_audit/sample_images/**/*.tif", recursive=True)
if not sample_files:
    sample_files = glob.glob("g:/SIH/oceantrace-ai/backend/data/dataset_audit/**/*.tif", recursive=True)

print("Found audit tif files:", sample_files[:5])

# Also check Phase 1 output rasters in backend/data/output
print("\n=== 2. Inspecting Phase 1 Output Rasters in backend/data/output ===")
p1_files = sorted(glob.glob("g:/SIH/oceantrace-ai/backend/data/output/*.tif"))
print(f"Total TIF files in Phase 1 output dir: {len(p1_files)}")
for p1 in p1_files:
    if not os.path.basename(p1).startswith("sar_mask_") and not os.path.basename(p1).startswith("sar_confidence_"):
        with rasterio.open(p1) as src:
            print(f"Phase 1 GeoTIFF: {os.path.basename(p1)}")
            print(f"  Bands count: {src.count}")
            print(f"  Shape: ({src.count}, {src.height}, {src.width})")
            print(f"  Dtype: {src.dtypes}")
            print(f"  CRS: {src.crs}")
            for b in range(1, src.count + 1):
                arr = src.read(b)
                valid = arr[np.isfinite(arr) & (arr != -9999)]
                if valid.size > 0:
                    print(f"  Band {b}: min={valid.min():.4f}, max={valid.max():.4f}, mean={valid.mean():.4f}, std={valid.std():.4f}")
                else:
                    print(f"  Band {b}: no valid pixels")
