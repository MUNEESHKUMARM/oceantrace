import os
import urllib.request
import py7zr
import rasterio
import numpy as np

mask_urls = {
    "Oil_Spill_mask": "https://zenodo.org/api/records/8346860/files/01_Train_Val_Oil_Spill_mask.7z/content",
    "No_Oil_mask": "https://zenodo.org/api/records/8253899/files/01_Train_Val_No_Oil_mask.7z/content",
    "Lookalike_mask": "https://zenodo.org/api/records/8253899/files/01_Train_Val_Lookalike_mask.7z/content"
}

dest_dir = "g:/SIH/oceantrace-ai/backend/data/dataset_audit/masks"
os.makedirs(dest_dir, exist_ok=True)

req_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for key, url in mask_urls.items():
    archive_path = os.path.join(dest_dir, f"{key}.7z")
    extract_dir = os.path.join(dest_dir, key)
    
    if not os.path.exists(archive_path):
        print(f"Downloading {key}...")
        req = urllib.request.Request(url, headers=req_headers)
        with urllib.request.urlopen(req) as resp, open(archive_path, 'wb') as out_file:
            out_file.write(resp.read())
        print(f"Downloaded {key} ({os.path.getsize(archive_path)} bytes)")
    else:
        print(f"{archive_path} already exists ({os.path.getsize(archive_path)} bytes)")
        
    if not os.path.exists(extract_dir):
        print(f"Extracting {archive_path}...")
        with py7zr.SevenZipFile(archive_path, mode='r') as z:
            z.extractall(path=extract_dir)
        print(f"Extracted {key}")

print("\n--- Auditing Extracted Masks ---")
for key in mask_urls.keys():
    extract_dir = os.path.join(dest_dir, key)
    all_tifs = []
    for root, _, files in os.walk(extract_dir):
        for f in files:
            if f.endswith('.tif') or f.endswith('.png'):
                all_tifs.append(os.path.join(root, f))
    
    print(f"\nMask Group: {key}")
    print(f"Total files found: {len(all_tifs)}")
    if len(all_tifs) > 0:
        sample_path = all_tifs[0]
        with rasterio.open(sample_path) as src:
            arr = src.read()
            print(f"Sample file: {os.path.basename(sample_path)}")
            print(f"Shape: {arr.shape}, dtype: {arr.dtype}, CRS: {src.crs}, transform: {src.transform}")
            unique_vals = np.unique(arr)
            print(f"Unique values in sample: {unique_vals}")
            
        # Check unique values across 50 random samples
        sample_indices = np.linspace(0, len(all_tifs)-1, min(50, len(all_tifs)), dtype=int)
        all_uniques = set()
        non_zero_counts = []
        for idx in sample_indices:
            with rasterio.open(all_tifs[idx]) as src:
                a = src.read()
                all_uniques.update(np.unique(a).tolist())
                non_zero_counts.append(np.count_nonzero(a))
        print(f"Unique values across sample batch: {sorted(list(all_uniques))}")
        print(f"Mean non-zero (oil/lookalike) pixels per sample: {np.mean(non_zero_counts):.2f}")
