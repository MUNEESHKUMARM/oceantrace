'use client';

import React, { createContext, useContext, useState, ReactNode, useCallback } from 'react';
import {
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

export interface SetActiveScenePayload {
  sceneId: string;
  pipelineResult?: PipelineResult | null;
  phase1Data?: Phase1Result | null;
  phase2Data?: Phase2Result | null;
  phase3Data?: Phase3Result | null;
  phase4Data?: Phase4Result | null;
  phase5Data?: Phase5Result | null;
  correlationResult?: AISCorrelationResponse | null;
  rankingResult?: AISRankingResponse | null;
  investigationReport?: InvestigationReportResponse | null;
  stageStatuses?: Record<number, PipelineStage['status']>;
}

export interface SceneContextType {
  activeSceneId: string | null;
  pipelineResult: PipelineResult | null;
  phase1Data: Phase1Result | null;
  phase2Data: Phase2Result | null;
  phase3Data: Phase3Result | null;
  phase4Data: Phase4Result | null;
  phase5Data: Phase5Result | null;
  correlationResult: AISCorrelationResponse | null;
  rankingResult: AISRankingResponse | null;
  investigationReport: InvestigationReportResponse | null;
  stageStatuses: Record<number, PipelineStage['status']>;
  isDemo: boolean;
  isAnalyzing: boolean;
  activeRunGenerationId: number;
  setActiveRealScene: (payload: SetActiveScenePayload) => void;
  setActiveDemo: () => void;
  resetSceneState: () => void;
  setIsAnalyzing: (analyzing: boolean) => void;
  incrementRunGeneration: () => number;
}

const defaultStageStatuses: Record<number, PipelineStage['status']> = {
  1: 'pending',
  2: 'pending',
  3: 'pending',
  4: 'pending',
  5: 'pending',
  6: 'pending',
  7: 'pending',
};

const SceneContext = createContext<SceneContextType | undefined>(undefined);

export function SceneProvider({ children }: { children: ReactNode }) {
  const [activeSceneId, setActiveSceneId] = useState<string | null>(null);
  const [pipelineResult, setPipelineResult] = useState<PipelineResult | null>(null);
  const [phase1Data, setPhase1Data] = useState<Phase1Result | null>(null);
  const [phase2Data, setPhase2Data] = useState<Phase2Result | null>(null);
  const [phase3Data, setPhase3Data] = useState<Phase3Result | null>(null);
  const [phase4Data, setPhase4Data] = useState<Phase4Result | null>(null);
  const [phase5Data, setPhase5Data] = useState<Phase5Result | null>(null);
  const [correlationResult, setCorrelationResult] = useState<AISCorrelationResponse | null>(null);
  const [rankingResult, setRankingResult] = useState<AISRankingResponse | null>(null);
  const [investigationReport, setInvestigationReport] = useState<InvestigationReportResponse | null>(null);
  const [stageStatuses, setStageStatuses] = useState<Record<number, PipelineStage['status']>>(defaultStageStatuses);
  const [isDemo, setIsDemo] = useState<boolean>(false);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [activeRunGenerationId, setActiveRunGenerationId] = useState<number>(0);

  const resetSceneState = useCallback(() => {
    setActiveSceneId(null);
    setPipelineResult(null);
    setPhase1Data(null);
    setPhase2Data(null);
    setPhase3Data(null);
    setPhase4Data(null);
    setPhase5Data(null);
    setCorrelationResult(null);
    setRankingResult(null);
    setInvestigationReport(null);
    setStageStatuses(defaultStageStatuses);
  }, []);

  const setActiveRealScene = useCallback((payload: SetActiveScenePayload) => {
    setIsDemo(false);
    setActiveSceneId(payload.sceneId);
    if (payload.pipelineResult !== undefined) setPipelineResult(payload.pipelineResult);
    if (payload.phase1Data !== undefined) setPhase1Data(payload.phase1Data);
    if (payload.phase2Data !== undefined) setPhase2Data(payload.phase2Data);
    if (payload.phase3Data !== undefined) setPhase3Data(payload.phase3Data);
    if (payload.phase4Data !== undefined) setPhase4Data(payload.phase4Data);
    if (payload.phase5Data !== undefined) setPhase5Data(payload.phase5Data);
    if (payload.correlationResult !== undefined) setCorrelationResult(payload.correlationResult);
    if (payload.rankingResult !== undefined) setRankingResult(payload.rankingResult);
    if (payload.investigationReport !== undefined) setInvestigationReport(payload.investigationReport);
    if (payload.stageStatuses !== undefined) setStageStatuses(payload.stageStatuses);
  }, []);

  const setActiveDemo = useCallback(() => {
    resetSceneState();
    setIsDemo(true);
    setActiveSceneId('DEMO-SAR-2026');
  }, [resetSceneState]);

  const incrementRunGeneration = useCallback(() => {
    let nextGen = 0;
    setActiveRunGenerationId((prev) => {
      nextGen = prev + 1;
      return nextGen;
    });
    return nextGen;
  }, []);

  return (
    <SceneContext.Provider
      value={{
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
        isAnalyzing,
        activeRunGenerationId,
        setActiveRealScene,
        setActiveDemo,
        resetSceneState,
        setIsAnalyzing,
        incrementRunGeneration,
      }}
    >
      {children}
    </SceneContext.Provider>
  );
}

export function useScene(): SceneContextType {
  const context = useContext(SceneContext);
  if (!context) {
    throw new Error('useScene must be used within a SceneProvider');
  }
  return context;
}
