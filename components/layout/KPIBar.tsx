'use client';

import {
  SpillCase,
  Phase1Result,
  Phase2Result,
  Phase3Result,
  Phase4Result,
  Phase5Result,
  AISCorrelationResponse,
  AISRankingResponse,
  InvestigationReportResponse,
} from '@/types';

interface Props {
  spillCase: SpillCase;
  analysisComplete: boolean;
  phase1Data?: Phase1Result | null;
  phase2Data?: Phase2Result | null;
  phase3Data?: Phase3Result | null;
  phase4Data?: Phase4Result | null;
  phase5Data?: Phase5Result | null;
  correlationResult?: AISCorrelationResponse | null;
  rankingResult?: AISRankingResponse | null;
  investigationReport?: InvestigationReportResponse | null;
  isDemo?: boolean;
}

interface KPIProps {
  label: string;
  value: string;
  sub?: string;
  color?: string;
  blink?: boolean;
}

function KPI({ label, value, sub, color = '#e2e8f0', blink = false }: KPIProps) {
  return (
    <div
      style={{
        background: 'var(--maritime-800)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '5px',
        padding: '6px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '1px',
        flex: 1,
        minWidth: 0,
      }}
    >
      <div style={{ fontSize: '0.52rem', color: '#475569', letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 600 }}>
        {label}
      </div>
      <div
        style={{
          fontSize: '1.1rem',
          fontWeight: 700,
          color,
          fontVariantNumeric: 'tabular-nums',
          lineHeight: 1.1,
          animation: blink ? 'pulse-warning 2s infinite' : 'none',
        }}
      >
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: '0.5rem', color: '#334155', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          {sub}
        </div>
      )}
    </div>
  );
}

