import sys
import os
import time
import datetime
import numpy as np
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

def run_phase1_tests():
    print("=======================================================================")
    print("OCEANTRACE AI - PHASE 1 AUTOMATED VERIFICATION SUITE (DYNAMIC STAC)")
    print("=======================================================================\n")

    # CHECK 1: CDSE OAuth authentication
    print("[CHECK 1/14] Verifying CDSE OAuth Authentication...")
    cdse_authenticated = False
    try:
        from app.services.cdse_auth import get_access_token
        token = get_access_token()
        assert token and len(token) > 100, "OAuth Token is invalid or too short"
        cdse_authenticated = True
        print(f"  [OK] VERIFIED: CDSE OAuth Access Token acquired (Len: {len(token)} chars)")
    except Exception as e:
        print(f"  [WARNING] CDSE OAuth authentication failed or unconfigured: {e}")

    # CHECK 2: STAC Catalog Search Logic & Descending Acquisition Timestamp Sorting
    print("\n[CHECK 2/14] Verifying STAC Discovery & Descending Date Sorting...")
    bbox = (71.5, 18.0, 72.5, 19.0)
    try:
        from app.services.sentinel1_service import sentinel1_service
        # Direct call to search_scenes with explicit date range
        scenes = sentinel1_service.search_scenes(
            bbox=bbox,
            start_date="2024-06-01",
            end_date="2024-06-30",
            max_results=10
        )
        assert len(scenes) > 0, "No Sentinel-1 GRD scenes discovered in STAC search"
        
        # Verify descending sorting order
        dts = [s["datetime"] for s in scenes if s.get("datetime")]
        for i in range(len(dts) - 1):
            dt_curr = datetime.datetime.fromisoformat(dts[i].replace("Z", "+00:00"))
            dt_next = datetime.datetime.fromisoformat(dts[i+1].replace("Z", "+00:00"))
            assert dt_curr >= dt_next, f"Scenes not sorted descending: {dts[i]} < {dts[i+1]}"

        print(f"  [OK] VERIFIED: STAC Catalog Search returned {len(scenes)} GRD scenes sorted newest first.")
        print(f"    - Newest Candidate ID: {scenes[0]['id']} | Date: {scenes[0]['datetime']} | Sat: {scenes[0].get('satellite')}")
    except Exception as e:
        print(f"  [FAIL] FAILED: STAC Discovery failed: {e}")
        return False

    # CHECK 3: Dynamic Search Window & Fallback Strategy Unit Test
    print("\n[CHECK 3/14] Verifying Dynamic Search Window Calculation & Fallback Logic...")
    try:
        from app.core.config import settings
        days_w1 = getattr(settings, "SENTINEL_SEARCH_DAYS", 7)
        fallback_days = getattr(settings, "SENTINEL_SEARCH_FALLBACK_DAYS", [14, 30])
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        
        start_w1 = (now_utc - datetime.timedelta(days=days_w1)).strftime("%Y-%m-%d")
        end_w1 = now_utc.strftime("%Y-%m-%d")
        
        assert start_w1 < end_w1, "Dynamic start date must be before end date"
        assert fallback_days == [14, 30], "Fallback search windows must be 14 and 30 days"
        print(f"  [OK] VERIFIED: Dynamic rolling window default: {days_w1} days ({start_w1} to {end_w1}), Fallbacks: {fallback_days} days.")
    except Exception as e:
        print(f"  [FAIL] FAILED: Dynamic window test failed: {e}")
        return False

    # CHECK 4: Error Handling on No Scenes Found
    print("\n[CHECK 4/14] Verifying Error Response on No Available Sentinel-1 Scenes...")
    try:
        # Invalid bbox in Antarctica far off grid where no recent S1 GRD scene exists
        impossible_bbox = (-179.9, -89.9, -179.8, -89.8)
        try:
            sentinel1_service.fetch_and_process_sar(
                bbox=impossible_bbox,
                start_date="2099-01-01",
                end_date="2099-01-02",
                polarization="VV"
            )
            print("  [FAIL] FAILED: Expected RuntimeError on no scenes found, but call succeeded.")
            return False
        except RuntimeError as rerr:
            print(f"  [OK] VERIFIED: Caught expected clear error message: '{rerr}'")
    except Exception as e:
        print(f"  [FAIL] Unexpected error during missing scene test: {e}")
        return False

    # CHECK 5 & 6: Sentinel-1 API request & Real raster response
    print("\n[CHECK 5-6/14] Verifying Process API Request & Real Raster Response...")
    try:
        process_res = sentinel1_service.fetch_and_process_sar(
            bbox=bbox,
            start_date="2024-06-01",
            end_date="2024-06-30",
            polarization="VV",
            width=512,
            height=512
        )
        output_file = process_res["output_file"]
        acq_time = process_res["acquisition_time"]
        assert os.path.exists(output_file), f"Output file does not exist: {output_file}"
        assert process_res.get("source_catalogue") == "Copernicus Data Space Ecosystem", "Catalogue metadata missing"
        print(f"  [OK] VERIFIED: Process API response received & GeoTIFF written to: {output_file}")
    except Exception as e:
        print(f"  [FAIL] FAILED: API Request or Raster response error: {e}")
        return False

    # CHECK 7 to 13: Detailed GeoTIFF Inspection with Rasterio
    print("\n[CHECK 7-13/14] Inspecting Exported GeoTIFF Metadata & Pixel Integrity with Rasterio...")
    try:
        import rasterio
        with rasterio.open(output_file) as src:
            w, h = src.width, src.height
            crs = src.crs
            transform = src.transform
            bounds = src.bounds
            data = src.read(1)

            # CHECK 7: 100% finite pixel validation
            finite_mask = np.isfinite(data) & (data != -9999.0)
            finite_count = int(np.count_nonzero(finite_mask))
            total_count = int(data.size)
            valid_pct = (finite_count / total_count) * 100.0
            print(f"  [CHECK 7/14] 100% Finite Pixel Validation: {finite_count} / {total_count} ({valid_pct:.2f}%)")
            assert finite_count == total_count, f"Raster contains invalid/nodata pixels ({finite_count}/{total_count})"

            # CHECK 8: CRS
            print(f"  [CHECK 8/14] CRS Verification: {crs} (EPSG:4326)")
            assert str(crs) == "EPSG:4326", f"CRS mismatch: expected EPSG:4326, got {crs}"

            # CHECK 9: Affine Transform
            print(f"  [CHECK 9/14] Affine Transform Verification: {transform}")
            assert transform.a != 0 and transform.e != 0, "Invalid affine transform scale"

            # CHECK 10: Geographic Bounds
            print(f"  [CHECK 10/14] Geographic Bounds Verification: {bounds}")
            assert bounds.left < bounds.right and bounds.bottom < bounds.top, "Invalid geographic bounds"

            # CHECK 11: Acquisition Timestamp
            print(f"  [CHECK 11/14] Acquisition Timestamp Verification: {acq_time}")
            assert acq_time and "T" in acq_time, f"Invalid acquisition timestamp format: {acq_time}"

            # CHECK 12: Output GeoTIFF readability with Rasterio
            print(f"  [CHECK 12/14] Output GeoTIFF Readability: Dimensions {w} x {h}, Bands: {src.count}, Dtype: {src.dtypes[0]}")
            assert w == 512 and h == 512 and src.count == 1, "Dimensions or band count mismatch"

            # CHECK 13: Preprocessing output (dB stats) & No NaNs
            min_db = float(data.min())
            max_db = float(data.max())
            mean_db = float(data.mean())
            nan_count = int(np.count_nonzero(np.isnan(data)))
            inf_count = int(np.count_nonzero(np.isinf(data)))
            print(f"  [CHECK 13/14] Preprocessing Output Stats (dB): Min={min_db:.4f}, Max={max_db:.4f}, Mean={mean_db:.4f} | NaNs={nan_count}, Infs={inf_count}")
            assert -50.0 <= min_db <= 0.0, f"Unreasonable min dB: {min_db}"
            assert -30.0 <= max_db <= 20.0, f"Unreasonable max dB: {max_db}"
            assert nan_count == 0 and inf_count == 0, "GeoTIFF contains NaN or Inf values!"

            # CHECK 14: PNG Preview & Thumbnail Existence and Quality
            preview_file = process_res.get("preview_file")
            thumbnail_file = process_res.get("thumbnail_file")
            print(f"\n[CHECK 14/14] Verifying SAR Preview & Thumbnail PNG Generation...")
            assert preview_file and os.path.exists(preview_file), f"Preview PNG file does not exist: {preview_file}"
            assert thumbnail_file and os.path.exists(thumbnail_file), f"Thumbnail PNG file does not exist: {thumbnail_file}"
            
            from app.services.sar_visualization import sar_visualization_service
            val_res = sar_visualization_service.validate_preview_image(Path(preview_file), expected_width=w, expected_height=h)
            assert val_res["valid"] is True, "Preview validation failed"
            print("  [OK] VERIFIED: Both Preview PNG and Thumbnail PNG exist and pass non-destructive visualization quality check.")

    except Exception as e:
        print(f"  [FAIL] FAILED: GeoTIFF/Preview verification failed: {e}")
        return False

    # SAFEGUARD 1: Isolated Real CDSE Integration Check (Non-blocking if live endpoint unreachable)
    print("\n-----------------------------------------------------------------------")
    print("REAL CDSE STAC LIVE INTEGRATION VERIFICATION (ISOLATED)")
    print("-----------------------------------------------------------------------")
    if cdse_authenticated:
        try:
            live_res = sentinel1_service.fetch_and_process_sar(bbox=bbox) # Dynamic latest query
            print(f"  [REAL INTEGRATION] STATUS: VERIFIED")
            print(f"  [REAL INTEGRATION] Product ID: {live_res.get('source_product_id')}")
            print(f"  [REAL INTEGRATION] Platform: {live_res.get('platform')}")
            print(f"  [REAL INTEGRATION] Acquisition Time: {live_res.get('acquisition_time')}")
            print(f"  [REAL INTEGRATION] Dynamic Search: {live_res.get('is_latest_available')}")
        except Exception as e:
            print(f"  [REAL INTEGRATION] STATUS: SKIPPED / BLOCKED ({e})")
    else:
        print("  [REAL INTEGRATION] STATUS: SKIPPED / BLOCKED (CDSE OAuth credentials not set)")

    print("\n=======================================================================")
    print("ALL PHASE 1 VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=======================================================================\n")
    return True

def test_phase1_all():
    assert run_phase1_tests() is True

if __name__ == "__main__":
    success = run_phase1_tests()
    sys.exit(0 if success else 1)
