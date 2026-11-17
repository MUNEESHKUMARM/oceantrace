import os
import sys
import json
import math
import time
import random
import logging
import asyncio
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Set, Tuple, List

import websockets

from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.models.ais import AISVesselPosition
from app.schemas.ais import AISPositionReport, AISCollectorStatus

logger = logging.getLogger("oceantrace.ais_service")
logger.setLevel(logging.INFO)


class AISStreamService:
    """
    Phase 6.1 Real-Time Live AISStream Collector Service.
    Connects to AISStream.io WebSocket API (wss://stream.aisstream.io/v0/stream),
    subscribes to OceanTrace AOI PositionReport messages, validates/normalizes events,
    persists records into MySQL database via SQLAlchemy, and maintains collector status metrics.
    """

    def __init__(self):
        self.ws_url = settings.AISSTREAM_WS_URL
        self.api_key = settings.AISSTREAM_API_KEY
        self.aoi_boxes = settings.AOI_BOUNDING_BOXES

        self._running = False
        self._connected = False
        self._subscription_active = False
        self._collector_task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

        self._messages_received = 0
        self._messages_stored = 0
        self._messages_rejected = 0
        self._tracked_mmsis: Set[str] = set()

        self._last_message_at: Optional[datetime] = None
        self._last_position_at: Optional[datetime] = None
        self._last_error: Optional[str] = None

        # Recent deduplication cache: (mmsi, iso_timestamp, lat, lon) -> receipt_timestamp
        self._recent_dedup_cache: Dict[Tuple[str, str, float, float], float] = {}

    @property
    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def build_subscription_message(self) -> Dict[str, Any]:
        """Constructs official AISStream subscription payload for OceanTrace AOI."""
        return {
            "APIKey": settings.AISSTREAM_API_KEY,
            "BoundingBoxes": settings.AOI_BOUNDING_BOXES,
            "FilterMessageTypes": ["PositionReport"],
        }

    def parse_ais_timestamp(self, ts_raw: Any) -> datetime:
        """Parse raw AIS timestamp to UTC datetime safely."""
        if isinstance(ts_raw, str) and ts_raw:
            try:
                dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass
        return datetime.now(timezone.utc)

    def validate_and_normalize_message(self, raw_data: Any) -> Optional[AISPositionReport]:
        """
        Validates raw AIS message dictionary or JSON string from WebSocket.
        Extracts MMSI, coordinates, speed, course, and heading.
        Rejects malformed or out-of-bounds records safely.
        """
        if isinstance(raw_data, (bytes, bytearray)):
            try:
                raw_data = raw_data.decode("utf-8")
            except Exception:
                self._messages_rejected += 1
                return None

        if isinstance(raw_data, str):
            try:
                msg_obj = json.loads(raw_data)
            except Exception as e:
                self._messages_rejected += 1
                logger.debug(f"[AIS] Discarded non-JSON WebSocket frame: {e}")
                return None
        elif isinstance(raw_data, dict):
            msg_obj = raw_data
        else:
            self._messages_rejected += 1
            return None

        msg_type = msg_obj.get("MessageType")
        meta = msg_obj.get("MetaData", {})
        message_body = msg_obj.get("Message", {})
        pos_report = message_body.get("PositionReport", {})

        # Handle SubscriptionConfirmation or non-PositionReport messages
        if msg_type == "SubscriptionConfirmation":
            self._subscription_active = True
            logger.info("[AIS] Subscription confirmed by AISStream server.")
            return None

        if msg_type != "PositionReport" and not pos_report:
            # Check if fields exist directly in meta or message root
            if "MMSI" not in meta and "UserID" not in pos_report:
                self._messages_rejected += 1
                return None

        # Extract MMSI
        raw_mmsi = meta.get("MMSI") or pos_report.get("UserID") or msg_obj.get("MMSI")
        if not raw_mmsi:
            self._messages_rejected += 1
            logger.debug("[AIS] PositionReport rejected: missing MMSI.")
            return None

        mmsi_str = str(raw_mmsi).strip()
        if not mmsi_str or len(mmsi_str) < 5 or not mmsi_str.isdigit():
            self._messages_rejected += 1
            logger.debug(f"[AIS] PositionReport rejected: invalid MMSI format '{mmsi_str}'.")
            return None

        # Extract Coordinates
        raw_lat = meta.get("latitude") if "latitude" in meta else pos_report.get("Latitude")
        raw_lon = meta.get("longitude") if "longitude" in meta else pos_report.get("Longitude")

        if raw_lat is None or raw_lon is None:
            self._messages_rejected += 1
            logger.debug(f"[AIS] PositionReport for MMSI {mmsi_str} rejected: missing coordinates.")
            return None

        try:
            lat = float(raw_lat)
            lon = float(raw_lon)
        except (ValueError, TypeError):
            self._messages_rejected += 1
            logger.debug(f"[AIS] PositionReport for MMSI {mmsi_str} rejected: non-numeric coordinates.")
            return None

        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            self._messages_rejected += 1
            logger.debug(f"[AIS] PositionReport for MMSI {mmsi_str} rejected: out-of-bounds coordinates ({lat}, {lon}).")
            return None

        # Validity flag check
        valid_flag = pos_report.get("Valid", True)
        if valid_flag is False:
            self._messages_rejected += 1
            logger.debug(f"[AIS] PositionReport for MMSI {mmsi_str} rejected: valid_flag is False.")
            return None

        # Extract Optional Motion Metrics
        raw_sog = pos_report.get("Sog")
        raw_cog = pos_report.get("Cog")
        raw_heading = pos_report.get("TrueHeading")
        nav_status = pos_report.get("NavigationalStatus")
        accuracy = pos_report.get("PositionAccuracy")

        sog = float(raw_sog) if raw_sog is not None and math.isfinite(float(raw_sog)) else None
        cog = float(raw_cog) if raw_cog is not None and math.isfinite(float(raw_cog)) else None
        true_heading = float(raw_heading) if raw_heading is not None and math.isfinite(float(raw_heading)) and float(raw_heading) < 511 else None

        ts_utc = self.parse_ais_timestamp(meta.get("time_utc") or pos_report.get("Timestamp"))
        received_utc = datetime.now(timezone.utc)

        try:
            return AISPositionReport(
                mmsi=mmsi_str,
                timestamp_utc=ts_utc,
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                sog_knots=round(sog, 2) if sog is not None else None,
                cog_degrees=round(cog, 1) if cog is not None else None,
                true_heading=round(true_heading, 1) if true_heading is not None else None,
                navigational_status=int(nav_status) if nav_status is not None else None,
                position_accuracy=bool(accuracy) if accuracy is not None else None,
                valid_position=True,
                ais_message_type="PositionReport",
                source="aisstream",
                received_at_utc=received_utc,
            )
        except Exception as ve:
            self._messages_rejected += 1
            logger.debug(f"[AIS] Normalization failed for MMSI {mmsi_str}: {ve}")
            return None

        return None

    def is_duplicate(self, report: AISPositionReport) -> bool:
        """Deduplication check based on MMSI, rounded coordinates, and timestamp."""
        key = (report.mmsi, report.timestamp_utc.strftime("%Y-%m-%dT%H:%M:%S"), report.latitude, report.longitude)
        now = time.time()

        # Clean old cache items older than 30s
        expired_keys = [k for k, v in self._recent_dedup_cache.items() if now - v > 30.0]
        for k in expired_keys:
            del self._recent_dedup_cache[k]

        if key in self._recent_dedup_cache:
            return True

        self._recent_dedup_cache[key] = now
        return False

    def persist_position(self, report: AISPositionReport) -> bool:
        """Persists normalized AIS position into database table ais_vessel_positions."""
        if self.is_duplicate(report):
            logger.debug(f"[AIS] Duplicate position for MMSI {report.mmsi} skipped.")
            return False

        try:
            db = SessionLocal()
            try:
                db_item = AISVesselPosition(
                    mmsi=report.mmsi,
                    timestamp_utc=report.timestamp_utc,
                    latitude=report.latitude,
                    longitude=report.longitude,
                    sog_knots=report.sog_knots,
                    cog_degrees=report.cog_degrees,
                    true_heading=report.true_heading,
                    navigational_status=report.navigational_status,
                    position_accuracy=report.position_accuracy,
                    ais_message_type=report.ais_message_type,
                    source=report.source,
                    received_at_utc=report.received_at_utc,
                )
                db.add(db_item)
                db.commit()
                self._messages_stored += 1
                self._tracked_mmsis.add(report.mmsi)
                self._last_position_at = report.received_at_utc
                logger.debug(f"[AIS] Stored position for MMSI {report.mmsi} ({report.latitude}, {report.longitude}).")
                return True
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[AIS] Persistence failed for MMSI {report.mmsi}: {str(e)}")
            self._last_error = f"Database insertion warning: {str(e)}"
            return False

    async def _run_collector_loop(self):
        """
        Long-lived asynchronous WebSocket consumer loop with exponential backoff and automatic reconnect.
        """
        if not self.is_available:
            logger.warning("[AIS] AISSTREAM_API_KEY is missing or empty. Collector disabled.")
            self._last_error = "AISSTREAM_API_KEY configuration missing in backend environment"
            return

        init_db()

        backoff_delay = 2.0
        max_backoff = 60.0

        sub_message = {
            "APIKey": self.api_key,
            "BoundingBoxes": self.aoi_boxes,
            "FilterMessageTypes": ["PositionReport"],
        }

        logger.info(f"[AIS] Collector service initializing for AOI bounds {self.aoi_boxes}...")

        while self._running:
            try:
                logger.info(f"[AIS] Connecting to AISStream WebSocket: {self.ws_url}...")
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=10,
                ) as ws:
                    self._connected = True
                    self._subscription_active = False
                    self._last_error = None
                    logger.info("[AIS] WebSocket connected. Sending subscription message...")

                    # Authenticate & Subscribe
                    await ws.send(json.dumps(sub_message))
                    logger.info("[AIS] Subscription payload transmitted to AISStream.")

                    connected_start = time.time()

                    async for message in ws:
                        if not self._running:
                            break

                        self._messages_received += 1
                        self._last_message_at = datetime.now(timezone.utc)

                        # Parse & normalize
                        report = self.validate_and_normalize_message(message)
                        if report is not None:
                            self._subscription_active = True
                            self.persist_position(report)

                        # Reset backoff on stable session
                        if time.time() - connected_start > 10.0:
                            backoff_delay = 2.0

            except asyncio.CancelledError:
                logger.info("[AIS] Collector loop cancelled.")
                break
            except Exception as e:
                self._connected = False
                self._subscription_active = False
                self._last_error = f"WebSocket error: {str(e)}"
                logger.warning(f"[AIS] WebSocket connection error: {str(e)}")

                if not self._running:
                    break

                # Exponential backoff with jitter
                jitter = random.uniform(0.1, 1.0)
                actual_delay = min(max_backoff, backoff_delay + jitter)
                logger.info(f"[AIS] Reconnecting in {actual_delay:.1f} seconds...")
                await asyncio.sleep(actual_delay)
                backoff_delay = min(max_backoff, backoff_delay * 1.5)

        self._connected = False
        self._subscription_active = False
        logger.info("[AIS] Collector loop stopped cleanly.")

    def start_collector(self):
        """Starts background collector thread."""
        if self._running:
            logger.info("[AIS] Collector thread is already running.")
            return

        if not self.is_available:
            logger.warning("[AIS] Collector start skipped: AISSTREAM_API_KEY is not configured.")
            return

        self._running = True

        def _thread_target():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(self._run_collector_loop())
            except Exception:
                pass
            finally:
                try:
                    self._loop.close()
                except Exception:
                    pass

        self._thread = threading.Thread(target=_thread_target, daemon=True, name="AISCollectorThread")
        self._thread.start()
        logger.info("[AIS] Background collector thread launched.")

    def stop_collector(self):
        """Gracefully stops background collector thread."""
        if not self._running:
            return

        logger.info("[AIS] Stopping background collector thread...")
        self._running = False
        self._connected = False
        self._subscription_active = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

        logger.info("[AIS] Collector service stopped cleanly.")

    def get_status(self) -> AISCollectorStatus:
        """Returns health and operational metrics without exposing secrets."""
        return AISCollectorStatus(
            service="AISStream",
            available=self.is_available,
            connected=self._connected,
            subscription_active=self._subscription_active,
            last_message_at=self._last_message_at.isoformat() if self._last_message_at else None,
            last_position_at=self._last_position_at.isoformat() if self._last_position_at else None,
            messages_received=self._messages_received,
            messages_stored=self._messages_stored,
            messages_rejected=self._messages_rejected,
            tracked_mmsi_count=len(self._tracked_mmsis),
            last_error=self._last_error,
        )


# Global singleton instance
ais_stream_service = AISStreamService()
