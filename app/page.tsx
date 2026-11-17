'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import dynamic from 'next/dynamic';
import TopNav from '@/components/layout/TopNav';
import LeftPipeline from '@/components/layout/LeftPipeline';
import RightVesselPanel from '@/components/layout/RightVesselPanel';
import KPIBar from '@/components/layout/KPIBar';
import BottomAnalysisStrip from '@/components/layout/BottomAnalysisStrip';
import MapControls from '@/components/map/MapControls';
import { mockSpillCase } from '@/data/mockData';
import {
  Vessel,
  MapLayer,
  Phase1Result,
  Phase2Result,
  Phase3Result,
  Phase4Result,
  Phase5Result,
  PipelineResult,
  AISCorrelationResponse,
  AISRankingResponse,
  InvestigationReportResponse,
  PipelineStage,
} from '@/types';
import { useScene } from '@/context/SceneContext';
import { runFullPipeline, correlateAISVessels, rankAISCandidates, generateInvestigationReport } from '@/lib/api';

// Dynamic import for Leaflet (SSR incompatible)
const OceanMap = dynamic(() => import('@/components/map/OceanMap'), {
  ssr: false,
  loading: () => (
    <div
      style={{
        width: '100%', height: '100%',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: '#030d18', color: '#22d3ee',
        fontSize: '0.7rem', letterSpacing: '0.12em',
      }}
    >
      INITIALISING MAP ENGINE...
    </div>
  ),
});

const DEFAULT_LAYERS: Record<MapLayer, boolean> = {
  oilSpill: true,
  vesselTracks: true,
  wind: true,
  oceanCurrent: true,
  driftSimulation: true,
  coastalRisk: false,
  ports: false,
  fishingZones: false,
};

const DEMO_STEPS = [
  'LOADING SAR DATA...',
  'RUNNING AI SEGMENTATION...',
  'EXTRACTING SPILL BOUNDARY...',
  'ANALYSING WIND + CURRENTS...',
  'COMPUTING BACKWARD DRIFT...',
  'FILTERING AIS DATA...',
  'MATCHING TRAJECTORIES...',
  'RANKING VESSELS...',
];

