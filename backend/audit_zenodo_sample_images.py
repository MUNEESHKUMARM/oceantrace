import os
import urllib.request
import py7zr
import rasterio
import numpy as np

dest_dir = "g:/SIH/oceantrace-ai/backend/data/dataset_audit/sample_images"
os.makedirs(dest_dir, exist_ok=True)

url = "https://zenodo.org/api/records/8346860/files/01_Train_Val_Oil_Spill_images.7z/content"
part1_7z = os.path.join(dest_dir, "Oil_Spill_images_partial.7z")

req_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# Download first 150 MB to get enough uncompressed files from the 7z archive
download_bytes = 150 * 1024 * 1024
print(f"Downloading first {download_bytes/(1024*1024):.0f} MB of 01_Train_Val_Oil_Spill_images.7z...")
req = urllib.request.Request(url, headers={**req_headers, 'Range': f'bytes=0-{download_bytes-1}'})

with urllib.request.urlopen(req) as resp, open(part1_7z, 'wb') as out_file:
    out_file.write(resp.read())
print(f"Downloaded partial 7z ({os.path.getsize(part1_7z)} bytes)")

# Try inspecting py7zr or py7zr extraction
try:
    with py7zr.SevenZipFile(part1_7z, mode='r') as z:
        names = z.getnames()
        print(f"Total files in partial archive index: {len(names)}")
        print("First 10 files:", names[:10])
        
        # Try extracting first available complete file
        for name in names[:5]:
            try:
                z.extract(targets=[name], path=dest_dir)
                extracted_file = os.path.join(dest_dir, name)
                if os.path.exists(extracted_file) and os.path.isfile(extracted_file):
                    print(f"\nSuccessfully extracted: {name} (size: {os.path.getsize(extracted_file)} bytes)")
                    with rasterio.open(extracted_file) as src:
                        arr = src.read()
                        print(f"Rasterio Shape: {arr.shape}")
                        print(f"Dtype: {arr.dtype}")
                        print(f"CRS: {src.crs}")
                        print(f"Transform: {src.transform}")
                        print(f"Min: {np.min(arr):.4f}")
                        print(f"Max: {np.max(arr):.4f}")
                        print(f"Mean: {np.mean(arr):.4f}")
                        print(f"p1: {np.percentile(arr, 1):.4f}, p2: {np.percentile(arr, 2):.4f}, p50: {np.percentile(arr, 50):.4f}, p98: {np.percentile(arr, 98):.4f}, p99: {np.percentile(arr, 99):.4f}")
                        print(f"Finite %: {np.mean(np.isfinite(arr))*100:.2f}%")
                        print(f"Zero/Constant %: {np.mean(arr == 0)*100:.2f}%")
            except Exception as ex:
                print(f"Extraction error for {name}: {ex}")
except Exception as e:
    print(f"7z partial read error: {e}")
