import os
import glob
import rasterio
import numpy as np

print("=== Auditing Existing 23 Files in backend/data/dataset/images ===")
img_files = sorted(glob.glob("g:/SIH/oceantrace-ai/backend/data/dataset/images/*.tif"))
print(f"Total TIF files in local dataset: {len(img_files)}")

stats = []
for f in img_files:
    with rasterio.open(f) as src:
        arr = src.read()
        amin, amax, amean = np.min(arr), np.max(arr), np.mean(arr)
        p2, p98 = np.percentile(arr, 2), np.percentile(arr, 98)
        pct_neg30 = np.mean(arr == -30.0) * 100
        stats.append({
            'file': os.path.basename(f),
            'shape': arr.shape,
            'dtype': str(arr.dtype),
            'min': amin,
            'max': amax,
            'mean': amean,
            'p2': p2,
            'p98': p98,
            'pct_neg30': pct_neg30
        })

print("\nSummary of Local 23 Images:")
print(f"{'Filename':<12} {'Shape':<16} {'Min':<10} {'Max':<10} {'Mean':<10} {'p2':<10} {'p98':<10} {'%-30dB':<10}")
for s in stats[:10]:
    print(f"{s['file']:<12} {str(s['shape']):<16} {s['min']:<10.2f} {s['max']:<10.2f} {s['mean']:<10.2f} {s['p2']:<10.2f} {s['p98']:<10.2f} {s['pct_neg30']:<10.2f}%")

avg_min = np.mean([s['min'] for s in stats])
avg_max = np.mean([s['max'] for s in stats])
avg_mean = np.mean([s['mean'] for s in stats])
avg_pct_neg30 = np.mean([s['pct_neg30'] for s in stats])
print(f"\nAggregate Local 23 Stats: Avg Min={avg_min:.2f}, Avg Max={avg_max:.2f}, Avg Mean={avg_mean:.2f}, Avg % at -30dB={avg_pct_neg30:.2f}%")
