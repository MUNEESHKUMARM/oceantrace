import os
import sys
import json
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.sentinel1_service import sentinel1_service

def run_discovery():
    bbox = (71.5, 18.0, 72.5, 19.0)
    start_date = "2026-09-01"
    end_date = "2026-09-23"
    
    print("=== 1A. CDSE STAC DISCOVERY ===")
    print(f"Configured AOI: {bbox} (Offshore Mumbai)")
    print(f"Search Window: {start_date}T00:00:00Z to {end_date}T23:59:59Z")
    
    candidates = sentinel1_service.search_scenes(bbox=bbox, start_date=start_date, end_date=end_date, max_results=50)
    print(f"\nTotal candidate scenes returned by STAC search: {len(candidates)}")
    
    for idx, sc in enumerate(candidates):
        print(f"\nCandidate [{idx+1}]:")
        print(f"  Product ID          : {sc.get('id')}")
        print(f"  Platform            : {sc.get('satellite')}")
        print(f"  Acquisition Datetime: {sc.get('datetime')}")
        print(f"  Product Type        : {sc.get('product_type')}")
        print(f"  Polarization        : {sc.get('polarization')}")
        print(f"  BBOX (Candidate)    : {sc.get('bbox')}")
        
        cand_bbox = sc.get('bbox', [])
        intersects = False
        if len(cand_bbox) == 4:
            # Check overlap
            intersects = not (cand_bbox[2] < bbox[0] or cand_bbox[0] > bbox[2] or cand_bbox[3] < bbox[1] or cand_bbox[1] > bbox[3])
        print(f"  Intersects with AOI : {intersects}")

if __name__ == '__main__':
    run_discovery()
