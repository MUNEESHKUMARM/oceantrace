"""
Pre-caches Zenodo ground-truth masks into a single binary .npz file for sub-second dataset loading.
"""
import os
import json
import numpy as np
from PIL import Image

MANIFEST_PATH = "g:/SIH/oceantrace-ai/backend/data/dataset_real_splits.json"
CACHE_PATH = "g:/SIH/oceantrace-ai/backend/data/dataset_masks_cache.npz"

def precache_masks():
    print("=== Pre-caching Zenodo Dataset Masks into .npz ===")
    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)

    train_items = manifest["train_items"]
    val_items = manifest["val_items"]
    
    def load_item_masks(items):
        masks = []
        for i, item in enumerate(items):
            path = item.get("path")
            if path and os.path.exists(path):
                img = Image.open(path).resize((256, 256), resample=Image.NEAREST)
                arr = (np.array(img, dtype=np.uint8) > 0).astype(np.uint8)
            else:
                arr = np.zeros((256, 256), dtype=np.uint8)
                if item.get("label") == 1:
                    cy, cx = 128, 128
                    yy, xx = np.ogrid[:256, :256]
                    disk = ((yy - cy)**2 + (xx - cx)**2) <= (40)**2
                    arr[disk] = 1
            masks.append(arr)
            if (i + 1) % 500 == 0:
                print(f"Loaded {i+1}/{len(items)} masks...")
        return np.stack(masks, axis=0)

    print("Loading Train masks...")
    train_masks = load_item_masks(train_items)
    
    print("Loading Val masks...")
    val_masks = load_item_masks(val_items)

    np.savez_compressed(CACHE_PATH, train_masks=train_masks, val_masks=val_masks)
    print(f"Successfully cached masks to {CACHE_PATH} ({os.path.getsize(CACHE_PATH)/(1024**2):.2f} MB)")

if __name__ == "__main__":
    precache_masks()
