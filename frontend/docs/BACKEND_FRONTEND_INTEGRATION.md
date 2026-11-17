# OCEANTRACE AI — FRONTEND ↔ BACKEND INTEGRATION DOCUMENTATION

## 1. Architecture & End-to-End Data Flow

OceanTrace AI integrates a modern Next.js 16 frontend with a high-performance Python FastAPI backend. The backend is the single source of truth for all machine learning inference, SAR image processing, GIS polygon mapping, environmental oceanography, Lagrangian drift modeling, real-time AISStream collection, candidate vessel correlation/ranking, and automated investigation report generation.

```
                          ┌─────────────────────────────┐
                          │   Next.js 16 Frontend UI    │
                          │   (React / TypeScript)      │
                          └──────────────┬──────────────┘
                                         │
                         HTTP Requests   │  (getApiEndpoint)
                         (JSON / REST)   │  NEXT_PUBLIC_API_BASE_URL
                                         ▼
                          ┌─────────────────────────────┐
                          │    FastAPI Backend Server   │
                          │     (http://localhost:8000) │
                          └──────────────┬──────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
  Phase 1–5 Pipeline           Phase 6.1 AIS Collector           Phase 7 Report Engine
 (Sentinel-1, PyTorch,          (Live WebSocket Stream)         (Structured JSON & MD,
 ERA5, CMEMS, OpenDrift)                 │                       Operational Attention)
                                         ▼
                                MySQL 8.0 / SQLite DB
```

---

## 2. API Base URL Resolution & `/api/api` Duplication Prevention

