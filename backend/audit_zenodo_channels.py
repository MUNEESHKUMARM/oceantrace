import os
import glob
import rasterio
import numpy as np

print("=== Auditing Image TIF Files specifically ===")
img_files = glob.glob("g:/SIH/oceantrace-ai/backend/data/dataset/images/*.tif")
print(f"Found {len(img_files)} image TIFs in local dataset dir")

for p in img_files[:5]:
    with rasterio.open(p) as src:
        print(f"\nFile: {os.path.basename(p)}")
        print(f"  Count (Bands): {src.count}")
        print(f"  Shape: ({src.count}, {src.height}, {src.width})")
        print(f"  Dtype: {src.dtypes}")
        for b in range(1, src.count + 1):
            arr = src.read(b)
            valid = arr[np.isfinite(arr) & (arr != -9999)]
            if valid.size > 0:
                print(f"  Band {b}: min={valid.min():.4f}, max={valid.max():.4f}, mean={valid.mean():.4f}, std={valid.std():.4f}")
