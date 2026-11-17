# OceanTrace AI — Reports Page Real Data & Actions Documentation

## 1. Overview
The Reports page (`app/reports/page.tsx`) provides official maritime surveillance and incident investigation reports generated directly from backend Phase 7 (`/api/investigation-report/{scene_id}`). 

This document details the real-data purification, scene state synchronization, JSON/PDF export capabilities, and interactive multi-channel sharing features.

---

## 2. Single Source of Truth & Real Data Binding
- **State Provider**: `SceneContext` (`useSceneContext()`).
- **Active Scene Binding**: The report dynamically fetches `/api/investigation-report/{activeSceneId}` when `isDemo === false`.
- **Scene Consistency Invariant**: `Reports.scene_id === activeSceneId`. Changing scenes instantly clears stale report data and loads the active backend report.
- **Zero vs. Unavailable Semantics**:
  - `spill_region_count: 0`, `predicted_oil_pixels: 0` $\rightarrow$ Rendered as `0 regions`, `0.00 km²`, `NO SPILL DETECTED`.
  - `origin_available: false` $\rightarrow$ Rendered as `ORIGIN NOT AVAILABLE`. No fake coordinates or confidence percentages.
  - `candidate_count: 0`, `ranking_available: false` $\rightarrow$ Rendered as `NO AIS CANDIDATES IDENTIFIED — RANKING NOT AVAILABLE`. All candidate rows and factor analysis panels are hidden.
  - `coastal_threats` empty $\rightarrow$ Rendered as `NO COASTAL THREATS IDENTIFIED`.
  - `attention_level: "NO_EVENT"` $\rightarrow$ Operational risk badge rendered as `NO_EVENT` with `ALERT: NONE`.

---

## 3. Real / Demo Mode Isolation
- **Real Data Mode (`isDemo === false`)**: Displays ONLY verified backend Phase 7 payloads. If backend response is empty or fails, displays `REPORT DATA UNAVAILABLE` with zero mock fallback.
- **Demo Mode (`isDemo === true`)**: Displays isolated demo incident fixtures for presentation and offline testing. Switching between modes immediately clears transient state.

---

## 4. Export & Action Capabilities

### A. Export JSON
- **Action**: Generates structured downloadable JSON file.
- **Content**: Full `InvestigationReportResponse` schema including `identification`, `sar_detection`, `spill_characteristics`, `environmental_conditions`, `probable_origin`, `ais_correlation`, `operational_alert`, and `disclaimer`.
- **Filename Pattern**: `investigation_report_<safe_scene_id>.json`.

### B. Export PDF
- **Action**: Opens structured printable report in a clean window for PDF printing (`window.print()`).
- **Content**: Formatted printable DOM template containing all current report sections, operational badges, acquisition timestamps, and scientific disclaimers.
- **Filename Pattern**: `investigation_report_<safe_scene_id>.pdf`.

### C. Share Report Modal (`ShareReportModal.tsx`)
- **System Share**: Triggers native `navigator.share()` on supported mobile/desktop web browsers.
- **WhatsApp**: Encodes safe summary link (`https://api.whatsapp.com/send?text=...`) without claiming legal causation or vessel responsibility.
- **Email**: Triggers `mailto:` link with pre-filled subject line and body summary.
- **Copy Report Link**: Copies exact report URL to clipboard (`navigator.clipboard.writeText`) with instant `COPIED` visual feedback.
- **Direct Downloads**: Embedded buttons for JSON and PDF downloads directly inside the modal.

---

## 5. Security & Data Integrity
- **No Secret Leakage**: Share text and URLs contain strictly public scene metadata and web links. No API keys, filesystem paths, or credentials are exposed.
- **Scientific Disclaimer**: Included across UI, JSON, PDF exports, and share content stating that satellite SAR findings are probabilistic and require physical verification.
