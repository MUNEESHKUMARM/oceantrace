# FRONTEND VESSEL RANKING REAL DATA VERIFICATION REPORT

**Project**: OCEANTRACE AI — SIH 2026  
**Scope**: Vessel Ranking Page Real-Data Purification Patch (Frontend Only)  
**Date**: September 24, 2026  
**Status**: VERIFIED & PASSED  

---

## A. Root Cause of Stale Selected-Vessel Panel
In `app/vessels/page.tsx`, the state initialization `const [selectedVessel, setSelectedVessel] = useState<Vessel>(sorted[0] || mockSpillCase.vessels[0])` evaluated to `mockSpillCase.vessels[0]` (`Vessel-04 / MV Arafura Spirit`) when `sorted` was empty (`[]`) in Real Data Mode. Furthermore, the right-side detail panel rendered `selectedVessel` unconditionally without verifying if candidates existed or if `selectedVessel` was `null`.

---

## B. Files Modified
1. [app/vessels/page.tsx](file:///g:/SIH/oceantrace-ai/app/vessels/page.tsx) — Purified `VesselsPage` to default `selectedVessel` to `null` in Real Data Mode, validate selections against active candidate list, render `NO VESSEL SELECTED` / `NO FACTOR ANALYSIS AVAILABLE` neutral empty panels when candidate count is 0, and label overall score as `ENGINEERING CORRELATION SCORE / 100`.
2. [frontend/docs/VESSEL_RANKING_REAL_DATA.md](file:///g:/SIH/oceantrace-ai/frontend/docs/VESSEL_RANKING_REAL_DATA.md) — Created comprehensive documentation on vessel ranking real data integration.

---

## C. Files Unchanged
- Backend Python code (`backend/app/**/*.py`) — 0 files modified.
- FastAPI endpoint contracts — 0 files modified.
- Phase 1–7 algorithms — 0 lines modified.
- UI theme, dark palette, CSS tokens, layout structure — 100% preserved.

---

## D. Mock Data Isolation
Static mock vessels (`Vessel-04`, `MV Arafura Spirit`, `MMSI 123456789`, `86/100`, `8.4 km`, `Liberia`, `Tanker`, `274 m`, `48 m`) are strictly isolated to `isDemo === true`. They cannot leak into Real Data Mode.

---

## E. Selected Vessel Reset
`selectedVessel` is automatically set to `null` when:
- Candidate count is 0.
- `ranking_available === false`.
- `activeSceneId` changes.
- Mode switches from DEMO to REAL.

---

## F. Current Production Scene Results

For current production scene `S1D_IW_GRDH_1SDV_20260918T010238_20260918T010309_004625_008A01_036E_COG`:
- **Candidate Count**: `0`
- **Ranking Status**: `RANKING NOT AVAILABLE`
- **Main Table**: `NO AIS CANDIDATES IDENTIFIED`
- **Right Panel**: `NO VESSEL SELECTED`
- **Factor Analysis**: `NO FACTOR ANALYSIS AVAILABLE`
- **Score**: `—`

---

## G. Verification Commands & Results

1. **TypeScript Type Check**:
   ```bash
   npx tsc --noEmit
   ```
   **Result**: `0 errors` (PASSED).

2. **Next.js Production Build**:
   ```bash
   npm run build
   ```
   **Result**: `Compiled successfully in 3.0s` (PASSED).

3. **Backend Regression Test Suite**:
   ```bash
   python -m pytest test_phase1.py test_phase2.py test_phase3.py test_phase4.py test_phase5.py test_phase6_1.py test_phase6_2.py test_phase6_3.py test_phase7.py -q
   ```
   **Result**: `106 passed, 30 warnings in 118.00s` (100% pass rate).

---

## H. Remaining Limitations
None. Vessel Ranking page real-data purification is complete.
