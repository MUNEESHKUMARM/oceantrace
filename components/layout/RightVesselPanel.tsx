'use client';

import { Vessel, AISCorrelationResponse, AISRankingResponse } from '@/types';

interface Props {
  vessels: Vessel[];
  selectedVessel: Vessel | null;
  onSelectVessel: (v: Vessel) => void;
  analysisComplete: boolean;
  isDemo?: boolean;
  correlationResult?: AISCorrelationResponse | null;
  rankingResult?: AISRankingResponse | null;
}

function ScoreBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="score-bar-track" style={{ flex: 1 }}>
      <div
        className="score-bar-fill"
        style={{
          width: `${value * 100}%`,
          background: color,
        }}
      />
    </div>
  );
}

function ScoreCircle({ value, size = 32 }: { value: number; size?: number }) {
  const r = (size - 4) / 2;
  const circ = 2 * Math.PI * r;
  const dash = circ * value;
  const color = value >= 0.7 ? '#ef4444' : value >= 0.5 ? '#f59e0b' : value >= 0.3 ? '#3b82f6' : '#475569';

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)', flexShrink: 0 }}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="2.5" />
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none"
        stroke={color}
        strokeWidth="2.5"
        strokeDasharray={`${dash} ${circ}`}
        strokeLinecap="round"
        style={{ transition: 'stroke-dasharray 0.5s ease' }}
      />
      <text
        x={size / 2} y={size / 2 + 4}
        textAnchor="middle"
        fill={color}
        fontSize="8"
        fontWeight="700"
        style={{ transform: `rotate(90deg) translate(0, -${size / 2 - size / 2}px)`, transformOrigin: `${size / 2}px ${size / 2}px` }}
      >
        {Math.round(value * 100)}
      </text>
    </svg>
  );
}

