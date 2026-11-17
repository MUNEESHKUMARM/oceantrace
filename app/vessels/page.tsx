'use client';

import { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import TopNav from '@/components/layout/TopNav';
import { mockSpillCase } from '@/data/mockData';
import { Vessel, AISCollectorStatus, AISVesselPosition } from '@/types';
import { getAISCollectorStatus, getRecentAISPositions } from '@/lib/api';
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer } from 'recharts';
import { useScene } from '@/context/SceneContext';

const REAL_FACTORS = [
  { key: 'proximityScore', label: 'Spatial Evidence', weight: 0.40 },
  { key: 'trajectoryScore', label: 'Intersection Evidence', weight: 0.35 },
  { key: 'timelineScore', label: 'Temporal Evidence', weight: 0.15 },
  { key: 'anomalyScore', label: 'Observation Evidence', weight: 0.10 },
];

const DEMO_FACTORS = [
  { key: 'proximityScore', label: 'Proximity', weight: 0.30 },
  { key: 'trajectoryScore', label: 'Trajectory', weight: 0.25 },
  { key: 'timelineScore', label: 'Timeline', weight: 0.20 },
  { key: 'anomalyScore', label: 'Anomaly', weight: 0.15 },
  { key: 'environmentScore', label: 'Environment', weight: 0.10 },
];