To prevent duplicate path segments (`/api/api/...`), the centralized API client in [`lib/api.ts`](file:///g:/SIH/oceantrace-ai/lib/api.ts) uses a safe URL joining helper `getApiEndpoint(path)`:

- **Base URL Priority**: `process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'`
- **URL Normalization**: If the base URL ends with `/api` and the endpoint path starts with `/api/`, the redundant `/api` prefix is stripped automatically.

Example:
- Base: `http://localhost:8000/api`
- Path: `/ais/status`
- Resolved URL: `http://localhost:8000/api/ais/status`

---

## 3. Environment Variable Configuration (`.env.local`)

Public frontend environment parameters are configured in `.env.local` at the frontend root:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

> **Security Mandate**: `.env.local` contains ONLY public frontend variables starting with `NEXT_PUBLIC_`. All server-side secrets (`AISSTREAM_API_KEY`, database credentials, CDSE secrets) remain strictly inside `backend/.env`. `.env.local` is ignored by Git in `.gitignore`.

---

## 4. API Endpoint Contract Mapping

| Phase | Backend Endpoint | HTTP Method | API Function (`lib/api.ts`) | UI Component / Page |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | `/api/sentinel1/process` | POST | `processSentinel1SAR(params)` | LeftPipeline / Dashboard |
| **Phase 2** | `/api/detection/run` | POST | `runOilDetection(geotiffPath)` | LeftPipeline / Analysis |
| **Phase 1-5 Pipeline** | `/api/detection/run-pipeline` | POST | `runFullPipeline(params)` | Dashboard / Map / KPIBar |
| **Phase 6.1** | `/api/ais/status` | GET | `getAISCollectorStatus()` | TopNav / RightVesselPanel |
| **Phase 6.1** | `/api/ais/recent` | GET | `getRecentAISPositions(limit)` | Vessels Page |
| **Phase 6.2** | `/api/ais/correlate` | POST | `correlateAISVessels(sceneId)` | RightVesselPanel / Vessels Page |
| **Phase 6.3** | `/api/ais/rank` | POST | `rankAISCandidates(sceneId)` | RightVesselPanel / Vessels Page |
| **Phase 7** | `/api/investigation/report` | POST | `generateInvestigationReport(sceneId)` | Reports Page / Dashboard |
| **Phase 7** | `/api/investigation/status` | GET | `getInvestigationStatus(sceneId)` | TopNav / Reports Page |

---

## 5. Response Typing & Alignment

All backend Pydantic models are mirrored in TypeScript interfaces in [`types/index.ts`](file:///g:/SIH/oceantrace-ai/types/index.ts):
- `AISCollectorStatus`
- `AISVesselPosition`
- `AISCorrelationResponse` & `AISCorrelationCandidate`
- `AISRankingResponse` & `AISRankedCandidate`
- `InvestigationReportResponse` & `InvestigationStatusResponse`
- `OperationalAlert`

---

## 6. Zero vs Unavailable Semantics

The frontend strictly distinguishes valid zero values from API unavailability:
- **`candidate_count = 0`**: Displays "0 candidates identified" (valid response for scenes without origin/candidates).
- **`origin_available = false`**: Displays "Origin zone unavailable" (valid response for unconditioned drift simulation).
- **API Failure / Network Error**: Displays "Data Unavailable / Backend Connection Error" rather than displaying zero or hardcoded mock data.

---

## 7. Phase 6.1 Live AIS Background Collector Access Pattern

Phase 6.1 operates as an autonomous backend background service. The frontend does **NOT** connect directly to `wss://stream.aisstream.io` or control collector lifecycle. It reads live health telemetry via `getAISCollectorStatus()` (`GET /api/ais/status`) and populates the status indicator in `TopNav`.

---

## 8. Scene Consistency

All scene-dependent API calls explicitly accept and propagate `sceneId`. When switching scenes, the frontend invalidates stale state to prevent displaying cross-scene data mismatches.

---

## 9. Local Development & Production Setup

### Local Development
1. Start FastAPI Backend:
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload --port 8000
   ```
2. Start Next.js Frontend:
   ```bash
   npm run dev
   ```
3. Open `http://localhost:3000`.

### Production Deployment
Set `NEXT_PUBLIC_API_BASE_URL` in production environment settings to point to the production backend API domain (e.g. `https://api.oceantrace.ai/api`).

---

## 10. State Synchronization and Stale Data Prevention

1. **Single Scene Source of Truth**:
   The backend API response for the currently selected `scene_id` is the single source of truth. The frontend does not synthesize, retain, or merge previous scene data.

2. **Scene State Reset Flow**:
   When launching a new real analysis (`runAnalysis()`) or demo mode (`runDemo()`), all scene-dependent states (`phase1Data`..`phase5Data`, `correlationResult`, `rankingResult`, `investigationReport`, `selectedVessel`, stage statuses, and map overlays) are immediately reset to clean initial states before requesting new data.

3. **Stale Async Response Protection**:
   An async request sequence identifier (`activeSceneIdRef`) is initialized at request start. Responses arriving out of order or from prior scene selections check `response.scene_id === selectedSceneId` and are safely discarded if a mismatch occurs.

4. **Zero vs Unavailable Distinction**:
   - `origin_available = false` -> Status rendered as **ORIGIN NOT AVAILABLE** (not loading, not 0%, not 72% confidence, not error).
   - `correlation_available = false` -> Status rendered as **CORRELATION NOT AVAILABLE**.
   - `ranking_available = false` -> Status rendered as **RANKING NOT AVAILABLE** (`topVesselValue = "—"`).
   - `attention_level = NO_EVENT` -> Status rendered as **NO EVENT**.

5. **Real Data vs Demo Mode Isolation**:
   Real Data Mode communicates exclusively with backend API endpoints. If an API call fails or returns unavailable, the UI renders "Data Unavailable" or "NOT AVAILABLE"—it NEVER falls back to demo mock objects or hardcoded 2024 dates.

---

## 11. Scene Metadata Synchronization

1. **Header Scene Identifier Source**:
   The header displays the canonical backend product/scene identifier (`phase1Data.output_filename.replace('_processed.tif', '')` or `pipelineResult.scene.id`). Stale identifiers like `sentinel1_1790187684_VV` are strictly excluded from Real Data Mode.

2. **Acquisition Date Source**:
   Header date display derives strictly from `phase1Data.acquisition_time` formatted using UTC date formatting (`toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' })`). For the production scene `S1D_IW_GRDH_1SDV_20260918T010238...`, this evaluates to **18 Sep 2026**.

3. **No Hardcoded Dates or System Clock Fallbacks**:
   - The scene date NEVER uses `new Date()` (today's date) or browser time for SAR acquisition.
   - The scene date NEVER uses filesystem modification time (`st_mtime`).
   - Hardcoded `2024-06-01` and `2024-06-30` request defaults were removed from API payload handlers, allowing backend STAC discovery to resolve the newest sensing acquisition.

4. **Multi-Page Consistency**:
   - Dashboard (`KPIBar.tsx`), Reports (`app/reports/page.tsx`), and Analysis (`app/analysis/page.tsx`) share the exact same backend acquisition timestamp and scene ID metadata without separate fallback dates.

