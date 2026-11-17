# OceanTrace AI — Phase 6.1 Real Live AISStream Collector Documentation

## 1. Overview & Purpose
Phase 6.1 implements the **Real Live AISStream Collector** for OceanTrace AI. The collector maintains a persistent, long-lived server-side WebSocket connection to AISStream.io, streams real-time AIS `PositionReport` vessel messages for the OceanTrace operating Area of Interest (AOI), validates and normalizes message payloads, persists records to the database, and exposes collector status and health telemetry through the backend API.

> **"AISStream is used here as a real-time AIS event source. AIS events are persisted by OceanTrace AI so that later Phase 6 correlation can inspect the locally retained history."**

> **"Live AIS collection does not establish spill causation or vessel responsibility."**

---

## 2. Live AIS Source & Connection Specifications
- **Data Provider:** AISStream.io Real-Time Open AIS Network
- **Official WebSocket Endpoint:** `wss://stream.aisstream.io/v0/stream`
- **Environment Variable:** `AISSTREAM_API_KEY` (loaded strictly from backend `.env`)
- **Security Rule:** The raw API key is never logged, exposed to the frontend, sent in API responses, or committed to Git.

---

## 3. OceanTrace AOI Bounding Boxes & Subscription Schema
The collector subscribes to the verified OceanTrace operating Area of Interest (AOI):
- **Latitude Range:** `18.0°N` to `19.0°N`
- **Longitude Range:** `71.5°E` to `72.5°E`

### Official Subscription Payload:
```json
{
  "APIKey": "<from environment>",
  "BoundingBoxes": [
    [
      [18.0, 71.5],
      [19.0, 72.5]
    ]
  ],
  "FilterMessageTypes": [
    "PositionReport"
  ]
}
```

---

## 4. Message Ingestion, Validation & Normalization
Incoming WebSocket messages are parsed and validated:
1. **JSON Decoding:** Validates text/binary WebSocket frames.
2. **Message Classification:** Distinguishes `SubscriptionConfirmation` from `PositionReport` events.
3. **Strict Parameter Validation:**
   - **MMSI:** Must be a non-empty, 9-digit numeric string.
   - **Latitude:** Must be numeric within $[-90.0, +90.0]$.
   - **Longitude:** Must be numeric within $[-180.0, +180.0]$.
   - **Valid Flag:** Respects `Valid` flag when present in AIS payload.
4. **Normalized Internal Schema:**
   - `mmsi`: Vessel identifier string
   - `timestamp_utc`: AIS-reported event timestamp (UTC)
   - `latitude`: Decimal degrees
   - `longitude`: Decimal degrees
   - `sog_knots`: Speed over ground in knots
   - `cog_degrees`: Course over ground in degrees ($0^\circ - 360^\circ$)
   - `true_heading`: True heading in degrees
   - `navigational_status`: AIS status integer
   - `position_accuracy`: High accuracy boolean flag
   - `source`: `"aisstream"`
   - `received_at_utc`: Backend receipt timestamp (UTC)

---

## 5. Database Persistence Model
Normalized records are persisted into the `ais_vessel_positions` table using SQLAlchemy 2.0 (MySQL 8.0 with graceful fallback engine):

### Table Schema (`ais_vessel_positions`):
| Column Name | Type | Options | Description |
|---|---|---|---|
| `id` | Integer | Primary Key, Auto Increment | Primary key surrogate ID |
| `mmsi` | String(20) | Indexed, Not Null | 9-digit vessel MMSI |
| `timestamp_utc` | DateTime(tz) | Indexed, Not Null | AIS-reported UTC timestamp |
| `latitude` | Float | Not Null | Decimal latitude |
| `longitude` | Float | Not Null | Decimal longitude |
| `sog_knots` | Float | Nullable | Speed Over Ground (knots) |
| `cog_degrees` | Float | Nullable | Course Over Ground (degrees) |
| `true_heading` | Float | Nullable | True Heading (degrees) |
| `navigational_status` | Integer | Nullable | AIS Navigational Status code |
| `position_accuracy` | Boolean | Nullable | Position accuracy flag |
| `ais_message_type` | String(50) | Not Null | AIS message class ("PositionReport") |
| `source` | String(50) | Not Null | Ingestion source ("aisstream") |
| `received_at_utc` | DateTime(tz) | Indexed, Not Null | Backend receipt UTC timestamp |
| `created_at_utc` | DateTime(tz) | Not Null | Record creation UTC timestamp |

### Indexes:
- `idx_ais_time_lat_lon`: `(timestamp_utc, latitude, longitude)`
- `idx_ais_mmsi_time`: `(mmsi, timestamp_utc)`

---

## 6. Reconnect Strategy & Resilience
- **Exponential Backoff:** Initial reconnect delay $2\text{ s}$, doubling on consecutive failures up to max $60\text{ s}$, with random jitter ($0.1 - 1.0\text{ s}$).
- **Resubscription:** Re-transmits full subscription payload immediately upon reconnect.
- **Graceful Lifecycle:** Runs as a non-blocking background service managed by FastAPI lifespan handlers. Does not crash main thread or API server on network errors.

---

## 7. Status Endpoint Telemetry
### `GET /api/ais/status`
```json
{
  "service": "AISStream",
  "available": true,
  "connected": true,
  "subscription_active": true,
  "last_message_at": "2026-09-23T01:15:20Z",
  "last_position_at": "2026-09-23T01:15:20Z",
  "messages_received": 142,
  "messages_stored": 138,
  "messages_rejected": 4,
  "tracked_mmsi_count": 29,
  "last_error": null
}
```

---

## 8. Limitations & Scope Constraints
1. **Phase 6.1 Scope Only:** Does not perform spatial/temporal vessel correlation, candidate scoring, or vessel ranking (reserved for Phase 6.2/6.3).
2. **Current Production Scene Separation:** Current Sentinel-1 scene has 0 predicted oil pixels; live AIS position collection runs independently without creating fabricated spill associations or vessel attributions.