export default function RightVesselPanel({ vessels, selectedVessel, onSelectVessel, analysisComplete, isDemo = false }: Props) {
  const sorted = [...vessels].sort((a, b) => b.overallScore - a.overallScore);

  const scoreColor = (score: number) => {
    if (score >= 70) return '#ef4444';
    if (score >= 50) return '#f59e0b';
    if (score >= 30) return '#3b82f6';
    return '#475569';
  };

  const factorColor = (v: number) => {
    if (v >= 0.7) return '#ef4444';
    if (v >= 0.5) return '#f59e0b';
    if (v >= 0.3) return '#22d3ee';
    return '#475569';
  };

  return (
    <div
      style={{
        background: 'var(--maritime-850)',
        borderLeft: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflowY: 'auto',
        overflowX: 'hidden',
      }}
    >
      {/* Header */}
      <div className="panel-header" style={{ flexShrink: 0 }}>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#22d3ee" strokeWidth="2">
          <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07" />
          <path d="M21 21L3 3m7.72 7.72A10.94 10.94 0 0 1 3.07 8.63 2 2 0 0 1 5.06 6.44" />
        </svg>
        <span className="label-sm" style={{ color: '#94a3b8', flex: 1 }}>Vessel Intelligence</span>
        <span className={`risk-badge ${isDemo ? 'critical' : 'low'}`}>
          {isDemo ? 'HIGH RISK' : 'PHASE 1'}
        </span>
      </div>

      {/* Top Candidates Header */}
      <div
        style={{
          padding: '8px 10px 4px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexShrink: 0,
        }}
      >
        <span style={{ fontSize: '0.625rem', fontWeight: 600, color: '#64748b', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
          {isDemo ? 'Top Potential Vessels' : 'AIS Correlation'}
        </span>
        {isDemo && analysisComplete && (
          <span style={{ fontSize: '0.575rem', color: '#22d3ee' }}>{vessels.length} vessels</span>
        )}
      </div>

      {!isDemo ? (
        /* REAL MODE: Display real Phase 6.2 & 6.3 backend correlation & ranking state */
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px 16px',
            textAlign: 'center',
            gap: '12px',
          }}
        >
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              background: 'rgba(34, 211, 238, 0.05)',
              border: '1px solid rgba(34, 211, 238, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#22d3ee" strokeWidth="1.8">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <div>
            <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#94a3b8', letterSpacing: '0.04em', marginBottom: '4px' }}>
              {analysisComplete ? 'NO AIS CANDIDATES IDENTIFIED' : 'AWAITING PHASE 6 CORRELATION'}
            </div>
            <p style={{ fontSize: '0.6rem', color: '#64748b', lineHeight: 1.5 }}>
              {analysisComplete
                ? 'No AIS candidate vessels matched this scene because no Phase 5 origin zone was generated (0 predicted oil pixels).'
                : 'Run Phase 1–7 Pipeline to perform real Sentinel-1 SAR ingestion, U-Net detection, drift estimation, and AIS correlation.'}
            </p>
          </div>
          <div
            style={{
              padding: '6px 10px',
              background: 'rgba(30, 41, 59, 0.6)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '4px',
              fontSize: '0.55rem',
              color: '#475569',
            }}
          >
            Phase 6.1 live AISStream background collector is active. Phase 6.2 correlation & 6.3 ranking ready.
          </div>
        </div>
      ) : (
        /* DEMO MODE: Display mock vessel ranking & details */
        <>
          {/* Rank Table */}
          <div style={{ padding: '0 8px', display: 'flex', flexDirection: 'column', gap: '2px', flexShrink: 0 }}>
            {/* Column Headers */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '22px 1fr 48px',
                gap: '6px',
                padding: '2px 10px',
                marginBottom: '2px',
              }}
            >
              <span style={{ fontSize: '0.5rem', color: '#475569', fontWeight: 600, textTransform: 'uppercase' }}>RK</span>
              <span style={{ fontSize: '0.5rem', color: '#475569', fontWeight: 600, textTransform: 'uppercase' }}>Vessel</span>
              <span style={{ fontSize: '0.5rem', color: '#475569', fontWeight: 600, textTransform: 'uppercase', textAlign: 'right' }}>Score</span>
            </div>

            {sorted.map((vessel, idx) => {
              const isSelected = selectedVessel?.id === vessel.id;
              const isTop = idx === 0;
              return (
                <div
                  key={vessel.id}
                  className={`rank-row ${isSelected ? 'selected' : ''}`}
                  onClick={() => onSelectVessel(vessel)}
                >
                  {/* Rank */}
                  <div
                    style={{
                      width: '18px', height: '18px',
                      borderRadius: '3px',
                      background: isTop ? 'rgba(239, 68, 68, 0.15)' : 'rgba(71, 85, 105, 0.2)',
                      border: `1px solid ${isTop ? 'rgba(239, 68, 68, 0.3)' : 'rgba(71, 85, 105, 0.3)'}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: '0.575rem',
                      fontWeight: 700,
                      color: isTop ? '#f87171' : '#64748b',
                      flexShrink: 0,
                    }}
                  >
                    {String(idx + 1).padStart(2, '0')}
                  </div>

                  {/* Vessel Info */}
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: '0.65rem', fontWeight: 600, color: isTop ? '#fca5a5' : '#94a3b8', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {vessel.id}
                    </div>
                    <div style={{ fontSize: '0.55rem', color: '#475569', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {vessel.type} · {vessel.flag}
                    </div>
                    {analysisComplete && (
                      <div style={{ marginTop: '3px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <ScoreBar value={vessel.similarityScore} color={factorColor(vessel.similarityScore)} />
                      </div>
                    )}
                  </div>

                  {/* Score */}
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <div
                      style={{
                        fontSize: '0.8rem',
                        fontWeight: 700,
                        color: scoreColor(vessel.overallScore),
                        fontVariantNumeric: 'tabular-nums',
                        lineHeight: 1,
                      }}
                    >
                      {analysisComplete ? vessel.overallScore : '--'}
                    </div>
                    <div style={{ fontSize: '0.5rem', color: '#475569' }}>/ 100</div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Divider */}
          <div style={{ height: '1px', background: 'var(--border-subtle)', margin: '8px 0', flexShrink: 0 }} />

          {/* Selected Vessel Detail Card */}
          {selectedVessel ? (
            <div style={{ padding: '0 8px', flex: 1, animation: 'fade-in 0.3s ease' }}>
              {/* Card Header */}
              <div
                style={{
                  background: 'rgba(239, 68, 68, 0.06)',
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  borderRadius: '5px',
                  padding: '8px 10px',
                  marginBottom: '6px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                  <div>
                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#fca5a5', letterSpacing: '0.02em' }}>
                      {selectedVessel.id}
                    </div>
                    <div style={{ fontSize: '0.6rem', color: '#64748b' }}>{selectedVessel.name}</div>
                  </div>
                  <div
                    style={{
                      padding: '2px 6px',
                      background: 'rgba(239, 68, 68, 0.15)',
                      border: '1px solid rgba(239, 68, 68, 0.3)',
                      borderRadius: '3px',
                      fontSize: '0.55rem',
                      fontWeight: 700,
                      color: '#f87171',
                      letterSpacing: '0.08em',
                      textTransform: 'uppercase',
                    }}
                  >
                    POTENTIAL SOURCE
                  </div>
                </div>

                {/* Score Display */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
                  <ScoreCircle value={selectedVessel.similarityScore} size={38} />
                  <div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ef4444', fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
                      {selectedVessel.overallScore}
                      <span style={{ fontSize: '0.65rem', color: '#64748b', fontWeight: 400 }}>/100</span>
                    </div>
                    <div style={{ fontSize: '0.55rem', color: '#64748b', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                      Overall Score
                    </div>
                  </div>
                  <div style={{ marginLeft: 'auto' }}>
                    <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#22d3ee', fontVariantNumeric: 'tabular-nums' }}>
                      {Math.round(selectedVessel.confidence * 100)}%
                    </div>
                    <div style={{ fontSize: '0.5rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                      Confidence
                    </div>
                  </div>
                </div>
              </div>

              {/* Details Grid */}
              {[
                ['MMSI', selectedVessel.mmsi],
                ['Type', selectedVessel.type],
                ['Flag', selectedVessel.flag],
                ['Length', `${selectedVessel.length} m`],
                ['Beam', `${selectedVessel.beam} m`],
                ['Dist. to Origin', `${selectedVessel.distanceToOriginKm} km`],
              ].map(([label, value]) => (
                <div
                  key={label}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '4px 0',
                    borderBottom: '1px solid rgba(30, 41, 59, 0.8)',
                  }}
                >
                  <span style={{ fontSize: '0.6rem', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
                  <span style={{ fontSize: '0.62rem', fontWeight: 600, color: '#94a3b8' }}>{value}</span>
                </div>
              ))}

              {/* AIS Gap Warning */}
              {selectedVessel.aisGapHours && selectedVessel.aisGapHours > 2 && (
                <div
                  style={{
                    marginTop: '6px',
                    padding: '5px 8px',
                    background: 'rgba(245, 158, 11, 0.08)',
                    border: '1px solid rgba(245, 158, 11, 0.2)',
                    borderRadius: '4px',
                    display: 'flex',
                    gap: '5px',
                    alignItems: 'flex-start',
                  }}
                >
                  <span style={{ color: '#fbbf24', fontSize: '0.65rem', fontWeight: 700 }}>⚠</span>
                  <div>
                    <div style={{ fontSize: '0.575rem', fontWeight: 600, color: '#fbbf24' }}>AIS Signal Gap</div>
                    <div style={{ fontSize: '0.55rem', color: '#64748b' }}>{selectedVessel.aisGapHours}h gap in AIS transmission detected near origin zone</div>
                  </div>
                </div>
              )}

              {/* Scoring Breakdown */}
              <div style={{ marginTop: '8px', marginBottom: '6px' }}>
                <div style={{ fontSize: '0.55rem', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '5px', fontWeight: 600 }}>
                  {isDemo ? 'Demo Scoring Factors' : 'Phase 6.3 Configured Factors'}
                </div>
                {(isDemo
                  ? [
                      { label: 'Proximity to Origin', value: selectedVessel.proximityScore, weight: '30%' },
                      { label: 'Trajectory Similarity', value: selectedVessel.trajectoryScore, weight: '25%' },
                      { label: 'Timeline Consistency', value: selectedVessel.timelineScore, weight: '20%' },
                      { label: 'Behaviour Anomaly', value: selectedVessel.anomalyScore, weight: '15%' },
                      { label: 'Env. Compatibility', value: selectedVessel.environmentScore, weight: '10%' },
                    ]
                  : [
                      { label: 'Spatial Evidence (Distance)', value: selectedVessel.proximityScore, weight: '40%' },
                      { label: 'Intersection Evidence (Track)', value: selectedVessel.trajectoryScore, weight: '35%' },
                      { label: 'Temporal Evidence (Window)', value: selectedVessel.timelineScore, weight: '15%' },
                      { label: 'Observation Evidence (AIS)', value: selectedVessel.anomalyScore, weight: '10%' },
                    ]
                ).map(factor => (
                  <div key={factor.label} style={{ marginBottom: '4px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                      <span style={{ fontSize: '0.55rem', color: '#64748b' }}>{factor.label}</span>
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.5rem', color: '#334155' }}>{factor.weight}</span>
                        <span style={{ fontSize: '0.6rem', fontWeight: 700, color: factorColor(factor.value), fontVariantNumeric: 'tabular-nums' }}>
                          {Math.round(factor.value * 100)}
                        </span>
                      </div>
                    </div>
                    <div className="score-bar-track">
                      <div
                        className="score-bar-fill"
                        style={{ width: `${factor.value * 100}%`, background: factorColor(factor.value) }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '20px',
                gap: '8px',
              }}
            >
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#334155" strokeWidth="1.5">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" />
              </svg>
              <span style={{ fontSize: '0.625rem', color: '#334155', textAlign: 'center', lineHeight: 1.4 }}>
                Select a vessel from<br />the ranking to view details
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
