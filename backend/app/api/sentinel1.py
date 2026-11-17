from fastapi import APIRouter, HTTPException, status
from typing import List
from app.schemas.sentinel1 import (
    AuthTestResponse,
    Sentinel1SearchRequest,
    Sentinel1SceneMetadata,
    Sentinel1ProcessRequest,
    Sentinel1ProcessResponse,
)
from app.services.cdse_auth import get_access_token, CDSEAuthenticationError
from app.services.sentinel1_service import sentinel1_service

router = APIRouter(prefix="/sentinel1", tags=["Sentinel-1 SAR"])


@router.get("/auth-test", response_model=AuthTestResponse)
def test_cdse_authentication():
    """
    Tests OAuth2 client credentials authentication with Copernicus Data Space Ecosystem.
    Does NOT return token or client secret.
    """
    try:
        token = get_access_token()
        if token:
            return AuthTestResponse(
                authenticated=True,
                service="Copernicus Data Space Sentinel Hub",
                message="Successfully authenticated with CDSE OAuth2 endpoints."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed: No token returned."
            )
    except CDSEAuthenticationError as e:
        return AuthTestResponse(
            authenticated=False,
            service="Copernicus Data Space Sentinel Hub",
            message=f"CDSE Auth Status: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected authentication test error: {str(e)}"
        )


@router.post("/search", response_model=List[Sentinel1SceneMetadata])
def search_sentinel1_scenes(request: Sentinel1SearchRequest):
    """
    Discovers available Sentinel-1 GRD SAR scenes in Copernicus STAC Catalog.
    """
    try:
        start_dt = request.start_date
        end_dt = request.end_date
        if not start_dt or not end_dt:
            import datetime
            from app.core.config import settings
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            days = getattr(settings, "SENTINEL_SEARCH_DAYS", 7)
            start_dt = (now_utc - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
            end_dt = now_utc.strftime("%Y-%m-%d")

        scenes = sentinel1_service.search_scenes(
            bbox=(request.bbox[0], request.bbox[1], request.bbox[2], request.bbox[3]),
            start_date=start_dt,
            end_date=end_dt,
            max_results=request.max_results,
        )
        return [Sentinel1SceneMetadata(**s) for s in scenes]
    except CDSEAuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/process", response_model=Sentinel1ProcessResponse)
def process_sentinel1_sar(request: Sentinel1ProcessRequest):
    """
    Requests Sentinel-1 GRD imagery from CDSE, executes SAR preprocessing
    (radiometric calibration, Lee speckle filtering, decibel scaling, GeoTIFF creation),
    and exports processed GeoTIFF to backend/data/output/.
    """
    try:
        result = sentinel1_service.fetch_and_process_sar(
            bbox=(request.bbox[0], request.bbox[1], request.bbox[2], request.bbox[3]),
            start_date=request.start_date,
            end_date=request.end_date,
            polarization=request.polarization,
            width=request.width,
            height=request.height,
        )
        return Sentinel1ProcessResponse(**result)
    except CDSEAuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


from fastapi.responses import FileResponse
from app.core.config import settings

@router.get("/preview/{image_id}")
def get_sentinel1_preview(image_id: str):
    """
    Returns human-viewable 8-bit SAR preview PNG or thumbnail image by ID or filename.
    """
    out_dir = settings.DATA_OUTPUT_DIR

    if image_id == "latest_thumbnail":
        thumb_files = sorted(out_dir.glob("*_thumbnail.png"), key=lambda p: p.stat().st_mtime, reverse=True)
        if thumb_files:
            return FileResponse(path=thumb_files[0], media_type="image/png")

    # 1. Exact file match
    candidate = out_dir / image_id
    if candidate.exists() and candidate.is_file():
        media_type = "image/png" if image_id.endswith(".png") else "application/octet-stream"
        return FileResponse(path=candidate, media_type=media_type)

    # 2. Add .png if missing
    if not image_id.endswith(".png"):
        candidate_png = out_dir / f"{image_id}.png"
        if candidate_png.exists():
            return FileResponse(path=candidate_png, media_type="image/png")

        # 3. Add _preview.png if missing
        candidate_prev = out_dir / f"{image_id}_preview.png"
        if candidate_prev.exists():
            return FileResponse(path=candidate_prev, media_type="image/png")

    # 4. Fallback: Return latest preview PNG if available
    png_files = sorted(out_dir.glob("*_preview.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    if png_files:
        return FileResponse(path=png_files[0], media_type="image/png")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"SAR preview image not found for image_id: {image_id}"
    )


