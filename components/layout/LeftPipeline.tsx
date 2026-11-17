'use client';

import { useState, useEffect } from 'react';
import { PipelineStage } from '@/types';

const initialStages: PipelineStage[] = [
  { id: 1, label: '01  SAR IMAGE INGESTION', description: 'Real GRD acquisition & preprocessing (Phase 1)', status: 'pending' },
  { id: 2, label: '02  VV U-NET SEGMENTATION', description: 'Deep-learning segmentation (Phase 2)', status: 'pending' },
  { id: 3, label: '03  SPILL BOUNDARY MAPPING', description: 'Vector polygonization & area (Phase 3)', status: 'pending' },
  { id: 4, label: '04  METOCEAN WIND & CURRENT', description: 'ECMWF & CMEMS integration (Phase 4)', status: 'pending' },
  { id: 5, label: '05  BACKWARD DRIFT & ORIGIN', description: 'Lagrangian backward/forward drift (Phase 5)', status: 'pending' },
  { id: 6, label: '06  AIS SPATIAL CORRELATION', description: 'Spatial/temporal AIS correlation (Phase 6.2)', status: 'pending' },
  { id: 7, label: '07  EXPLAINABLE RANKING', description: 'Evidence-weighted candidate scoring (Phase 6.3)', status: 'pending' },
  { id: 8, label: '08  INVESTIGATION REPORT', description: 'Automated report & attention classification (Phase 7)', status: 'pending' },
];

interface Props {
  onRunAnalysis: () => void;
  onRunDemo: () => void;
  isRunning: boolean;
  currentStage: number;
  onStagesComplete: () => void;
  isDemo?: boolean;
  statusText?: string;
  stageStatuses?: Record<number, PipelineStage['status']>;
}

