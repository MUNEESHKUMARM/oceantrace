import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    PROJECT_NAME: str = "OceanTrace AI — Maritime Oil Spill Intelligence Backend"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    # CDSE / Sentinel Hub OAuth Credentials
    CDSE_CLIENT_ID: str = os.getenv("CDSE_CLIENT_ID", "")
    CDSE_CLIENT_SECRET: str = os.getenv("CDSE_CLIENT_SECRET", "")
    CDSE_TOKEN_URL: str = os.getenv(
        "CDSE_TOKEN_URL",
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
    )
    CDSE_BASE_URL: str = os.getenv(
        "CDSE_BASE_URL", "https://sh.dataspace.copernicus.eu"
    )
    CDSE_STAC_URL: str = os.getenv(
        "CDSE_STAC_URL", "https://stac.dataspace.copernicus.eu/v1"
    )

    # Sentinel-1 Search Defaults
    SENTINEL_SEARCH_DAYS: int = int(os.getenv("SENTINEL_SEARCH_DAYS", "7"))
    SENTINEL_SEARCH_FALLBACK_DAYS: list = [14, 30]

    # AISStream Live AIS Collector Settings
    AISSTREAM_API_KEY: str = os.getenv("AISSTREAM_API_KEY", "")
    AISSTREAM_WS_URL: str = os.getenv("AISSTREAM_WS_URL", "wss://stream.aisstream.io/v0/stream")
    
    # OceanTrace Verified Operating AOI (Lat: 18.0 -> 19.0, Lon: 71.5 -> 72.5)
    AOI_BOUNDING_BOXES: list = [
        [
            [18.0, 71.5],
            [19.0, 72.5]
        ]
    ]
    # AIS Correlation Settings (Engineering candidate retrieval threshold)
    AIS_CORRELATION_SEARCH_RADIUS_KM: float = float(os.getenv("AIS_CORRELATION_SEARCH_RADIUS_KM", "50.0"))

    # Phase 6.3 AIS Ranking Weights (Must be non-negative and sum to 1.0)
    AIS_RANKING_SPATIAL_WEIGHT: float = float(os.getenv("AIS_RANKING_SPATIAL_WEIGHT", "0.40"))
    AIS_RANKING_INTERSECTION_WEIGHT: float = float(os.getenv("AIS_RANKING_INTERSECTION_WEIGHT", "0.35"))
    AIS_RANKING_TEMPORAL_WEIGHT: float = float(os.getenv("AIS_RANKING_TEMPORAL_WEIGHT", "0.15"))
    AIS_RANKING_OBSERVATION_WEIGHT: float = float(os.getenv("AIS_RANKING_OBSERVATION_WEIGHT", "0.10"))

    # Phase 7 Configurable Operational Attention Thresholds
    SPILL_ATTENTION_AREA_THRESHOLD_KM2: float = float(os.getenv("SPILL_ATTENTION_AREA_THRESHOLD_KM2", "1.0"))
    ORIGIN_HIGH_ATTENTION_THRESHOLD: float = float(os.getenv("ORIGIN_HIGH_ATTENTION_THRESHOLD", "0.7"))
    AIS_HIGH_CORRELATION_THRESHOLD: float = float(os.getenv("AIS_HIGH_CORRELATION_THRESHOLD", "0.8"))
    ATTENTION_RULE_VERSION: str = os.getenv("ATTENTION_RULE_VERSION", "7.0.0-deterministic-v1")

    # Database Configuration (MySQL 8.0 / SQLAlchemy 2.x)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        os.getenv("MYSQL_URL", "mysql+pymysql://root:password@localhost:3306/oceantrace")
    )

    # Storage Paths
    BASE_DIR: Path = BASE_DIR
    DATA_INPUT_DIR: Path = BASE_DIR / "data" / "input"
    DATA_OUTPUT_DIR: Path = BASE_DIR / "data" / "output"
    MODEL_CHECKPOINT_DIR: Path = BASE_DIR / "models" / "checkpoints"

    def __init__(self):
        self.DATA_INPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.DATA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.MODEL_CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
