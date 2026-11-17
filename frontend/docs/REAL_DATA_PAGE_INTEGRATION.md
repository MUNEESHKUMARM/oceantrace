# Real Data Page Integration & Scene Synchronization Documentation

## Overview

This document specifies the Real Run Scene Synchronization architecture implemented for OceanTrace AI. Every successful execution of **RUN REAL ANALYSIS** synchronizes all frontend pages (`Dashboard`, `Analysis`, `Vessels`, `Reports`) with the backend-returned Sentinel-1 SAR scene.

---

## 1. Core Synchronization Rules

1. **Backend as Single Source of Truth**:
   - The scene identifier (`scene_id`) and acquisition timestamp (`acquisition_time`) are strictly derived from the backend response.
   - The frontend never invents synthetic scene IDs, browser clock fallbacks, or filesystem timestamps.

2. **Same-Scene Reruns (CASE A)**:
   - When no newer Sentinel-1 acquisition exists, the backend legitimately returns the latest available acquisition.
   - Re-clicking **RUN REAL ANALYSIS** refreshes and rebinds all outputs to the same scene without altering acquisition timestamps or fabricating scene IDs.

3. **New-Scene Replacement (CASE B)**:
   - When a newer Sentinel-1 acquisition is processed by the backend, all previous scene-dependent state is invalidated and replaced atomically across all pages.

4. **Stale Response Protection**:
   - Every analysis request generates a unique request generation ID (`activeRunGenerationId` / `activeSceneIdRef`).
   - Responses arriving after a newer run has initiated are automatically discarded before state mutation.

5. **Phase 6.1 AIS Background Collector Isolation**:
   - The live AIS collector operates as an independent backend service.
   - The **RUN REAL ANALYSIS** button does not restart or interrupt the AIS collector.

6. **Downstream Phase Propagation**:
   - `correlateAISVessels(sceneId)` (Phase 6.2)
   - `rankAISCandidates(sceneId)` (Phase 6.3)
   - `generateInvestigationReport(sceneId)` (Phase 7)
   - All downstream calls receive the active scene ID derived from the Phase 1–5 backend output.

---

## 2. Shared State Architecture

The application utilizes `SceneContext` (`context/SceneContext.tsx`) wrapped in `RootLayout` (`app/layout.tsx`):

```typescript
const {
  activeSceneId,
  pipelineResult,
  phase1Data,
  phase2Data,
  phase3Data,
  phase4Data,
  phase5Data,
  correlationResult,
  rankingResult,
  investigationReport,
  stageStatuses,
  isDemo,
  setActiveRealScene,
  setActiveDemo,
  resetSceneState,
} = useScene();
```

All 4 application routes (`/`, `/analysis`, `/vessels`, `/reports`) read from this unified context, guaranteeing complete cross-page scene synchronization.
