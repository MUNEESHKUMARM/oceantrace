"""
OceanTrace AI — Shared SAR Normalization Module (Phase 2.4)
Single source of truth for physical Sentinel-1 SAR dB preprocessing contract.
Used identically by train_unet.py, oil_detection_service.py, and evaluation scripts.
"""

import numpy as np

# Fixed Physical Normalization Contract Parameters
MIN_DB_BOUND = -32.0  # Decibel lower bound (-32 dB maps to 0.0)
MAX_DB_BOUND = 0.0    # Decibel upper bound (0 dB maps to 1.0)
DB_SPAN = 32.0        # Total decibel range (0.0 - (-32.0) = 32.0 dB)


def normalize_sar_db(raw_sar_db: np.ndarray) -> np.ndarray:
    """
    Applies the fixed physical Sentinel-1 SAR decibel normalization contract:
    1. Replaces NaN / -9999 / infinite non-valid values with MIN_DB_BOUND (-32.0 dB)
    2. Clips physical decibel values to [-32.0 dB, 0.0 dB]
    3. Linearly scales [-32.0 dB, 0.0 dB] to [0.0, 1.0]

    Formula:
        x_norm = clip((x_dB + 32.0) / 32.0, 0.0, 1.0)

    Mapping:
        -32.0 dB -> 0.0
        -16.0 dB -> 0.5
          0.0 dB -> 1.0
    """
    sar_clean = raw_sar_db.astype(np.float32, copy=True)
    
    # Handle non-finite / nodata values safely
    invalid_mask = ~np.isfinite(sar_clean) | (sar_clean == -9999.0)
    sar_clean[invalid_mask] = MIN_DB_BOUND

    # Clip to physical bounds [-32.0, 0.0] dB
    np.clip(sar_clean, MIN_DB_BOUND, MAX_DB_BOUND, out=sar_clean)

    # Scale linearly to [0.0, 1.0]
    norm_sar = (sar_clean - MIN_DB_BOUND) / DB_SPAN
    return norm_sar.astype(np.float32)


def audit_db_clipping_gate(sar_db_array: np.ndarray) -> dict:
    """
    Mandatory Pre-Training Gate Audit:
    Calculates clipping percentages and normalized pixel statistics over a training batch/dataset.
    """
    valid_mask = np.isfinite(sar_db_array) & (sar_db_array != -9999.0)
    if not np.any(valid_mask):
        raise ValueError("Pre-training gate failed: Input array contains 0 valid finite pixels.")

    valid_pixels = sar_db_array[valid_mask]
    total_valid = valid_pixels.size

    below_m32 = float(np.count_nonzero(valid_pixels < MIN_DB_BOUND) / total_valid * 100.0)
    inside_m32_0 = float(np.count_nonzero((valid_pixels >= MIN_DB_BOUND) & (valid_pixels <= MAX_DB_BOUND)) / total_valid * 100.0)
    above_0 = float(np.count_nonzero(valid_pixels > MAX_DB_BOUND) / total_valid * 100.0)

    norm_pixels = normalize_sar_db(valid_pixels)

    return {
        "pct_below_m32_db": round(below_m32, 4),
        "pct_inside_m32_0_db": round(inside_m32_0, 4),
        "pct_above_0_db": round(above_0, 4),
        "normalized_stats": {
            "min": round(float(norm_pixels.min()), 4),
            "max": round(float(norm_pixels.max()), 4),
            "mean": round(float(norm_pixels.mean()), 4),
            "p2": round(float(np.percentile(norm_pixels, 2.0)), 4),
            "p98": round(float(np.percentile(norm_pixels, 98.0)), 4),
        },
        "gate_passed": bool(inside_m32_0 >= 90.0)
    }