function VesselRadar({ vessel, factors }: { vessel: Vessel | null; factors: Array<{ key: string; label: string; weight: number }> }) {
  if (!vessel) {
    return (
      <div style={{ height: '180px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569', fontSize: '0.62rem', letterSpacing: '0.08em' }}>
        NO FACTOR ANALYSIS AVAILABLE
      </div>
    );
  }

  const data = factors.map(f => ({
    factor: f.label,
    value: Math.round(((vessel as any)[f.key] ?? 0) * 100),
  }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <RadarChart data={data}>
        <PolarGrid stroke="rgba(34,211,238,0.1)" />
        <PolarAngleAxis dataKey="factor" tick={{ fill: '#64748b', fontSize: 9 }} />
        <Radar dataKey="value" stroke="#ef4444" fill="#ef4444" fillOpacity={0.15} dot={{ fill: '#ef4444', r: 3 }} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

export default function VesselsPage() {
  const sceneCtx = useScene();
  const { isDemo, activeSceneId, rankingResult, correlationResult } = sceneCtx;

  const isRealActive = !isDemo && !!activeSceneId;
  const currentSceneId = isRealActive ? activeSceneId : mockSpillCase.id;
  const currentFactors = isRealActive ? REAL_FACTORS : DEMO_FACTORS;

  // Build candidate vessel array
  const vessels: Vessel[] = useMemo(() => {
    if (isDemo) {
      return [...mockSpillCase.vessels].sort((a, b) => b.overallScore - a.overallScore);
    }
    if (!isRealActive || !rankingResult || !rankingResult.ranking_available || !rankingResult.ranked_candidates) {
      return [];
    }
    return rankingResult.ranked_candidates.map((rc, idx) => ({
      id: `Candidate-${String(idx + 1).padStart(2, '0')}`,
      mmsi: rc.mmsi,
      name: `MMSI ${rc.mmsi}`,
      type: 'Tanker' as const,
      flag: 'NOT AVAILABLE',
      length: 0,
      beam: 0,
      track: [],
      lastKnownPosition: { lat: 0, lng: 0 },
      distanceToOriginKm: rc.raw_evidence?.minimum_distance_to_origin_km ?? 0,
      similarityScore: rc.evidence?.intersection_score ?? 0,
      behaviourScore: rc.evidence?.observation_score ?? 0,
      confidence: rc.candidate_score,
      proximityScore: rc.evidence?.spatial_score ?? 0,
      timelineScore: rc.evidence?.temporal_score ?? 0,
      trajectoryScore: rc.evidence?.intersection_score ?? 0,
      anomalyScore: rc.evidence?.observation_score ?? 0,
      environmentScore: 0,
      overallScore: Math.round(rc.candidate_score * 100),
    }));
  }, [isDemo, isRealActive, rankingResult]);

  const [selectedVessel, setSelectedVessel] = useState<Vessel | null>(null);
  const [aisStatus, setAisStatus] = useState<AISCollectorStatus | null>(null);
  const [recentPositions, setRecentPositions] = useState<AISVesselPosition[]>([]);

  // Sync selected vessel when active scene or mode changes
  useEffect(() => {
    if (isDemo && mockSpillCase.vessels.length > 0) {
      setSelectedVessel(mockSpillCase.vessels[0]);
    } else if (isRealActive && rankingResult?.ranking_available && vessels.length > 0) {
      const exists = selectedVessel && vessels.some(v => v.mmsi === selectedVessel.mmsi);
      setSelectedVessel(exists ? selectedVessel : vessels[0]);
    } else {
      setSelectedVessel(null);
    }
  }, [activeSceneId, isDemo, isRealActive, rankingResult, vessels]);

  useEffect(() => {
    let isMounted = true;
    getAISCollectorStatus()
      .then(st => {
        if (isMounted) setAisStatus(st);
      })
      .catch(err => {
        console.warn('Could not fetch AIS status:', err);
      });

    getRecentAISPositions(20)
      .then(pos => {
        if (isMounted) setRecentPositions(pos);
      })
      .catch(() => {});

    return () => {
      isMounted = false;
    };
  }, []);

  const scoreColor = (score: number) => {
    if (score >= 70) return '#ef4444';
    if (score >= 50) return '#f59e0b';
    if (score >= 30) return '#3b82f6';
    return '#475569';
  };

  const factorBar = (value: number) => {
    const color = value >= 0.7 ? '#ef4444' : value >= 0.5 ? '#f59e0b' : value >= 0.3 ? '#22d3ee' : '#475569';
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', width: '80px' }}>
        <div className="score-bar-track" style={{ flex: 1 }}>
          <div className="score-bar-fill" style={{ width: `${value * 100}%`, background: color }} />
        </div>
        <span style={{ fontSize: '0.6rem', color, fontWeight: 600, fontVariantNumeric: 'tabular-nums', width: '24px', textAlign: 'right' }}>
          {Math.round(value * 100)}
        </span>
      </div>
    );
  };

  // Strictly check if selected vessel panel should be shown
  const showSelectedPanel =
    selectedVessel !== null &&
    vessels.length > 0 &&
    vessels.some(v => v.mmsi === selectedVessel.mmsi) &&
    (isDemo || (isRealActive && rankingResult?.ranking_available === true));

  return (
    <div style={{ height: '100vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', background: 'var(--maritime-900)' }}>
      <TopNav />
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>

        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: '1rem', fontWeight: 700, color: '#e2e8f0' }}>
              Vessel Intelligence — <span style={{ color: '#22d3ee' }}>AIS Correlation ({currentSceneId})</span>
            </h1>
            <p style={{ fontSize: '0.62rem', color: '#475569', marginTop: '2px' }}>
              {vessels.length} candidate vessels ranked by evidence score · {currentSceneId}
            </p>
          </div>
          <div style={{ display: 'flex', gap: '6px' }}>
            <Link href="/" style={{ textDecoration: 'none' }}><button className="btn-secondary">← Dashboard</button></Link>
            <Link href="/reports" style={{ textDecoration: 'none' }}><button className="btn-primary">Generate Report →</button></Link>
          </div>
        </div>

        {/* Disclaimer */}
        <div style={{
          padding: '8px 12px',
          background: 'rgba(245, 158, 11, 0.06)',
          border: '1px solid rgba(245, 158, 11, 0.2)',
          borderRadius: '5px',
          display: 'flex',
          gap: '8px',
          alignItems: 'center',
        }}>
          <span style={{ color: '#fbbf24', fontSize: '0.8rem' }}>⚠</span>
          <p style={{ fontSize: '0.6rem', color: '#64748b', lineHeight: 1.5 }}>
            <strong style={{ color: '#fbbf24' }}>IMPORTANT DISCLAIMER:</strong>{' '}
            OceanTrace AI provides evidence-based decision support. Rankings represent statistical correlations only.
            The system does not establish legal responsibility or automatically accuse any vessel.
            All vessels listed are described as <strong style={{ color: '#94a3b8' }}>Potential Source Vessels</strong> pending further investigation.
          </p>
        </div>

        {/* Main Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: '10px', flex: 1 }}>
          {/* Table Container */}
          <div style={{ background: 'var(--maritime-850)', border: '1px solid var(--border-subtle)', borderRadius: '5px', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            {/* Table Header */}
            <div style={{ background: 'var(--maritime-800)', borderBottom: '1px solid var(--border-subtle)', padding: '6px 12px' }}>
              <div style={{
                display: 'grid',
                gridTemplateColumns: '30px 60px 140px 80px 90px 90px 90px 90px 90px 60px',
                gap: '8px',
                alignItems: 'center',
              }}>
                {['RK', 'ID', 'Vessel', 'Type', 'Spatial', 'Track', 'Window', 'Observation', 'Environ.', 'SCORE'].map(col => (
                  <div key={col} style={{ fontSize: '0.52rem', fontWeight: 700, color: '#475569', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                    {col}
                  </div>
                ))}
              </div>
            </div>

            {/* Table Body or Empty State */}
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {vessels.length === 0 ? (
                <div style={{ padding: '40px 20px', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#94a3b8', letterSpacing: '0.06em', marginBottom: '6px' }}>
                    NO AIS CANDIDATES IDENTIFIED
                  </div>
                  <div style={{ fontSize: '0.62rem', color: '#475569', maxWidth: '400px', margin: '0 auto', lineHeight: 1.5 }}>
                    {isRealActive
                      ? `Phase 6.2 / 6.3 AIS correlation engine identified 0 candidate vessels matching the spatial-temporal window for scene ${currentSceneId}.`
                      : 'No candidate vessels available for the selected scene.'}
                  </div>
                  <div style={{ marginTop: '12px' }}>
                    <span className="risk-badge not_available">RANKING NOT AVAILABLE</span>
                  </div>
                </div>
              ) : (
                vessels.map((vessel, idx) => {
                  const isSelected = selectedVessel?.id === vessel.id;
                  const isTop = idx === 0;
                  return (
                    <div
                      key={vessel.id}
                      onClick={() => setSelectedVessel(vessel)}
                      style={{
                        padding: '8px 12px',
                        borderBottom: '1px solid rgba(15, 23, 42, 0.8)',
                        cursor: 'pointer',
                        background: isSelected ? 'rgba(239,68,68,0.06)' : 'transparent',
                        borderLeft: isSelected ? '2px solid #ef4444' : '2px solid transparent',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <div style={{
                        display: 'grid',
                        gridTemplateColumns: '30px 60px 140px 80px 90px 90px 90px 90px 90px 60px',
                        gap: '8px',
                        alignItems: 'center',
                      }}>
                        {/* Rank */}
                        <div style={{
                          width: '22px', height: '22px', borderRadius: '3px',
                          background: isTop ? 'rgba(239,68,68,0.15)' : 'rgba(51,65,85,0.4)',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: '0.6rem', fontWeight: 700,
                          color: isTop ? '#f87171' : '#64748b',
                          border: `1px solid ${isTop ? 'rgba(239,68,68,0.3)' : 'rgba(51,65,85,0.4)'}`,
                        }}>
                          {String(idx + 1).padStart(2, '0')}
                        </div>
                        {/* ID */}
                        <div style={{ fontSize: '0.65rem', fontWeight: 600, color: isTop ? '#fca5a5' : '#94a3b8' }}>{vessel.id}</div>
                        {/* Name */}
                        <div>
                          <div style={{ fontSize: '0.62rem', fontWeight: 600, color: '#e2e8f0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{vessel.name}</div>
                          <div style={{ fontSize: '0.55rem', color: '#475569' }}>MMSI: {vessel.mmsi} · {vessel.flag}</div>
                        </div>
                        {/* Type */}
                        <div style={{ fontSize: '0.58rem', color: '#64748b' }}>{vessel.type}</div>
                        {/* Factors */}
                        {factorBar(vessel.proximityScore)}
                        {factorBar(vessel.trajectoryScore)}
                        {factorBar(vessel.timelineScore)}
                        {factorBar(vessel.anomalyScore)}
                        {factorBar(vessel.environmentScore)}
                        {/* Score */}
                        <div style={{ textAlign: 'center' }}>
                          <div style={{ fontSize: '1rem', fontWeight: 700, color: scoreColor(vessel.overallScore), fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
                            {vessel.overallScore}
                          </div>
                          <div style={{ fontSize: '0.48rem', color: '#475569' }}>/ 100</div>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Scoring Methodology */}
            <div style={{ padding: '8px 12px', borderTop: '1px solid var(--border-subtle)', background: 'var(--maritime-800)' }}>
              <div style={{ fontSize: '0.55rem', color: '#475569', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '4px', fontWeight: 600 }}>
                {isRealActive ? 'Phase 6.3 Configured Ranking Methodology' : 'Demo Scoring Methodology'}
              </div>
              <div style={{ display: 'flex', gap: '12px' }}>
                {currentFactors.map(f => (
                  <div key={f.key} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <div style={{ width: '3px', height: '12px', background: '#22d3ee', borderRadius: '1px' }} />
                    <span style={{ fontSize: '0.52rem', color: '#475569' }}>{f.label}: <strong style={{ color: '#64748b' }}>{Math.round(f.weight * 100)}%</strong></span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Panel — Selected Vessel or Neutral Empty State */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {showSelectedPanel && selectedVessel ? (
              <>
                <div style={{ background: 'var(--maritime-850)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: '5px', overflow: 'hidden' }}>
                  <div className="panel-header" style={{ background: 'rgba(239,68,68,0.05)' }}>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2">
                      <path d="M18 8h1a4 4 0 0 1 0 8h-1"/><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"/><line x1="6" y1="1" x2="6" y2="4"/><line x1="10" y1="1" x2="10" y2="4"/><line x1="14" y1="1" x2="14" y2="4"/>
                    </svg>
                    <span className="label-sm" style={{ color: '#94a3b8', flex: 1 }}>Selected Vessel</span>
                    <span className="risk-badge critical">POTENTIAL SOURCE</span>
                  </div>
                  <div style={{ padding: '10px' }}>
                    <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#fca5a5', marginBottom: '2px' }}>{selectedVessel.id}</div>
                    <div style={{ fontSize: '0.65rem', color: '#64748b', marginBottom: '8px' }}>{selectedVessel.name}</div>
                    {[
                      ['MMSI', selectedVessel.mmsi],
                      ['Type', selectedVessel.type],
                      ['Flag', selectedVessel.flag],
                      ['Length', selectedVessel.length ? `${selectedVessel.length} m` : 'NOT AVAILABLE'],
                      ['Beam', selectedVessel.beam ? `${selectedVessel.beam} m` : 'NOT AVAILABLE'],
                      ['Distance to Origin', selectedVessel.distanceToOriginKm ? `${selectedVessel.distanceToOriginKm.toFixed(1)} km` : 'N/A'],
                      ['Correlation Score', `${Math.round(selectedVessel.confidence * 100)}%`],
                    ].map(([label, value]) => (
                      <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid rgba(30,41,59,0.8)' }}>
                        <span style={{ fontSize: '0.58rem', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
                        <span style={{ fontSize: '0.62rem', fontWeight: 600, color: '#94a3b8' }}>{value}</span>
                      </div>
                    ))}
                    {/* Overall Score */}
                    <div style={{ textAlign: 'center', padding: '10px 0', marginTop: '4px' }}>
                      <div style={{ fontSize: '2.2rem', fontWeight: 700, color: scoreColor(selectedVessel.overallScore), fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
                        {selectedVessel.overallScore}
                      </div>
                      <div style={{ fontSize: '0.54rem', color: '#475569', letterSpacing: '0.08em', textTransform: 'uppercase', marginTop: '4px' }}>
                        ENGINEERING CORRELATION SCORE / 100
                      </div>
                    </div>
                  </div>
                </div>

                {/* Radar Chart */}
                <div style={{ background: 'var(--maritime-850)', border: '1px solid var(--border-subtle)', borderRadius: '5px', overflow: 'hidden' }}>
                  <div className="panel-header">
                    <span className="label-sm" style={{ color: '#94a3b8' }}>Factor Analysis</span>
                  </div>
                  <VesselRadar vessel={selectedVessel} factors={currentFactors} />
                </div>
              </>
            ) : (
              <>
                <div style={{ background: 'var(--maritime-850)', border: '1px solid var(--border-subtle)', borderRadius: '5px', overflow: 'hidden', padding: '16px 12px', textAlign: 'center' }}>
                  <div className="panel-header" style={{ background: 'transparent', borderBottom: 'none', justifyContent: 'center', padding: 0, marginBottom: '8px' }}>
                    <span className="label-sm" style={{ color: '#64748b' }}>Selected Vessel</span>
                  </div>
                  <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', letterSpacing: '0.04em', marginBottom: '4px' }}>
                    NO VESSEL SELECTED
                  </div>
                  <div style={{ fontSize: '0.58rem', color: '#475569', lineHeight: 1.4 }}>
                    {vessels.length === 0 ? 'Ranking Not Available for current scene.' : 'Select a candidate from the table to view correlation evidence.'}
                  </div>
                  <div style={{ marginTop: '12px', padding: '8px', background: 'rgba(30,41,59,0.4)', borderRadius: '4px', border: '1px solid rgba(51,65,85,0.4)' }}>
                    <div style={{ fontSize: '0.52rem', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '2px' }}>Candidate Status</div>
                    <div style={{ fontSize: '0.65rem', fontWeight: 600, color: '#64748b' }}>—</div>
                  </div>
                </div>

                {/* Neutral Radar Placeholder */}
                <div style={{ background: 'var(--maritime-850)', border: '1px solid var(--border-subtle)', borderRadius: '5px', overflow: 'hidden' }}>
                  <div className="panel-header">
                    <span className="label-sm" style={{ color: '#94a3b8' }}>Factor Analysis</span>
                  </div>
                  <VesselRadar vessel={null} factors={currentFactors} />
                </div>
              </>
            )}

            <button className="btn-danger" style={{ width: '100%', justifyContent: 'center', opacity: showSelectedPanel ? 1 : 0.5, cursor: showSelectedPanel ? 'pointer' : 'not-allowed' }} disabled={!showSelectedPanel}>
              Open Investigation File
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