export default function LeftPipeline({
  onRunAnalysis,
  onRunDemo,
  isRunning,
  currentStage,
  onStagesComplete,
  isDemo = false,
  statusText,
  stageStatuses,
}: Props) {
  const [stages, setStages] = useState<PipelineStage[]>(initialStages);

  useEffect(() => {
    if (stageStatuses) {
      setStages(
        initialStages.map(s => ({
          ...s,
          status: stageStatuses[s.id] || s.status,
        }))
      );
      return;
    }

    if (!isRunning) {
      if (currentStage === 0) {
        setStages(initialStages.map(s => ({ ...s, status: 'pending' })));
      } else if (!isDemo && currentStage >= 1) {
        setStages(prev =>
          prev.map((s, i) => {
            if (i < currentStage) return { ...s, status: 'completed' };
            return { ...s, status: 'pending' };
          })
        );
      }
      return;
    }

    if (isDemo) {
      setStages(prev =>
        prev.map((s, i) => {
          if (i + 1 < currentStage) return { ...s, status: 'completed' };
          if (i + 1 === currentStage) return { ...s, status: 'active' };
          return { ...s, status: 'pending' };
        })
      );
      if (currentStage > 8) onStagesComplete();
    } else {
      setStages(prev =>
        prev.map((s, i) => {
          if (i + 1 === currentStage) return { ...s, status: 'active' };
          if (i + 1 < currentStage) return { ...s, status: 'completed' };
          return { ...s, status: 'pending' };
        })
      );
    }
  }, [currentStage, isRunning, isDemo, stageStatuses]);

  const statusColor = (status: PipelineStage['status']) => {
    switch (status) {
      case 'completed': return '#22d3ee';
      case 'active': return '#22d3ee';
      case 'warning': return '#f59e0b';
      case 'critical': return '#ef4444';
      case 'not_available': return '#64748b';
      default: return '#475569';
    }
  };

  return (
    <div
      style={{
        background: 'var(--maritime-850)',
        borderRight: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        maxHeight: '100%',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '10px 12px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#22d3ee" strokeWidth="2">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
          </svg>
          <span className="label-sm" style={{ color: '#94a3b8' }}>Investigation Pipeline</span>
        </div>
        <span
          style={{
            fontSize: '0.52rem',
            fontWeight: 700,
            padding: '1px 5px',
            borderRadius: '2px',
            background: isDemo ? 'rgba(245, 158, 11, 0.15)' : 'rgba(34, 211, 238, 0.15)',
            border: `1px solid ${isDemo ? 'rgba(245, 158, 11, 0.3)' : 'rgba(34, 211, 238, 0.3)'}`,
            color: isDemo ? '#f59e0b' : '#22d3ee',
            letterSpacing: '0.08em',
          }}
        >
          {isDemo ? 'DEMO' : 'REAL DATA'}
        </span>
      </div>

      {/* Processing Indicator */}
      {isRunning && (
        <div
          style={{
            padding: '6px 12px',
            background: 'rgba(34, 211, 238, 0.05)',
            borderBottom: '1px solid rgba(34, 211, 238, 0.1)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            flexShrink: 0,
          }}
        >
          <div
            style={{
              width: '8px', height: '8px', borderRadius: '50%',
              background: '#22d3ee',
              animation: 'pulse-warning 0.8s ease infinite',
            }}
          />
          <span style={{ fontSize: '0.6rem', color: '#22d3ee', letterSpacing: '0.08em', fontWeight: 600 }}>
            {statusText || (isDemo ? 'DEMO PROCESSING...' : 'FETCHING SENTINEL-1 SAR...')}
          </span>
        </div>
      )}

      {/* Stages */}
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '8px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
        {stages.map((stage, idx) => (
          <div key={stage.id} style={{ position: 'relative' }}>
            <div
              className={`pipeline-stage ${stage.status}`}
              style={{
                opacity: stage.status === 'pending' && isRunning ? 0.5 : 1,
                transition: 'all 0.3s ease',
              }}
            >
              {/* Number */}
              <div className="stage-num">
                {stage.status === 'completed' ? (
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  <span>{String(stage.id).padStart(2, '0')}</span>
                )}
              </div>

              {/* Content */}
              <div style={{ minWidth: 0 }}>
                <div
                  style={{
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    letterSpacing: '0.05em',
                    color: stage.status === 'completed'
                      ? '#22d3ee'
                      : stage.status === 'active'
                      ? '#e2e8f0'
                      : '#64748b',
                    lineHeight: 1.2,
                    marginBottom: '2px',
                  }}
                >
                  {stage.label}
                </div>
                <div style={{ fontSize: '0.575rem', color: '#475569', lineHeight: 1.3 }}>
                  {stage.description}
                </div>

                {/* Active Progress Bar */}
                {stage.status === 'active' && (
                  <div
                    style={{
                      marginTop: '4px',
                      height: '2px',
                      background: 'rgba(34, 211, 238, 0.15)',
                      borderRadius: '1px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        height: '100%',
                        background: 'var(--cyan-400)',
                        borderRadius: '1px',
                        animation: 'shimmer 1.5s linear infinite',
                        backgroundImage: 'linear-gradient(90deg, transparent 0%, #22d3ee 50%, transparent 100%)',
                        backgroundSize: '200% 100%',
                      }}
                    />
                  </div>
                )}
              </div>

              {/* Status Dot */}
              {stage.status !== 'pending' && (
                <div
                  style={{
                    marginLeft: 'auto',
                    width: '5px', height: '5px',
                    borderRadius: '50%',
                    background: statusColor(stage.status),
                    flexShrink: 0,
                    boxShadow: stage.status === 'active' ? '0 0 8px rgba(34,211,238,0.5)' : 'none',
                  }}
                />
              )}
            </div>

            {/* Connector Line */}
            {idx < stages.length - 1 && (
              <div
                style={{
                  width: '1.5px',
                  height: '4px',
                  background:
                    stages[idx + 1].status !== 'pending'
                      ? 'rgba(34, 211, 238, 0.3)'
                      : 'rgba(100, 116, 139, 0.2)',
                  marginLeft: '20px',
                }}
              />
            )}
          </div>
        ))}
      </div>

      {/* Run Analysis Button */}
      <div
        style={{
          padding: '10px',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
          flexShrink: 0,
        }}
      >
        <button
          className="btn-primary"
          onClick={onRunAnalysis}
          disabled={isRunning}
          style={{
            width: '100%',
            justifyContent: 'center',
            fontSize: '0.7rem',
            padding: '9px',
            background: isRunning && !isDemo ? 'rgba(8, 145, 178, 0.3)' : undefined,
          }}
        >
          {isRunning && !isDemo ? (
            <>
              <div
                style={{
                  width: '10px', height: '10px',
                  border: '1.5px solid rgba(255,255,255,0.3)',
                  borderTopColor: '#fff',
                  borderRadius: '50%',
                  animation: 'spin-slow 0.8s linear infinite',
                }}
              />
              CONNECTING TO BACKEND...
            </>
          ) : (
            <>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
              RUN REAL ANALYSIS
            </>
          )}
        </button>

        <button
          className="btn-secondary"
          style={{ width: '100%', justifyContent: 'center', fontSize: '0.65rem' }}
          onClick={() => onRunDemo()}
          disabled={isRunning}
        >
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" /><polygon points="10 8 16 12 10 16 10 8" />
          </svg>
          RUN DEMO MODE
        </button>
      </div>
    </div>
  );
}