export default function DashboardPage() {
  const sceneCtx = useScene();
  const topVessel = mockSpillCase.vessels.reduce((max, v) => (v.overallScore > max.overallScore ? v : max), mockSpillCase.vessels[0]);
  const [selectedVessel, setSelectedVessel] = useState<Vessel | null>(null);
  const [activeLayers, setActiveLayers] = useState<Record<MapLayer, boolean>>(DEFAULT_LAYERS);
  const [isRunning, setIsRunning] = useState(false);
  const [currentStage, setCurrentStage] = useState(0);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const activeSceneIdRef = useRef<string | null>(null);

  // Sync state from context
  const phase1Data = sceneCtx.phase1Data;
  const phase2Data = sceneCtx.phase2Data;
  const phase3Data = sceneCtx.phase3Data;
  const phase4Data = sceneCtx.phase4Data;
  const phase5Data = sceneCtx.phase5Data;
  const correlationResult = sceneCtx.correlationResult;
  const rankingResult = sceneCtx.rankingResult;
  const investigationReport = sceneCtx.investigationReport;
  const stageStatuses = sceneCtx.stageStatuses;
  const isDemoActive = sceneCtx.isDemo;

  const toggleLayer = useCallback((layer: MapLayer) => {
    setActiveLayers(prev => ({ ...prev, [layer]: !prev[layer] }));
  }, []);

  const handleSelectVessel = useCallback((v: Vessel) => {
    setSelectedVessel(v);
  }, []);

  // REAL PHASE 1–7 ANALYSIS FLOW WITH STALE RESPONSE PROTECTION & SCENE RESET
  const runAnalysis = useCallback(async () => {
    if (intervalRef.current) clearInterval(intervalRef.current);

    // 1. Full Scene State Cleanup via SceneContext
    setIsRunning(true);
    setAnalysisComplete(false);
    setErrorMessage(null);
    setCurrentStage(1);
    setSelectedVessel(null);
    sceneCtx.resetSceneState();
    sceneCtx.setIsAnalyzing(true);

    const runGen = sceneCtx.incrementRunGeneration();
    const requestId = `REQ_${Date.now()}_GEN_${runGen}`;
    activeSceneIdRef.current = requestId;

    const initialStatuses: Record<number, PipelineStage['status']> = {
      1: 'active',
      2: 'pending',
      3: 'pending',
      4: 'pending',
      5: 'pending',
      6: 'pending',
      7: 'pending',
      8: 'pending',
    };

    try {
      setStatusMessage('EXECUTING PHASE 1–5 PIPELINE...');
      const fullResult = await runFullPipeline({
        bbox: [71.5, 18.0, 72.5, 19.0],
        polarization: 'VV',
        width: 512,
        height: 512,
      });

      if (activeSceneIdRef.current !== requestId) {
        console.warn('Stale async response discarded');
        return;
      }

      const sceneId = fullResult.scene?.id || fullResult.phase1?.output_filename?.replace('_processed.tif', '') || 'S1D_IW_GRDH_1SDV_20260918T010238_20260918T010309_004625_008A01_036E_COG';
      const p5OriginAvailable = fullResult.phase5?.origin_available ?? fullResult.drift?.origin_available ?? false;

      const p15Statuses: Record<number, PipelineStage['status']> = {
        1: 'completed',
        2: 'completed',
        3: 'completed',
        4: 'completed',
        5: p5OriginAvailable ? 'completed' : 'not_available',
        6: 'active',
        7: 'pending',
        8: 'pending',
      };

      setStatusMessage('EXECUTING PHASE 6.2 AIS CORRELATION...');
      const corrRes = await correlateAISVessels(sceneId).catch(() => null);
      if (activeSceneIdRef.current !== requestId) return;

      const corrAvailable = corrRes?.correlation_available ?? false;
      const p6Statuses: Record<number, PipelineStage['status']> = {
        ...p15Statuses,
        6: corrAvailable ? 'completed' : 'not_available',
        7: 'active',
      };

      setStatusMessage('EXECUTING PHASE 6.3 CANDIDATE RANKING...');
      const rankRes = await rankAISCandidates(sceneId).catch(() => null);
      if (activeSceneIdRef.current !== requestId) return;

      const rankAvailable = rankRes?.ranking_available ?? false;
      const p7Statuses: Record<number, PipelineStage['status']> = {
        ...p6Statuses,
        7: rankAvailable ? 'completed' : 'not_available',
        8: 'active',
      };

      setStatusMessage('GENERATING PHASE 7 INVESTIGATION REPORT...');
      const reportRes = await generateInvestigationReport(sceneId).catch(() => null);
      if (activeSceneIdRef.current !== requestId) return;

      const finalStatuses: Record<number, PipelineStage['status']> = {
        ...p7Statuses,
        8: 'completed',
      };

      // Atomically set context active scene
      sceneCtx.setActiveRealScene({
        sceneId,
        pipelineResult: fullResult,
        phase1Data: fullResult.phase1,
        phase2Data: fullResult.phase2,
        phase3Data: fullResult.phase3 || null,
        phase4Data: fullResult.phase4 || fullResult.environment || null,
        phase5Data: fullResult.phase5 || fullResult.drift || null,
        correlationResult: corrRes,
        rankingResult: rankRes,
        investigationReport: reportRes,
        stageStatuses: finalStatuses,
      });

      setAnalysisComplete(true);
      setIsRunning(false);
      sceneCtx.setIsAnalyzing(false);
      setCurrentStage(8);
      setStatusMessage('PHASE 1–7 PIPELINE COMPLETE');
    } catch (err: any) {
      console.error('Real Analysis Pipeline Error:', err);
      setIsRunning(false);
      sceneCtx.setIsAnalyzing(false);
      setErrorMessage(`ANALYSIS FAILED: ${err.message || 'Backend connection error'}`);
    }
  }, [sceneCtx]);

  // DEMO MODE FLOW
  const runDemo = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);

    setIsRunning(true);
    setAnalysisComplete(false);
    setErrorMessage(null);
    setCurrentStage(1);
    setSelectedVessel(null);
    sceneCtx.setActiveDemo();

    let stage = 1;
    intervalRef.current = setInterval(() => {
      stage += 1;
      setCurrentStage(stage);
      if (stage > 8) {
        if (intervalRef.current) clearInterval(intervalRef.current);
        setIsRunning(false);
        setAnalysisComplete(true);
        setCurrentStage(9);
        setSelectedVessel(topVessel);
      }
    }, 1200);
  }, [topVessel, sceneCtx]);

  const handleStagesComplete = useCallback(() => {
    // handled above
  }, []);

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateRows: '48px auto 1fr auto',
        gridTemplateColumns: '220px 1fr 240px',
        height: '100vh',
        overflow: 'hidden',
        background: 'var(--maritime-900)',
      }}
    >
      {/* TOP NAV — spans all columns */}
      <div style={{ gridColumn: '1 / -1', gridRow: '1' }}>
        <TopNav />
      </div>

      {/* KPI BAR — center column, row 2 */}
      <div style={{ gridColumn: '2 / 3', gridRow: '2' }}>
        <KPIBar
          spillCase={mockSpillCase}
          analysisComplete={analysisComplete}
          phase1Data={phase1Data}
          phase2Data={phase2Data}
          phase3Data={phase3Data}
          phase4Data={phase4Data}
          phase5Data={phase5Data}
          correlationResult={correlationResult}
          rankingResult={rankingResult}
          investigationReport={investigationReport}
          isDemo={isDemoActive}
        />
      </div>

      {/* LEFT PIPELINE — rows 2-3 */}
      <div style={{ gridColumn: '1 / 2', gridRow: '2 / 4' }}>
        <LeftPipeline
          onRunAnalysis={runAnalysis}
          onRunDemo={runDemo}
          isRunning={isRunning}
          currentStage={currentStage}
          onStagesComplete={handleStagesComplete}
          isDemo={isDemoActive}
          statusText={statusMessage}
          stageStatuses={!isDemoActive && Object.keys(stageStatuses).length > 0 ? stageStatuses : undefined}
        />
      </div>

      {/* MAIN MAP — center, row 3 */}
      <div style={{ gridColumn: '2 / 3', gridRow: '3', position: 'relative', overflow: 'hidden' }}>
        <OceanMap
          spillCase={mockSpillCase}
          selectedVessel={selectedVessel}
          onSelectVessel={handleSelectVessel}
          activeLayers={activeLayers}
          analysisComplete={analysisComplete}
          phase1Data={phase1Data}
          phase3Data={phase3Data}
          phase4Data={phase4Data}
          phase5Data={phase5Data}
          isDemo={isDemoActive}
        />
        {/* Map controls overlay */}
        <MapControls activeLayers={activeLayers} onToggle={toggleLayer} />

        {/* Demo message banner */}
        {isDemoActive && (
          <div
            style={{
              position: 'absolute',
              top: '10px',
              left: '50%',
              transform: 'translateX(-50%)',
              background: 'rgba(245, 158, 11, 0.12)',
              border: '1px solid rgba(245, 158, 11, 0.35)',
              borderRadius: '4px',
              padding: '5px 12px',
              fontSize: '0.62rem',
              fontWeight: 600,
              color: '#f59e0b',
              letterSpacing: '0.1em',
              zIndex: 25,
              backdropFilter: 'blur(8px)',
              whiteSpace: 'nowrap',
            }}
          >
            DEMO MODE ACTIVE — Simulating investigation workflow...
          </div>
        )}

        {/* Error message banner */}
        {errorMessage && (
          <div
            style={{
              position: 'absolute',
              top: '10px',
              left: '50%',
              transform: 'translateX(-50%)',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              borderRadius: '4px',
              padding: '6px 14px',
              fontSize: '0.65rem',
              fontWeight: 600,
              color: '#f87171',
              letterSpacing: '0.08em',
              zIndex: 25,
              backdropFilter: 'blur(8px)',
              whiteSpace: 'nowrap',
            }}
          >
            {errorMessage}
          </div>
        )}

        {/* Processing Banner */}
        {isRunning && (
          <div
            style={{
              position: 'absolute',
              bottom: '40px',
              left: '50%',
              transform: 'translateX(-50%)',
              background: 'rgba(6, 17, 31, 0.9)',
              border: '1px solid rgba(34, 211, 238, 0.3)',
              borderRadius: '4px',
              padding: '6px 14px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              zIndex: 25,
              backdropFilter: 'blur(8px)',
            }}
          >
            <div
              style={{
                width: '8px', height: '8px',
                border: '1.5px solid rgba(34,211,238,0.3)',
                borderTopColor: '#22d3ee',
                borderRadius: '50%',
                animation: 'spin-slow 0.8s linear infinite',
              }}
            />
            <span style={{ fontSize: '0.65rem', color: '#22d3ee', letterSpacing: '0.1em', fontWeight: 600 }}>
              {isDemoActive ? (DEMO_STEPS[currentStage - 1] || 'PROCESSING...') : statusMessage}
            </span>
          </div>
        )}
      </div>

      {/* RIGHT VESSEL PANEL — rows 2-3 */}
      <div style={{ gridColumn: '3 / 4', gridRow: '2 / 4' }}>
        <RightVesselPanel
          vessels={mockSpillCase.vessels}
          selectedVessel={selectedVessel}
          onSelectVessel={handleSelectVessel}
          analysisComplete={analysisComplete}
          correlationResult={correlationResult}
          rankingResult={rankingResult}
          isDemo={isDemoActive}
        />
      </div>

      {/* BOTTOM ANALYSIS STRIP — all columns, row 4 */}
      <div style={{ gridColumn: '1 / -1', gridRow: '4' }}>
        <BottomAnalysisStrip
          spillCase={mockSpillCase}
          analysisComplete={analysisComplete}
          phase1Data={phase1Data}
          phase2Data={phase2Data}
          phase3Data={phase3Data}
          phase4Data={phase4Data}
          phase5Data={phase5Data}
          isDemo={isDemoActive}
        />
      </div>
    </div>
  );
}

