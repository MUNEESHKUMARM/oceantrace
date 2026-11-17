import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from contextlib import asynccontextmanager
from app.api import health, sentinel1, detection, spill_mapping, environment, drift, ais, investigation
from app.services.ais_stream_service import ais_stream_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    # Startup: Start AISStream Live AIS Collector
    logger = logging.getLogger("oceantrace.main")
    logger.info("Starting OceanTrace AI backend application...")
    if ais_stream_service.is_available:
        ais_stream_service.start_collector()
    else:
        logger.warning("AISStream API key missing in environment. Collector skipped.")
    yield
    # Shutdown: Stop AISStream Collector cleanly
    logger.info("Shutting down OceanTrace AI backend application...")
    ais_stream_service.stop_collector()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="OceanTrace AI — Sentinel-1 SAR Access, AI Detection, Spill Mapping, Environmental Analysis, Drift Modelling & Live AIS API",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health.router, prefix=settings.API_PREFIX)
app.include_router(sentinel1.router, prefix=settings.API_PREFIX)
app.include_router(detection.router, prefix=settings.API_PREFIX)
app.include_router(spill_mapping.router, prefix=settings.API_PREFIX)
app.include_router(environment.router, prefix=settings.API_PREFIX)
app.include_router(drift.router, prefix=settings.API_PREFIX)
app.include_router(ais.router, prefix=settings.API_PREFIX)
app.include_router(investigation.router, prefix=settings.API_PREFIX)

# Dual prefix compatibility (/api and /api/v1)
if settings.API_PREFIX != "/api/v1":
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(sentinel1.router, prefix="/api/v1")
    app.include_router(detection.router, prefix="/api/v1")
    app.include_router(spill_mapping.router, prefix="/api/v1")
    app.include_router(environment.router, prefix="/api/v1")
    app.include_router(drift.router, prefix="/api/v1")
    app.include_router(ais.router, prefix="/api/v1")
    app.include_router(investigation.router, prefix="/api/v1")



@app.get("/")
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": f"{settings.API_PREFIX}/docs",
        "health": f"{settings.API_PREFIX}/health"
    }
