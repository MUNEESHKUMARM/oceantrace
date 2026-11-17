import os
import sys
import time
import urllib.request
from pathlib import Path
import numpy as np
import rasterio
import py7zr

DATASET_DIR = Path(__file__).resolve().parent / "data" / "dataset"
IMAGES_DIR = DATASET_DIR / "images"
MASKS_DIR = DATASET_DIR / "masks"

def download_with_headers(url: str, output_path: Path):
    """Downloads Zenodo archive file with custom user agent."""
    print(f"Downloading dataset archive from {url}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
    }

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response, open(output_path, 'wb') as out_file:
        total_size = int(response.headers.get('content-length', 0))
        bytes_downloaded = 0
        chunk_size = 1024 * 1024 * 2  # 2MB chunks

        start_time = time.time()
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            bytes_downloaded += len(chunk)
            elapsed = time.time() - start_time
            speed_mb = (bytes_downloaded / (1024 * 1024)) / elapsed if elapsed > 0 else 0
            if total_size > 0:
                percent = (bytes_downloaded / total_size) * 100
                print(f"\rProgress: {bytes_downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB ({percent:.1f}%) | {speed_mb:.1f} MB/s", end="")
            else:
                print(f"\rDownloaded: {bytes_downloaded / (1024*1024):.1f} MB | {speed_mb:.1f} MB/s", end="")
        print("\nDownload complete!")

