import os
import logging
import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger("oceantrace.db")

Base = declarative_base()

db_url = settings.DATABASE_URL
fallback_db_path = settings.BASE_DIR / "data" / "oceantrace.db"
fallback_db_path.parent.mkdir(parents=True, exist_ok=True)

# Create fallback engine
fallback_engine = create_engine(
    f"sqlite:///{fallback_db_path}",
    connect_args={"check_same_thread": False},
)

primary_engine = None
try:
    if "mysql" in db_url:
        primary_engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=10,
            max_overflow=20,
        )
    else:
        primary_engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
        )
except Exception as e:
    logger.warning(f"Could not initialize primary database engine ({db_url}): {e}. Using fallback SQLite storage.")

active_engine = primary_engine if primary_engine is not None else fallback_engine
PrimarySession = sessionmaker(autocommit=False, autoflush=False, bind=active_engine)
FallbackSession = sessionmaker(autocommit=False, autoflush=False, bind=fallback_engine)


def init_db():
    """Create database tables if they do not exist."""
    try:
        Base.metadata.create_all(bind=active_engine)
        logger.info("Database tables initialized successfully on primary engine.")
    except Exception as e:
        logger.warning(f"Primary database initialization warning ({e}). Initializing fallback SQLite database.")
        try:
            Base.metadata.create_all(bind=fallback_engine)
            logger.info("Fallback SQLite database initialized successfully.")
        except Exception as fe:
            logger.error(f"Fallback database initialization failed: {fe}")


def SessionLocal() -> Session:
    """Returns an active database session, using primary engine or falling back cleanly."""
    if primary_engine is not None:
        try:
            sess = PrimarySession()
            sess.execute(text("SELECT 1"))
            return sess
        except Exception as e:
            logger.debug(f"Primary MySQL session test failed ({e}), switching session to fallback SQLite.")
            sess.close()
    
    # Ensure fallback tables exist
    try:
        Base.metadata.create_all(bind=fallback_engine)
    except Exception:
        pass
    return FallbackSession()


def get_db():
    """FastAPI dependency for database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
