import os
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
import rasterio
from PIL import Image

logger = logging.getLogger(__name__)


class SARVisualizationService:
    @staticmethod
    def create_sar_preview(
        geotiff_path: str,
        lower_percentile: float = 2.0,
        upper_percentile: float = 98.0,
        thumbnail_size: Tuple[int, int] = (128, 128),
    ) -> Dict[str, Any]:
        """
        Generates a non-destructive human-viewable 8-bit PNG preview image
        and thumbnail from a Float32 Sentinel-1 SAR GeoTIFF.
        Uses a display-only contrast stretch (2nd-98th percentile clipping).
        The original Float32 GeoTIFF is NOT modified in any way.
        """
        path = Path(geotiff_path)
        if not path.exists():
            raise FileNotFoundError(f"Source GeoTIFF not found: {geotiff_path}")

        # 1. Read Float32 SAR raster using Rasterio
        with rasterio.open(path) as src:
            data = src.read(1)
            nodata_val = src.nodata
            src_w, src_h = src.width, src.height

        # 2. Extract finite valid pixels
        if nodata_val is not None:
            valid_mask = np.isfinite(data) & (data != nodata_val)
        else:
            valid_mask = np.isfinite(data)

        valid_pixels = data[valid_mask]
        if valid_pixels.size == 0:
            raise ValueError(f"Cannot generate preview: 0 valid finite pixels in {geotiff_path}")

        source_min = float(np.min(valid_pixels))
        source_max = float(np.max(valid_pixels))

        # 3. Calculate robust percentiles for display stretch
        p2 = float(np.percentile(valid_pixels, lower_percentile))
        p98 = float(np.percentile(valid_pixels, upper_percentile))

        # 4. Perform display-only contrast stretch
        clipped = np.clip(data, p2, p98)

        if p98 > p2:
            display_scaled = (clipped - p2) / (p98 - p2) * 255.0
        else:
            display_scaled = np.zeros_like(data, dtype=np.float32)

        # Set invalid/nodata pixels to 0
        display_scaled = np.where(valid_mask, display_scaled, 0.0)
        preview_uint8 = np.clip(display_scaled, 0, 255).astype(np.uint8)

        preview_min = int(np.min(preview_uint8[valid_mask])) if np.any(valid_mask) else 0
        preview_max = int(np.max(preview_uint8[valid_mask])) if np.any(valid_mask) else 0

        logger.info(
            "SAR Preview Contrast Stretch Stats for %s:\n"
            "  Source Min (dB): %.4f\n"
            "  Source Max (dB): %.4f\n"
            "  Lower Percentile (p%.1f): %.4f\n"
            "  Upper Percentile (p%.1f): %.4f\n"
            "  Preview Min (uint8): %d\n"
            "  Preview Max (uint8): %d",
            path.name, source_min, source_max, lower_percentile, p2, upper_percentile, p98, preview_min, preview_max
        )

        # 5. Determine preview and thumbnail output paths
        base_name = path.stem
        if base_name.endswith("_processed"):
            preview_filename = base_name.replace("_processed", "_preview") + ".png"
            thumbnail_filename = base_name.replace("_processed", "_thumbnail") + ".png"
        else:
            preview_filename = f"{base_name}_preview.png"
            thumbnail_filename = f"{base_name}_thumbnail.png"

        output_dir = path.parent
        preview_path = output_dir / preview_filename
        thumbnail_path = output_dir / thumbnail_filename

        # 6. Save full-resolution preview PNG
        img = Image.fromarray(preview_uint8, mode="L")
        img.save(preview_path, format="PNG")

        # 7. Generate thumbnail preserving aspect ratio
        thumb_img = img.copy()
        thumb_img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
        thumb_img.save(thumbnail_path, format="PNG")

        # 8. Quality Validation
        validation = SARVisualizationService.validate_preview_image(
            preview_path=preview_path,
            expected_width=src_w,
            expected_height=src_h
        )

        logger.info(
            "Successfully created SAR preview PNG (%s) and thumbnail PNG (%s)",
            preview_path.name, thumbnail_path.name
        )

        return {
            "preview_file": str(preview_path),
            "preview_filename": preview_filename,
            "thumbnail_file": str(thumbnail_path),
            "thumbnail_filename": thumbnail_filename,
            "statistics": {
                "source_min": source_min,
                "source_max": source_max,
                "p2": p2,
                "p98": p98,
                "preview_min": preview_min,
                "preview_max": preview_max,
            },
            "validation": validation,
        }

    @staticmethod
    def validate_preview_image(
        preview_path: Path,
        expected_width: int,
        expected_height: int
    ) -> Dict[str, Any]:
        """
        Validates the generated PNG preview image:
        - PNG exists and file size > 0
        - PNG opens successfully
        - Width = source width
        - Height = source height
        - Mode = grayscale (L)
        - Pixel values 0-255
        - No NaN / Inf
        """
        if not preview_path.exists():
            raise FileNotFoundError(f"Preview PNG file does not exist: {preview_path}")

        file_size = preview_path.stat().st_size
        if file_size == 0:
            raise ValueError(f"Preview PNG file is empty (0 bytes): {preview_path}")

        with Image.open(preview_path) as img:
            width, height = img.size
            mode = img.mode
            img_arr = np.array(img)

        nan_count = int(np.count_nonzero(np.isnan(img_arr)))
        inf_count = int(np.count_nonzero(np.isinf(img_arr)))
        p_min = int(np.min(img_arr))
        p_max = int(np.max(img_arr))

        if width != expected_width or height != expected_height:
            raise ValueError(
                f"Preview image dimension mismatch: expected ({expected_width}, {expected_height}), got ({width}, {height})"
            )

        if mode not in ["L", "RGB"]:
            raise ValueError(f"Unexpected image mode: {mode}")

        if nan_count > 0 or inf_count > 0:
            raise ValueError(f"Preview PNG contains NaN/Inf values! (NaNs: {nan_count}, Infs: {inf_count})")

        return {
            "valid": True,
            "file_size_bytes": file_size,
            "width": width,
            "height": height,
            "mode": mode,
            "min_pixel": p_min,
            "max_pixel": p_max,
            "nan_count": nan_count,
            "inf_count": inf_count,
        }


sar_visualization_service = SARVisualizationService()
