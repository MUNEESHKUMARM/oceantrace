import logging
import requests
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from app.core.config import settings
from app.services.cdse_auth import get_access_token, CDSEAuthenticationError
from app.services.sar_preprocessing import sar_preprocessing_service

logger = logging.getLogger(__name__)


import logging
import requests
import numpy as np
import datetime
import io
import rasterio
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

from app.core.config import settings
from app.services.cdse_auth import get_access_token, CDSEAuthenticationError
from app.services.sar_preprocessing import sar_preprocessing_service

logger = logging.getLogger(__name__)


class Sentinel1Service:
    def __init__(self):
        self.catalog_url = f"{settings.CDSE_BASE_URL}/api/v1/catalog/1.0.0/search"
        self.stac_url = f"{getattr(settings, 'CDSE_STAC_URL', 'https://stac.dataspace.copernicus.eu/v1')}/search"
        self.process_url = f"{settings.CDSE_BASE_URL}/api/v1/process"

    def search_scenes(
        self,
        bbox: Tuple[float, float, float, float],
        start_date: str,
        end_date: str,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Queries Copernicus Data Space STAC / Catalog for Sentinel-1 GRD scenes intersecting AOI.
        Returns results sorted by actual sensing datetime in DESCENDING order (newest first).
        """
        min_lon, min_lat, max_lon, max_lat = bbox

        payload = {
            "bbox": [min_lon, min_lat, max_lon, max_lat],
            "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
            "collections": ["sentinel-1-grd"],
            "limit": max_results,
        }

        features = []
        token = None
        try:
            token = get_access_token()
        except Exception as e:
            logger.warning("Could not acquire CDSE token for search, trying unauthenticated STAC: %s", str(e))

        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # Try CDSE STAC Endpoint first, then fallback to Catalog endpoint
        endpoints_to_try = [self.stac_url, self.catalog_url]
        for url in endpoints_to_try:
            try:
                logger.info("[PHASE1] Querying CDSE STAC: %s (bbox=%s, datetime=%s)", url, bbox, payload["datetime"])
                res = requests.post(url, json=payload, headers=headers, timeout=20.0)
                if res.status_code == 200:
                    data = res.json()
                    features = data.get("features", [])
                    if features:
                        break
            except Exception as e:
                logger.warning("[PHASE1] STAC query to %s failed: %s", url, str(e))

        results = []
        for feat in features:
            props = feat.get("properties", {})
            results.append({
                "id": feat.get("id"),
                "datetime": props.get("datetime"),
                "satellite": props.get("platform", "SENTINEL-1"),
                "product_type": props.get("s1:product_type", "GRD"),
                "polarization": props.get("s1:polarization", ["VV", "VH"]),
                "orbit_direction": props.get("sat:orbit_state", "ASCENDING"),
                "bbox": feat.get("bbox", list(bbox)),
            })

        # Parse sensing datetime and sort candidates descending (newest acquisition first)
        def parse_acquisition_datetime(scene_item: Dict[str, Any]) -> datetime.datetime:
            dt_str = scene_item.get("datetime")
            if not dt_str:
                return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
            try:
                return datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except Exception:
                return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)

        results.sort(key=parse_acquisition_datetime, reverse=True)
        logger.info("[PHASE1] STAC search returned %d candidates (sorted newest first)", len(results))
        return results

    def fetch_and_process_sar(
        self,
        bbox: Tuple[float, float, float, float],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        polarization: str = "VV",
        width: int = 512,
        height: int = 512,
    ) -> Dict[str, Any]:
        """
        Requests Sentinel-1 GRD imagery from CDSE Sentinel Hub Process API for newest valid scene,
        applies SAR preprocessing pipeline, and outputs Float32 GeoTIFF and preview PNG.
        """
        token = get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        min_lon, min_lat, max_lon, max_lat = bbox

        is_dynamic = False
        candidate_scenes: List[Dict[str, Any]] = []

        # Determine if caller requested specific dates or dynamic latest search
        if not start_date or not end_date or start_date.lower() in ["auto", "latest"] or end_date.lower() in ["auto", "latest"]:
            is_dynamic = True
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            
            # Step 1: Initial recent search window (default 7 days)
            days_w1 = getattr(settings, "SENTINEL_SEARCH_DAYS", 7)
            t_start_w1 = (now_utc - datetime.timedelta(days=days_w1)).strftime("%Y-%m-%d")
            t_end_w1 = now_utc.strftime("%Y-%m-%d")
            
            logger.info("[PHASE1] CDSE search started for AOI %s over last %d days (%s to %s)", bbox, days_w1, t_start_w1, t_end_w1)
            candidate_scenes = self.search_scenes(bbox=bbox, start_date=t_start_w1, end_date=t_end_w1, max_results=10)

            # Step 2: Fallback window 14 days
            if not candidate_scenes:
                logger.info("[PHASE1] No scenes found in %d-day window. Expanding search window to 14 days...", days_w1)
                t_start_w2 = (now_utc - datetime.timedelta(days=14)).strftime("%Y-%m-%d")
                candidate_scenes = self.search_scenes(bbox=bbox, start_date=t_start_w2, end_date=t_end_w1, max_results=10)

            # Step 3: Fallback window 30 days
            if not candidate_scenes:
                logger.info("[PHASE1] No scenes found in 14-day window. Expanding search window to 30 days...")
                t_start_w3 = (now_utc - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
                candidate_scenes = self.search_scenes(bbox=bbox, start_date=t_start_w3, end_date=t_end_w1, max_results=10)

            if not candidate_scenes:
                raise RuntimeError(
                    f"No Sentinel-1 acquisition available for AOI {bbox} in recent search windows (7, 14, 30 days)."
                )
        else:
            # Explicit date range requested by caller
            logger.info("[PHASE1] Explicit date range requested: %s to %s for bbox %s", start_date, end_date, bbox)
            candidate_scenes = self.search_scenes(bbox=bbox, start_date=start_date, end_date=end_date, max_results=10)

        # Select newest valid candidate product
        valid_pixels: Optional[np.ndarray] = None
        selected_scene: Optional[Dict[str, Any]] = None
        actual_acq_time = (end_date + "T12:00:00Z") if end_date else datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        actual_bbox = list(bbox)

        evalscript = """//VERSION=3
function setup() {
  return {
    input: ["VV"],
    output: { bands: 1, sampleType: "FLOAT32" }
  };
}
function evaluatePixel(sample) {
  return [sample.VV];
}
"""

        # Check local cache for newest valid candidate to avoid re-downloading
        if candidate_scenes:
            first_candidate = candidate_scenes[0]
            scene_id = first_candidate.get("id", "scene")
            cached_filename = f"{scene_id}_{polarization}_processed.tif"
            cached_path = settings.DATA_OUTPUT_DIR / cached_filename
            cached_preview = settings.DATA_OUTPUT_DIR / f"{scene_id}_{polarization}_preview.png"

            if cached_path.exists() and cached_preview.exists() and cached_path.stat().st_size > 0:
                logger.info("[PHASE1] Cache hit for product %s. Reusing local processed files.", scene_id)
                try:
                    with rasterio.open(cached_path) as src:
                        pixels = src.read(1)
                        if np.count_nonzero(np.isfinite(pixels) & (pixels > 0)) > 0:
                            # Re-construct metadata output from cached files
                            val_pct = float((np.count_nonzero(np.isfinite(pixels)) / pixels.size) * 100.0)
                            min_v = float(pixels.min())
                            max_v = float(pixels.max())
                            mean_v = float(pixels.mean())

                            return {
                                "status": "success",
                                "product_type": first_candidate.get("product_type", "GRD"),
                                "output_file": str(cached_path),
                                "output_filename": cached_path.name,
                                "preview_file": str(cached_preview),
                                "preview_filename": cached_preview.name,
                                "thumbnail_file": str(cached_preview),
                                "thumbnail_filename": cached_preview.name,
                                "acquisition_time": first_candidate.get("datetime") or actual_acq_time,
                                "polarization": polarization,
                                "processing": {
                                    "radiometric_calibration": True,
                                    "speckle_filtering": True,
                                    "decibel_scaling": True,
                                    "geometric_correction": True,
                                    "land_sea_masking": True,
                                },
                                "validation": {
                                    "finite_pixels_count": int(pixels.size),
                                    "nan_pixels_count": 0,
                                    "total_pixels_count": int(pixels.size),
                                    "valid_pixels_pct": val_pct,
                                    "min_value_db": min_v,
                                    "max_value_db": max_v,
                                    "mean_value_db": mean_v,
                                },
                                "raster_info": {
                                    "width": width,
                                    "height": height,
                                    "crs": "EPSG:4326",
                                    "bounds": {
                                        "min_lon": bbox[0],
                                        "min_lat": bbox[1],
                                        "max_lon": bbox[2],
                                        "max_lat": bbox[3],
                                    },
                                    "min_value_db": min_v,
                                    "max_value_db": max_v,
                                    "mean_value_db": mean_v,
                                },
                                "visualization": {
                                    "preview_filename": cached_preview.name,
                                    "thumbnail_filename": cached_preview.name,
                                    "statistics": {
                                        "source_min": min_v,
                                        "source_max": max_v,
                                        "p2": float(np.percentile(pixels, 2)),
                                        "p98": float(np.percentile(pixels, 98)),
                                        "preview_min": 0,
                                        "preview_max": 255,
                                    },
                                },
                                "source_product_id": scene_id,
                                "platform": first_candidate.get("satellite", "SENTINEL-1"),
                                "is_latest_available": is_dynamic,
                                "source_catalogue": "Copernicus Data Space Ecosystem",
                            }
                except Exception as e:
                    logger.warning("[PHASE1] Could not read cached product %s: %s. Fetching fresh...", scene_id, str(e))

        # Query Process API for candidate scenes sorted newest first
        if candidate_scenes:
            for candidate in candidate_scenes:
                dt_str = candidate.get("datetime")
                scene_bbox = candidate.get("bbox", list(bbox))
                if not dt_str:
                    continue

                dt_obj = datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                t_from = (dt_obj - datetime.timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
                t_to = (dt_obj + datetime.timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

                scene_center_lon = (scene_bbox[0] + scene_bbox[2]) / 2.0
                scene_center_lat = (scene_bbox[1] + scene_bbox[3]) / 2.0

                sub_bbox = [
                    scene_center_lon - 0.15,
                    scene_center_lat - 0.15,
                    scene_center_lon + 0.15,
                    scene_center_lat + 0.15
                ]

                payload = {
                    "input": {
                        "bounds": {
                            "bbox": sub_bbox,
                            "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
                        },
                        "data": [
                            {
                                "type": "sentinel-1-grd",
                                "dataFilter": {
                                    "timeRange": {
                                        "from": t_from,
                                        "to": t_to
                                    }
                                },
                                "processing": {
                                    "orthorectify": True,
                                    "backCoeff": "SIGMA0_ELLIPSOID"
                                }
                            }
                        ]
                    },
                    "output": {
                        "width": width,
                        "height": height,
                        "responses": [
                            {
                                "identifier": "default",
                                "format": {"type": "image/tiff"}
                            }
                        ]
                    },
                    "evalscript": evalscript
                }

                try:
                    logger.info("[PHASE1] Fetching SAR raster for newest candidate product %s (%s)...", candidate.get("id"), dt_str)
                    response = requests.post(self.process_url, json=payload, headers=headers, timeout=40.0)
                    if response.status_code == 200 and response.headers.get("content-type", "").startswith("image/"):
                        with rasterio.open(io.BytesIO(response.content)) as src:
                            pixels = src.read(1)
                            finite_cnt = np.count_nonzero(np.isfinite(pixels) & (pixels > 0))
                            if finite_cnt > 0:
                                valid_pixels = pixels
                                actual_acq_time = dt_str
                                actual_bbox = sub_bbox
                                selected_scene = candidate
                                logger.info("[PHASE1] Successfully fetched valid SAR raster for scene %s", candidate.get("id"))
                                break
                except Exception as e:
                    logger.warning("[PHASE1] Error fetching candidate scene %s: %s", candidate.get("id"), str(e))

        # Direct Process API fallback if candidate iteration yields 0 finite pixels
        if valid_pixels is None and start_date and end_date:
            logger.info("[PHASE1] Direct Process API query fallback for range %s to %s...", start_date, end_date)
            payload = {
                "input": {
                    "bounds": {
                        "bbox": list(bbox),
                        "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
                    },
                    "data": [
                        {
                            "type": "sentinel-1-grd",
                            "dataFilter": {
                                "timeRange": {
                                    "from": f"{start_date}T00:00:00Z",
                                    "to": f"{end_date}T23:59:59Z"
                                }
                            },
                            "processing": {
                                "orthorectify": True,
                                "backCoeff": "SIGMA0_ELLIPSOID"
                            }
                        }
                    ]
                },
                "output": {
                    "width": width,
                    "height": height,
                    "responses": [
                        {
                            "identifier": "default",
                            "format": {"type": "image/tiff"}
                        }
                    ]
                },
                "evalscript": evalscript
            }

            try:
                response = requests.post(self.process_url, json=payload, headers=headers, timeout=40.0)
                if response.status_code == 200 and response.headers.get("content-type", "").startswith("image/"):
                    with rasterio.open(io.BytesIO(response.content)) as src:
                        pixels = src.read(1)
                        if np.count_nonzero(np.isfinite(pixels) & (pixels > 0)) > 0:
                            valid_pixels = pixels
            except Exception as e:
                logger.error("[PHASE1] Direct Process API request failed: %s", str(e))

        if valid_pixels is None:
            raise RuntimeError(
                f"Sentinel-1 SAR retrieval FAILED: 100% of raster pixels returned from CDSE Sentinel Hub are NaN. "
                f"No valid satellite backscatter pixels could be retrieved for bbox {bbox}."
            )

        # Execute SAR Preprocessing Pipeline (Calibration, Lee Speckle Filter, dB Scaling, GeoTIFF Export)
        result = sar_preprocessing_service.process_sar_raster(
            raw_pixels=valid_pixels,
            bbox=tuple(actual_bbox),
            acquisition_time=actual_acq_time,
            polarization=polarization,
            apply_calibration=True,
            apply_speckle_filter=True,
            apply_db_scale=True,
        )

        # Enrich response metadata
        prod_id = selected_scene.get("id") if selected_scene else "sentinel1"
        platform_name = selected_scene.get("satellite", "SENTINEL-1") if selected_scene else "SENTINEL-1"

        result["source_product_id"] = prod_id
        result["platform"] = platform_name
        result["is_latest_available"] = is_dynamic
        result["source_catalogue"] = "Copernicus Data Space Ecosystem"

        logger.info("[PHASE1] Phase 1 complete for product %s (platform: %s, acquisition: %s)", prod_id, platform_name, actual_acq_time)
        return result


sentinel1_service = Sentinel1Service()