def run_pipeline():
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    MASKS_DIR.mkdir(parents=True, exist_ok=True)

    # Zenodo Part III Archive URL (9.18 GB containing 150 test Sentinel-1 SAR images and ground truth masks)
    archive_url = "https://zenodo.org/api/records/13761290/files/02_Test_images_and_ground_truth.7z/content"
    archive_path = DATASET_DIR / "02_Test_images_and_ground_truth.7z"

    # Step 1: Check existing files
    existing_images = list(IMAGES_DIR.rglob("*.tif")) + list(IMAGES_DIR.rglob("*.tiff")) + list(IMAGES_DIR.rglob("*.png"))
    existing_masks = list(MASKS_DIR.rglob("*.tif")) + list(MASKS_DIR.rglob("*.tiff")) + list(MASKS_DIR.rglob("*.png"))

    if len(existing_images) == 0 or len(existing_masks) == 0:
        if not archive_path.exists() or archive_path.stat().st_size < 1000000:
            print("Downloading Zenodo Part III dataset archive (9.18 GB)...")
            try:
                download_with_headers(archive_url, archive_path)
            except Exception as e:
                print(f"\nDownload error: {e}")

        if archive_path.exists():
            print(f"Extracting {archive_path.name}...")
            try:
                with py7zr.SevenZipFile(archive_path, mode='r') as z:
                    z.extractall(path=DATASET_DIR)
                print("Extraction completed!")
            except Exception as e:
                print(f"Extraction error: {e}")

    # Step 2: Audit extracted dataset
    print("\n=======================================================================")
    print("PHASE 2 REAL DATASET AUDIT & AUDIT METRICS REPORT")
    print("=======================================================================\n")

    all_tifs = list(DATASET_DIR.rglob("*.tif")) + list(DATASET_DIR.rglob("*.tiff")) + list(DATASET_DIR.rglob("*.png"))
    print(f"Dataset Location: {DATASET_DIR}")
    print(f"Total Raster/Mask Files Discovered: {len(all_tifs)}")

    img_files = []
    mask_files = []

    for f in all_tifs:
        f_lower = str(f).lower()
        if "mask" in f_lower or "ground_truth" in f_lower or "gt" in f_lower:
            mask_files.append(f)
        else:
            img_files.append(f)

    print(f"Identified Images: {len(img_files)}")
    print(f"Identified Masks:  {len(mask_files)}")

    if len(img_files) == 0 or len(mask_files) == 0:
        print("\n=======================================================================")
        print("PHASE 2 BLOCKED — DATASET ISSUE")
        print("EXACT REASON: No Sentinel-1 SAR image/mask file pairs could be extracted or found in dataset directory.")
        print("=======================================================================\n")
        return False

    # Match pairs by filename stem or index
    img_dict = {f.name.lower().replace("_mask", "").replace("mask_", "").replace("_gt", ""): f for f in img_files}
    mask_dict = {f.name.lower().replace("_mask", "").replace("mask_", "").replace("_gt", ""): f for f in mask_files}

    matched_keys = sorted(list(set(img_dict.keys()).intersection(set(mask_dict.keys()))))
    print(f"Matched Image/Mask Pairs: {len(matched_keys)} / {len(img_files)}")

    total_valid_pairs = 0
    corrupted_count = 0
    unique_mask_values = set()
    total_bg_pixels = 0
    total_oil_pixels = 0
    total_other_pixels = 0
    nan_inf_count = 0

    img_shapes = set()
    mask_shapes = set()
    formats = set()

    for key in matched_keys:
        ip = img_dict[key]
        mp = mask_dict[key]

        try:
            with rasterio.open(ip) as s_img:
                arr_img = s_img.read(1)
                img_shapes.add(arr_img.shape)
                formats.add(s_img.driver)

            with rasterio.open(mp) as s_mask:
                arr_mask = s_mask.read(1)
                mask_shapes.add(arr_mask.shape)

            if arr_img.shape != arr_mask.shape:
                corrupted_count += 1
                continue

            if not np.all(np.isfinite(arr_img)):
                nan_inf_count += 1

            uniques = np.unique(arr_mask)
            unique_mask_values.update(uniques.tolist())

            bg_pixels = int(np.count_nonzero(arr_mask == 0))
            oil_pixels = int(np.count_nonzero(arr_mask == 1))
            other_px = int(arr_mask.size - bg_pixels - oil_pixels)

            total_bg_pixels += bg_pixels
            total_oil_pixels += oil_pixels
            total_other_pixels += other_px
            total_valid_pairs += 1

        except Exception as e:
            corrupted_count += 1

    total_px = total_bg_pixels + total_oil_pixels + total_other_pixels
    bg_pct = (total_bg_pixels / total_px * 100) if total_px > 0 else 0
    oil_pct = (total_oil_pixels / total_px * 100) if total_px > 0 else 0

    print("\n-----------------------------------------------------------------------")
    print("DETAILED DATASET AUDIT STATISTICS")
    print("-----------------------------------------------------------------------")
    print(f"  Exact Dataset Location:   {DATASET_DIR.resolve()}")
    print(f"  Number of Images:        {len(img_files)}")
    print(f"  Number of Masks:         {len(mask_files)}")
    print(f"  Valid Image/Mask Pairs:  {total_valid_pairs}")
    print(f"  Corrupted/Invalid Files: {corrupted_count}")
    print(f"  Image Dimensions:        {list(img_shapes)}")
    print(f"  Mask Dimensions:         {list(mask_shapes)}")
    print(f"  File Formats:            {list(formats)}")
    print(f"  Unique Mask Values:      {sorted(list(unique_mask_values))}")
    print(f"  NaN / Inf Occurrences:   {nan_inf_count}")
    print(f"  Class Pixel Distribution:")
    print(f"    - Background (0): {total_bg_pixels} pixels ({bg_pct:.2f}%)")
    print(f"    - Oil Spill  (1): {total_oil_pixels} pixels ({oil_pct:.2f}%)")
    if total_other_pixels > 0:
        print(f"    - Other Classes:   {total_other_pixels} pixels ({total_other_pixels / total_px * 100:.2f}%)")
    print("-----------------------------------------------------------------------\n")

    is_binary = (set(unique_mask_values) <= {0, 1})
    print(f"Binary Segmentation Support (0=Background, 1=Oil Spill): {is_binary}")

    if total_valid_pairs > 0 and is_binary:
        print("\n=======================================================================")
        print("DATASET READY FOR TRAINING")
        print("=======================================================================\n")
        return True
    else:
        print("\n=======================================================================")
        print("PHASE 2 BLOCKED — DATASET ISSUE")
        if total_valid_pairs == 0:
            print("EXACT REASON: 0 valid image/mask pairs found or download incomplete.")
        elif not is_binary:
            print(f"EXACT REASON: Unique mask values {sorted(list(unique_mask_values))} contain non-binary labels.")
        print("=======================================================================\n")
        return False

if __name__ == "__main__":
    run_pipeline()
