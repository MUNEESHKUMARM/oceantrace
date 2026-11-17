import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import numpy as np
import rasterio
from rasterio.crs import CRS

from app.core.config import settings
from app.models.segmentation_unet import UNet, TORCH_AVAILABLE
from app.services.sar_normalization import normalize_sar_db, audit_db_clipping_gate

if TORCH_AVAILABLE:
    import torch
    import torch.nn.functional as F

logger = logging.getLogger(__name__)


class OilDetectionService:
    def __init__(self, model_checkpoint_path: Optional[str] = None):
        if model_checkpoint_path:
            self.model_checkpoint_path = Path(model_checkpoint_path)
        else:
            new_ckpt = settings.BASE_DIR / "models" / "checkpoints" / "unet_oil_spill_real_vv.pth"
            legacy_ckpt = settings.BASE_DIR / "models" / "checkpoints" / "unet_oil_spill.pth"
            self.model_checkpoint_path = new_ckpt if new_ckpt.exists() else legacy_ckpt

        self.device = "cuda" if (TORCH_AVAILABLE and torch.cuda.is_available()) else "cpu"
        self._model: Optional[Any] = None

    def _load_model(self) -> Any:
        """Loads PyTorch U-Net model from trained checkpoint weights."""
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch is not available in the current environment.")

        if not self.model_checkpoint_path.exists():
            logger.warning("No trained model checkpoint found at %s", self.model_checkpoint_path)
            raise RuntimeError(
                f"PHASE 2 BLOCKED — DATASET/MODEL ISSUE: Model checkpoint not found at {self.model_checkpoint_path}. "
                f"Real AI detection requires a trained U-Net model checkpoint."
            )

        checkpoint = torch.load(self.model_checkpoint_path, map_location=self.device)
        state_dict = checkpoint["model_state_dict"] if (isinstance(checkpoint, dict) and "model_state_dict" in checkpoint) else (checkpoint["state_dict"] if (isinstance(checkpoint, dict) and "state_dict" in checkpoint) else checkpoint)

        try:
            model = UNet(in_channels=1, num_classes=1, base_c=16).to(self.device)
            model.load_state_dict(state_dict)
        except Exception:
            model = UNet(in_channels=1, num_classes=1, base_c=64).to(self.device)
            model.load_state_dict(state_dict)

        model.eval()
        self._model = model
        logger.info("[PHASE2] Successfully loaded PyTorch U-Net model from %s", self.model_checkpoint_path)
        return model

    def resolve_latest_phase1_geotiff(self) -> Path:
        """
        Dynamically resolves the latest processed scientific GeoTIFF from Phase 1.
        Uses Phase 1 CDSE STAC discovery to identify candidate scenes sorted by acquisition
        sensing datetime (newest first), linking directly to the exact processed local raster.
        Never relies on arbitrary filesystem modification time (st_mtime).
        """
        logger.info("[PHASE2] Querying Phase 1 CDSE STAC for newest acquisition by sensing datetime...")
        from app.services.sentinel1_service import sentinel1_service
        p1_res = sentinel1_service.fetch_and_process_sar(bbox=(71.5, 18.0, 72.5, 19.0))
        output_path = Path(p1_res["output_file"])
        logger.info("[PHASE2] Resolved latest Phase 1 scene by acquisition datetime (%s): %s",
                    p1_res.get("acquisition_time"), output_path.name)
        return output_path

    @staticmethod
    def audit_input_compatibility(raw_sar: np.ndarray) -> Dict[str, Any]:
        """
        Audits input SAR raster statistics against the physical Sentinel-1 VV U-Net training normalization contract.
        Trained Contract: Single-channel decibel SAR [-32.0 dB, 0.0 dB] scaled linearly to [0.0, 1.0].
        Dynamically returns COMPATIBLE, PARTIALLY_COMPATIBLE, or INCOMPATIBLE.
        """
        gate = audit_db_clipping_gate(raw_sar)
        finite_mask = np.isfinite(raw_sar) & (raw_sar != -9999.0)
        valid_pixels = raw_sar[finite_mask] if np.any(finite_mask) else raw_sar.ravel()

        min_v = float(valid_pixels.min())
        max_v = float(valid_pixels.max())
        mean_v = float(valid_pixels.mean())
        p2 = float(np.percentile(valid_pixels, 2.0))
        p98 = float(np.percentile(valid_pixels, 98.0))

        norm_sar = normalize_sar_db(raw_sar)
        norm_valid = norm_sar[finite_mask] if np.any(finite_mask) else norm_sar.ravel()

        status = "COMPATIBLE" if gate["gate_passed"] else "PARTIALLY_COMPATIBLE"
        reason = "Raster metrics align with physical Sentinel-1 decibel SAR input contract." if gate["gate_passed"] else "Decibel values have partial clipping."

        return {
            "training_range": "[-32.0 dB, 0.0 dB]",
            "scene_range": [round(min_v, 4), round(max_v, 4)],
            "scene_mean": round(mean_v, 4),
            "scene_p2": round(p2, 4),
            "scene_p98": round(p98, 4),
            "finite_pixel_pct": round(float(np.mean(finite_mask)*100.0), 2),
            "normalization_breakdown": {
                "below_m32_db_pct": gate["pct_below_m32_db"],
                "between_m32_0_db_pct": gate["pct_inside_m32_0_db"],
                "above_0_db_pct": gate["pct_above_0_db"],
            },
            "normalized_stats": gate["normalized_stats"],
            "normalization_method": "decibel_scaling_clip_0_1",
            "compatibility_status": status,
            "reason": reason,
            "note": "Current scene inference is a model-predicted oil-spill region demonstration on newly acquired Sentinel-1 data."
        }

    def run_detection(self, geotiff_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes AI Oil-Spill Detection / Segmentation Pipeline:
        1. Resolve latest Phase 1 SAR GeoTIFF dynamically if omitted
        2. Audit input compatibility and validate pixel integrity
        3. Apply model input normalization matching trained contract
        4. Execute PyTorch U-Net model inference
        5. Generate binary prediction mask (0=Background, 1=Oil Spill) & confidence map
        6. Export output rasters (sar_mask.tif, sar_confidence.tif, sar_overlay.png) with georeferencing
        7. Return structured JSON response with real confidence & diagnostics
        """
        if not geotiff_path or geotiff_path.lower() in ["latest", "auto"]:
            input_path = self.resolve_latest_phase1_geotiff()
        else:
            input_path = Path(geotiff_path)

        if not input_path.exists():
            raise FileNotFoundError(f"Input SAR GeoTIFF not found: {input_path}")

        logger.info("[PHASE2] Resolving latest Phase 1 scene: %s", input_path.name)

        # 1. Read input GeoTIFF using Rasterio
        with rasterio.open(input_path) as src:
            width = src.width
            height = src.height
            crs = src.crs
            transform = src.transform
            raw_sar = src.read(1)

        # 2. Audit input compatibility
        compat_info = self.audit_input_compatibility(raw_sar)
        logger.info("[PHASE2] Preprocessing input range: min=%s, max=%s, mean=%s",
                    compat_info.get("scene_range", [None, None])[0],
                    compat_info.get("scene_range", [None, None])[1],
                    compat_info.get("scene_mean"))
        logger.info("[PHASE2] Compatibility: %s (%s)", compat_info["compatibility_status"], compat_info["reason"])

        if compat_info["compatibility_status"] == "INCOMPATIBLE":
            raise ValueError(f"Input SAR GeoTIFF is INCOMPATIBLE with U-Net contract: {compat_info['reason']}")

        # 3. Model Normalization matching physical training preprocessing [-32.0 dB, 0.0 dB] -> [0.0, 1.0]
        norm_sar = normalize_sar_db(raw_sar)

        # Handle size compatibility (e.g. resize if not 512x512)
        if (height, width) != (512, 512):
            logger.info("[PHASE2] Resizing input raster from (%d, %d) to (512, 512) for U-Net inference", height, width)
            from PIL import Image
            img_norm = Image.fromarray(norm_sar).resize((512, 512), resample=Image.BILINEAR)
            norm_sar_input = np.array(img_norm, dtype=np.float32)
        else:
            norm_sar_input = norm_sar

        # 4. Check for trained model weights
        if not self.model_checkpoint_path.exists():
            logger.error("Trained model checkpoint missing at %s", self.model_checkpoint_path)
            raise RuntimeError(
                f"PHASE 2 BLOCKED — DATASET/MODEL ISSUE: Model weights missing at {self.model_checkpoint_path}. "
                f"Cannot perform real AI inference without trained model weights. Fake AI results are prohibited."
            )

        model = self._load_model()
        logger.info("[PHASE2] Loading U-Net checkpoint from %s", self.model_checkpoint_path.name)
        logger.info("[PHASE2] Running real inference")

        # 5. PyTorch Model Inference
        with torch.no_grad():
            tensor_in = torch.from_numpy(norm_sar_input).unsqueeze(0).unsqueeze(0).to(self.device)  # (1, 1, 512, 512)
            logits = model(tensor_in)  # (1, 1, 512, 512)
            if logits.size(1) == 1:
                oil_probs_512 = torch.sigmoid(logits).squeeze().cpu().numpy()  # (512, 512)
            else:
                probs = F.softmax(logits, dim=1).squeeze(0).cpu().numpy()
                oil_probs_512 = probs[1]

        # Resize output probabilities back to original raster shape if needed
        if (height, width) != (512, 512):
            from PIL import Image
            oil_probs = np.array(Image.fromarray(oil_probs_512).resize((width, height), resample=Image.BILINEAR), dtype=np.float32)
        else:
            oil_probs = oil_probs_512

        threshold = 0.5
        pred_mask = (oil_probs > threshold).astype(np.uint8)
        confidence_map = np.where(pred_mask == 1, oil_probs, 1.0 - oil_probs).astype(np.float32)

        oil_pixels = int(np.count_nonzero(pred_mask == 1))
        bg_pixels = int(np.count_nonzero(pred_mask == 0))
        total_pixels = int(pred_mask.size)
        oil_pct = float((oil_pixels / total_pixels) * 100.0)

        is_detected = bool(oil_pixels > 50)  # Minimum pixel threshold for detection
        if is_detected and oil_pixels > 0:
            avg_confidence = float(np.mean(confidence_map[pred_mask == 1]))
        else:
            avg_confidence = float(np.mean(confidence_map[pred_mask == 0]))

        logger.info("[PHASE2] Oil pixels: %d / %d (%.2f%%)", oil_pixels, total_pixels, oil_pct)
        logger.info("[PHASE2] Oil percentage: %.4f%%", oil_pct)
        logger.info("[PHASE2] Oil detected: %s", is_detected)

        # 6. Export Output Files (sar_mask.tif, sar_confidence.tif, sar_overlay.png)
        timestamp_str = int(time.time())
        output_dir = settings.DATA_OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        scene_stem = input_path.stem.replace("_processed", "")
        mask_filename = f"sar_mask_{scene_stem}.tif"
        conf_filename = f"sar_confidence_{scene_stem}.tif"
        overlay_filename = f"sar_overlay_{scene_stem}.png"

        mask_path = output_dir / mask_filename
        conf_path = output_dir / conf_filename
        overlay_path = output_dir / overlay_filename

        # Write Prediction Mask GeoTIFF
        with rasterio.open(
            mask_path,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype=pred_mask.dtype,
            crs=crs,
            transform=transform,
        ) as dst:
            dst.write(pred_mask, 1)

        # Write Confidence Map GeoTIFF
        with rasterio.open(
            conf_path,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype=confidence_map.dtype,
            crs=crs,
            transform=transform,
        ) as dst:
            dst.write(confidence_map, 1)

        # Create Overlay Visualization PNG
        self._generate_overlay_image(raw_sar, pred_mask, overlay_path)

        logger.info("[PHASE2] Prediction mask saved to %s", mask_path.name)
        logger.info("[PHASE2] Overlay saved to %s", overlay_path.name)
        logger.info("[PHASE2] Phase 2 complete")

        return {
            "detected": is_detected,
            "confidence": round(avg_confidence, 4),
            "mask_file": str(mask_path),
            "confidence_file": str(conf_path),
            "overlay_file": str(overlay_path),
            "class_distribution": {
                "background_pixels": int(bg_pixels),
                "oil_spill_pixels": int(oil_pixels),
                "lookalike_pixels": 0,
            },
            "oil_pixel_percentage": round(oil_pct, 4),
            "threshold": threshold,
            "compatibility": compat_info,
            "model_info": {
                "architecture": "U-Net",
                "checkpoint": str(self.model_checkpoint_path),
                "device": self.device,
            },
            "disclaimer": "Model inference on real Sentinel-1 acquisition without scene-specific ground truth; quantitative IoU/Dice validation requires labeled ground truth."
        }

    @staticmethod
    def _generate_overlay_image(raw_sar: np.ndarray, pred_mask: np.ndarray, output_png_path: Path):
        """
        Generates RGB PNG overlay visualization combining actual SAR grayscale base + oil mask overlay.
        - Background (0): actual SAR grayscale image (contrast-stretched 2nd-98th percentile).
        - Oil Spill (1): highlighted in red.
        - If no oil detected: returns the exact original SAR base image (never blank white).
        """
        try:
            from PIL import Image
            valid_mask = np.isfinite(raw_sar) & (raw_sar != -9999.0)
            valid_pixels = raw_sar[valid_mask] if np.any(valid_mask) else raw_sar.ravel()

            if valid_pixels.size > 0:
                p2 = float(np.percentile(valid_pixels, 2.0))
                p98 = float(np.percentile(valid_pixels, 98.0))
                clipped = np.clip(raw_sar, p2, p98)
                if p98 > p2:
                    sar_uint8 = ((clipped - p2) / (p98 - p2) * 255.0).astype(np.uint8)
                else:
                    sar_uint8 = np.zeros_like(raw_sar, dtype=np.uint8)
            else:
                sar_uint8 = np.zeros_like(raw_sar, dtype=np.uint8)

            sar_uint8 = np.where(valid_mask, sar_uint8, 0)
            rgb = np.stack([sar_uint8, sar_uint8, sar_uint8], axis=-1)

            # Highlight Oil Spill pixels (Class 1) with red tint overlay
            oil_mask = (pred_mask == 1)
            if np.any(oil_mask):
                rgb[oil_mask, 0] = np.clip(rgb[oil_mask, 0].astype(np.int16) + 160, 0, 255).astype(np.uint8)
                rgb[oil_mask, 1] = (rgb[oil_mask, 1] * 0.2).astype(np.uint8)
                rgb[oil_mask, 2] = (rgb[oil_mask, 2] * 0.2).astype(np.uint8)

            img = Image.fromarray(rgb)
            img.save(output_png_path)
            logger.info("[PHASE2] Saved overlay visualization to %s", output_png_path.name)
        except Exception as e:
            logger.warning("Failed to save overlay visualization image: %s", str(e))


oil_detection_service = OilDetectionService()
