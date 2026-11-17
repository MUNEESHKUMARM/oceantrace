# Vessel Ranking Real Data Integration Documentation

## Overview

This document specifies the Vessel Ranking real-data integration for OceanTrace AI (`app/vessels/page.tsx`).

---

## 1. Selected Vessel Lifecycle in Real Data Mode

1. **Initial & Default State**:
   - `selectedVessel` defaults to `null` in Real Data Mode when no candidate vessel is selected or when candidate count is 0.
   - Stale fallback to mock objects (`mockSpillCase.vessels[0]`) is strictly prohibited in Real Data Mode.

2. **Candidate Count = 0 / Ranking Unavailable**:
   - Main table displays: `NO AIS CANDIDATES IDENTIFIED` with `RANKING NOT AVAILABLE` badge.
   - Right-side panel displays: `NO VESSEL SELECTED` with neutral unavailable candidate status (`—`).
   - Radar chart displays: `NO FACTOR ANALYSIS AVAILABLE`.

3. **Active Real Candidates**:
   - Rendered from Phase 6.3 backend response (`rankingResult.ranked_candidates`).
   - `selectedVessel` is automatically validated against current active candidate list on scene/mode change.
   - Score is labeled as `ENGINEERING CORRELATION SCORE / 100`.
   - Missing metadata fields (flag, length, beam) display `NOT AVAILABLE`.

4. **Real vs Demo Mode Isolation**:
   - Demo Mode isolates `mockSpillCase.vessels` and demo factor analysis when `isDemo === true`.
   - Real Data Mode reads strictly from `SceneContext` (`rankingResult` / `correlationResult`).
   - Mode switching triggers an immediate reset of `selectedVessel` to `null`.
