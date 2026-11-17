import os
import sys
import time
import urllib.request
import zipfile
from pathlib import Path
import numpy as np
import rasterio

DATASET_DIR = Path(__file__).resolve().parent / "data" / "dataset"
IMAGES_DIR = DATASET_DIR / "images"
MASKS_DIR = DATASET_DIR / "masks"

def download_file(url: str, output_path: Path):
    """Downloads a file with progress logging."""
    print(f"Downloading from {url} to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response, open(output_path, 'wb') as out_file:
        total_size = int(response.headers.get('content-length', 0))
        bytes_downloaded = 0
        chunk_size = 1024 * 1024  # 1MB chunks
        
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            bytes_downloaded += len(chunk)
            if total_size > 0:
                percent = (bytes_downloaded / total_size) * 100
                print(f"\rProgress: {bytes_downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB ({percent:.1f}%)", end="")
        print("\nDownload complete.")

def acquire_dataset():
    """Acquires Zenodo Sentinel-1 SAR Oil Spill dataset files if not already present."""
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    MASKS_DIR.mkdir(parents=True, exist_ok=True)

    # Check if images and masks already exist
    existing_images = list(IMAGES_DIR.glob("*.*"))
    existing_masks = list(MASKS_DIR.glob("*.*"))

    if len(existing_images) > 0 and len(existing_masks) > 0:
        print(f"Dataset already present in {DATASET_DIR}: {len(existing_images)} images, {len(existing_masks)} masks.")
        return

    print("Acquiring Zenodo Sentinel-1 SAR Oil Spill dataset archives...")
    # Zenodo Part I download URLs (7z archives)
    images_url = "https://zenodo.org/records/8346860/files/01_Train_Val_Oil_Spill_images.7z?download=1"
    masks_url = "https://zenodo.org/records/8346860/files/01_Train_Val_Oil_Spill_mask.7z?download=1"

    img_archive = DATASET_DIR / "01_Train_Val_Oil_Spill_images.7z"
    mask_archive = DATASET_DIR / "01_Train_Val_Oil_Spill_mask.7z"

    try:
        import py7zr
        if not img_archive.exists():
            download_file(images_url, img_archive)
        if not mask_archive.exists():
            download_file(masks_url, mask_archive)

        print("Extracting image archive...")
        with py7zr.SevenZipFile(img_archive, mode='r') as archive:
            archive.extractall(path=IMAGES_DIR)

        print("Extracting mask archive...")
        with py7zr.SevenZipFile(mask_archive, mode='r') as archive:
            archive.extractall(path=MASKS_DIR)

    except Exception as e:
        print(f"Archive download/extract error: {e}")
        print("Fallback: Checking if dataset files are in nested directories or manual extraction...")

def audit_dataset():
    """Performs strict validation and audit of dataset images and ground-truth masks."""
    print("\n=======================================================================")
    print("PHASE 2 AUTOMATED DATASET AUDIT")
    print("=======================================================================\n")

    # Locate image and mask files
    image_files = sorted(list(IMAGES_DIR.rglob("*.tif")) + list(IMAGES_DIR.rglob("*.tiff")) + list(IMAGES_DIR.rglob("*.png")) + list(IMAGES_DIR.rglob("*.jpg")))
    mask_files = sorted(list(MASKS_DIR.rglob("*.tif")) + list(MASKS_DIR.rglob("*.tiff")) + list(MASKS_DIR.rglob("*.png")) + list(MASKS_DIR.rglob("*.jpg")))

    print(f"Found {len(image_files)} image files and {len(mask_files)} mask files in {DATASET_DIR}.\n")

    if len(image_files) == 0 or len(mask_files) == 0:
        print("[AUDIT FAIL] DATASET ERROR: Image or mask folder is empty.")
        print("EXACT REASON: No Sentinel-1 SAR raster image or mask files found.")
        return False

    # Pair matching check
    image_dict = {f.stem.lower(): f for f in image_files}
    mask_dict = {f.stem.lower(): f for f in mask_files}

    matched_keys = sorted(list(set(image_dict.keys()).intersection(set(mask_dict.keys()))))
    print(f"Paired Image/Mask Matched Keys: {len(matched_keys)} / {len(image_files)}")

    if len(matched_keys) == 0:
        print("[AUDIT FAIL] DATASET ERROR: 0 paired image/mask files matched by filename stem.")
        print("EXACT REASON: Mismatch between image filenames and mask filenames.")
        return False

    # Detailed statistics
    total_valid_pairs = 0
    corrupted_files = 0
    unique_mask_values = set()
    total_bg_pixels = 0
    total_oil_pixels = 0
    other_pixels = 0
    nan_inf_count = 0

    img_shapes = set()
    mask_shapes = set()
    file_formats = set()

    print("Auditing image/mask pixel integrity...")
    for idx, key in enumerate(matched_keys):
        img_path = image_dict[key]
        mask_path = mask_dict[key]

        try:
            # Read Image
            with rasterio.open(img_path) as src_img:
                img_data = src_img.read(1)
                img_shapes.add(img_data.shape)
                file_formats.add(src_img.driver)

            # Read Mask
            with rasterio.open(mask_path) as src_mask:
                mask_data = src_mask.read(1)
                mask_shapes.add(mask_data.shape)

            if img_data.shape != mask_data.shape:
                print(f"  ! Dimension Mismatch for {key}: Image {img_data.shape} vs Mask {mask_data.shape}")
                corrupted_files += 1
                continue

            # Check NaNs / Infs
            if not np.all(np.isfinite(img_data)):
                nan_inf_count += 1

            # Mask Values
            uniques = np.unique(mask_data)
            unique_mask_values.update(uniques.tolist())

            # Pixel distribution
            bg_cnt = int(np.count_nonzero(mask_data == 0))
            oil_cnt = int(np.count_nonzero(mask_data == 1))
            oth_cnt = int(mask_data.size - bg_cnt - oil_cnt)

            total_bg_pixels += bg_cnt
            total_oil_pixels += oil_cnt
            other_pixels += oth_cnt

            total_valid_pairs += 1

        except Exception as e:
            print(f"  ! Error reading pair {key}: {e}")
            corrupted_files += 1

    total_pixels = total_bg_pixels + total_oil_pixels + other_pixels
    bg_pct = (total_bg_pixels / total_pixels * 100) if total_pixels > 0 else 0
    oil_pct = (total_oil_pixels / total_pixels * 100) if total_pixels > 0 else 0

    print("\n-----------------------------------------------------------------------")
    print("DATASET AUDIT REPORT")
    print("-----------------------------------------------------------------------")
    print(f"  Dataset Directory:     {DATASET_DIR}")
    print(f"  Total Images Discovered: {len(image_files)}")
    print(f"  Total Masks Discovered:  {len(mask_files)}")
    print(f"  Valid Image/Mask Pairs:  {total_valid_pairs}")
    print(f"  Corrupted/Mismatch Files: {corrupted_files}")
    print(f"  Image Dimensions:       {list(img_shapes)}")
    print(f"  Mask Dimensions:        {list(mask_shapes)}")
    print(f"  File Formats:           {list(file_formats)}")
    print(f"  Unique Mask Values:     {sorted(list(unique_mask_values))}")
    print(f"  NaN / Inf Occurrences:  {nan_inf_count}")
    print(f"  Pixel Class Distribution:")
    print(f"    - Background (0): {total_bg_pixels} pixels ({bg_pct:.2f}%)")
    print(f"    - Oil Spill  (1): {total_oil_pixels} pixels ({oil_pct:.2f}%)")
    if other_pixels > 0:
        print(f"    - Other Classes:   {other_pixels} pixels ({other_pixels / total_pixels * 100:.2f}%)")
    print("-----------------------------------------------------------------------\n")

    # Binary Segmentation Check
    is_binary = (set(unique_mask_values) <= {0, 1})
    print(f"Binary Segmentation Support (0=Background, 1=Oil): {is_binary}")

    if total_valid_pairs > 0 and is_binary:
        print("\n=======================================================================")
        print("DATASET READY FOR TRAINING")
        print("=======================================================================\n")
        return True
    else:
        print("\n=======================================================================")
        print(f"[AUDIT FAIL] DATASET INSUFFICIENT FOR TRAINING")
        if total_valid_pairs == 0:
            print("EXACT REASON: 0 valid image/mask pairs found.")
        elif not is_binary:
            print(f"EXACT REASON: Mask values {sorted(list(unique_mask_values))} do not match binary schema (0, 1).")
        print("=======================================================================\n")
        return False

if __name__ == "__main__":
    acquire_dataset()
    success = audit_dataset()
    sys.exit(0 if success else 1)