export default function KPIBar({
  spillCase,
  analysisComplete,
  phase1Data,
  phase2Data,
  phase3Data,
  phase4Data,
  phase5Data,
  correlationResult,
  rankingResult,
  investigationReport,
  isDemo = false,
}: Props) {
  const { spill, originZone, vessels } = spillCase;
  const topVessel = [...vessels].sort((a, b) => b.overallScore - a.overallScore)[0];

  const caseIdDisplay = isDemo
    ? spillCase.id
    : phase1Data
    ? phase1Data.output_filename.replace('_processed.tif', '')
    : 'AWAITING REAL RUN';

  const dateDisplay = isDemo
    ? new Date(spillCase.detectedAt).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' })
    : phase1Data?.acquisition_time
    ? new Date(phase1Data.acquisition_time).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' })
    : 'REAL MODE';

  const oilDetectedValue = isDemo
    ? (analysisComplete ? 'YES' : '—')
    : (analysisComplete && (phase3Data || phase2Data) ? ((phase3Data?.spill_detected ?? phase2Data?.detected) ? 'YES' : 'NO') : '—');

  const oilDetectedColor = isDemo
    ? '#ef4444'
    : (analysisComplete && (phase3Data || phase2Data) ? ((phase3Data?.spill_detected ?? phase2Data?.detected) ? '#ef4444' : '#10b981') : '#64748b');

  const oilDetectedSub = isDemo ? 'Sentinel-1 SAR' : (phase2Data ? 'PyTorch U-Net' : 'Phase 2 Req.');

  const confidenceValue = isDemo
    ? (analysisComplete ? `${Math.round(spill.confidence * 100)}%` : '—')
    : (analysisComplete && phase2Data ? `${(phase2Data.confidence * 100).toFixed(1)}%` : '—');

  const spillAreaValue = isDemo
    ? (analysisComplete ? `${spill.areaKm2} km²` : '—')
    : (analysisComplete && phase3Data ? `${phase3Data.total_area_km2.toFixed(2)} km²` : '0.00 km²');

  const spillAreaSub = isDemo ? 'Estimated' : (phase3Data ? 'Phase 3 GIS' : 'Phase 3 Req.');

  const spillAreaColor = isDemo ? '#fbbf24' : (phase3Data && phase3Data.spill_detected ? '#fbbf24' : '#64748b');

  const originConfValue = isDemo
    ? (analysisComplete ? `${Math.round(originZone.confidence * 100)}%` : '—')
    : (analysisComplete && phase5Data
      ? (phase5Data.origin_available ? `${(phase5Data.origin.confidence * 100).toFixed(1)}%` : 'NOT AVAILABLE')
      : '—');

  const originConfColor = isDemo
    ? '#22d3ee'
    : (phase5Data?.origin_available ? '#22d3ee' : '#64748b');

  const candidatesValue = isDemo
    ? (analysisComplete ? String(vessels.length).padStart(2, '0') : '—')
    : (correlationResult
      ? (correlationResult.correlation_available ? String(correlationResult.candidate_count).padStart(2, '0') : '00')
      : '—');

  const topVesselValue = isDemo
    ? (analysisComplete ? `${topVessel.overallScore} / 100` : '—')
    : (rankingResult && rankingResult.ranking_available && rankingResult.ranked_candidates.length > 0
      ? `${rankingResult.ranked_candidates[0].candidate_score} / 100`
      : '—');

  const coastalRiskValue = isDemo
    ? (analysisComplete ? spillCase.riskLevel : '—')
    : (investigationReport
      ? (investigationReport.operational_alert?.attention_level === 'NO_EVENT' ? 'NO EVENT' : investigationReport.operational_alert?.attention_level || 'NOT AVAILABLE')
      : 'NOT AVAILABLE');

  const windSpeedValue = isDemo
    ? `${spillCase.environment.windSpeed} m/s`
    : (analysisComplete && phase4Data ? `${phase4Data.wind.speed_ms.toFixed(1)} m/s` : '—');

  const windSpeedSub = isDemo
    ? `Dir: ${spillCase.environment.windDirection}°`
    : (analysisComplete && phase4Data ? `Dir: ${phase4Data.wind.direction_deg.toFixed(0)}°` : 'Phase 4 Env Req.');

  const currSpeedValue = isDemo
    ? `${spillCase.environment.currentSpeed} m/s`
    : (analysisComplete && phase4Data ? `${phase4Data.ocean_current.speed_ms.toFixed(2)} m/s` : '—');

  const currSpeedSub = isDemo
    ? `Dir: ${spillCase.environment.currentDirection}°`
    : (analysisComplete && phase4Data ? `Dir: ${phase4Data.ocean_current.direction_deg.toFixed(0)}°` : 'Phase 4 Env Req.');

  return (
    <div
      style={{
        gridColumn: '2 / 3',
        background: 'var(--maritime-900)',
        borderBottom: '1px solid var(--border-subtle)',
        padding: '6px 10px',
        display: 'flex',
        gap: '6px',
        alignItems: 'stretch',
        flexShrink: 0,
        overflowX: 'auto',
      }}
    >
      {/* Case ID */}
      <div
        style={{
          background: 'var(--maritime-800)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '5px',
          padding: '6px 12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '1px',
          flexShrink: 0,
        }}
      >
        <div style={{ fontSize: '0.52rem', color: '#475569', letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 600 }}>
          {isDemo ? 'Case ID (DEMO)' : 'Scene / Case ID'}
        </div>
        <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#22d3ee', fontVariantNumeric: 'tabular-nums', fontFamily: 'monospace' }}>
          {caseIdDisplay}
        </div>
        <div style={{ fontSize: '0.5rem', color: '#334155' }}>
          {dateDisplay}
        </div>
      </div>

      {/* Oil Spill Detected */}
      <KPI
        label="Oil Spill Detected"
        value={oilDetectedValue}
        sub={oilDetectedSub}
        color={oilDetectedColor}
        blink={Boolean((isDemo && analysisComplete) || (phase3Data?.spill_detected || phase2Data?.detected))}
      />

      {/* Spill Area */}
      <KPI
        label="Spill Area"
        value={spillAreaValue}
        sub={spillAreaSub}
        color={spillAreaColor}
      />

      {/* Model Confidence */}
      <KPI
        label="MODEL CONFIDENCE"
        value={confidenceValue}
        sub={isDemo ? 'AI Model' : (phase2Data ? 'PyTorch U-Net' : 'Phase 2 Req.')}
        color={isDemo ? '#22d3ee' : (phase2Data ? '#22d3ee' : '#64748b')}
      />

      {/* Origin Confidence */}
      <KPI
        label="Origin Confidence"
        value={originConfValue}
        sub={isDemo ? 'Backward Drift' : (phase5Data ? (phase5Data.origin_available ? 'Phase 5 Drift' : 'Unavailable') : 'Phase 5 Req.')}
        color={originConfColor}
      />

      {/* Candidate Vessels */}
      <KPI
        label="Candidate Vessels"
        value={candidatesValue}
        sub={isDemo ? 'AIS Correlated' : 'Phase 6 AIS'}
        color="#64748b"
      />

      {/* Top Vessel Score */}
      <KPI
        label="Top Vessel Score"
        value={topVesselValue}
        sub={isDemo ? (analysisComplete ? topVessel.id : 'No data') : 'Phase 6.3 Rank'}
        color={isDemo ? '#ef4444' : '#64748b'}
      />

      {/* Coastal Risk */}
      <div
        style={{
          background: isDemo && analysisComplete ? 'rgba(239, 68, 68, 0.06)' : 'var(--maritime-800)',
          border: `1px solid ${isDemo && analysisComplete ? 'rgba(239, 68, 68, 0.25)' : 'var(--border-subtle)'}`,
          borderRadius: '5px',
          padding: '6px 12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '1px',
          flex: 1,
          minWidth: 0,
        }}
      >
        <div style={{ fontSize: '0.52rem', color: '#475569', letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 600 }}>
          Coastal Risk
        </div>
        <div
          style={{
            fontSize: '1.1rem',
            fontWeight: 700,
            color: isDemo && analysisComplete ? '#ef4444' : (coastalRiskValue === 'NO EVENT' ? '#22d3ee' : '#64748b'),
            lineHeight: 1.1,
            textTransform: 'uppercase',
          }}
        >
          {coastalRiskValue}
        </div>
        {isDemo && analysisComplete && (
          <div style={{ fontSize: '0.5rem', color: '#ef4444', letterSpacing: '0.06em' }}>
            {spillCase.coastalThreats.length} threats identified
          </div>
        )}
      </div>

      {/* Wind */}
      <KPI
        label="Wind Speed"
        value={windSpeedValue}
        sub={windSpeedSub}
        color={isDemo ? '#64748b' : (phase4Data ? '#22d3ee' : '#64748b')}
      />

      {/* Current */}
      <KPI
        label="Ocean Current"
        value={currSpeedValue}
        sub={currSpeedSub}
        color={isDemo ? '#64748b' : (phase4Data ? '#06b6d4' : '#64748b')}
      />
    </div>
  );
}


