from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Index
from app.core.database import Base


class AISVesselPosition(Base):
    """
    Phase 6.1 AIS Vessel Position Persistence Model.
    Stores normalized, real-time AIS PositionReport messages ingested from AISStream.io.
    """

    __tablename__ = "ais_vessel_positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mmsi = Column(String(20), index=True, nullable=False)
    timestamp_utc = Column(DateTime(timezone=True), index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    sog_knots = Column(Float, nullable=True)
    cog_degrees = Column(Float, nullable=True)
    true_heading = Column(Float, nullable=True)
    navigational_status = Column(Integer, nullable=True)
    position_accuracy = Column(Boolean, nullable=True)
    ais_message_type = Column(String(50), default="PositionReport", nullable=False)
    source = Column(String(50), default="aisstream", nullable=False)
    received_at_utc = Column(DateTime(timezone=True), index=True, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at_utc = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_ais_time_lat_lon", "timestamp_utc", "latitude", "longitude"),
        Index("idx_ais_mmsi_time", "mmsi", "timestamp_utc"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "mmsi": self.mmsi,
            "timestamp_utc": self.timestamp_utc.isoformat() if self.timestamp_utc else None,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "sog_knots": self.sog_knots,
            "cog_degrees": self.cog_degrees,
            "true_heading": self.true_heading,
            "navigational_status": self.navigational_status,
            "position_accuracy": self.position_accuracy,
            "ais_message_type": self.ais_message_type,
            "source": self.source,
            "received_at_utc": self.received_at_utc.isoformat() if self.received_at_utc else None,
        }
