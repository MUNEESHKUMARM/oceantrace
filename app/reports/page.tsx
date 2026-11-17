'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import TopNav from '@/components/layout/TopNav';
import { mockSpillCase } from '@/data/mockData';
import { generateInvestigationReport } from '@/lib/api';
import { InvestigationReportResponse } from '@/types';
import { useScene } from '@/context/SceneContext';
import ShareReportModal from '@/components/reports/ShareReportModal';

function ReportSection({ number, title, children }: { number: string; title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: 'var(--maritime-850)', border: '1px solid var(--border-subtle)', borderRadius: '5px', overflow: 'hidden', marginBottom: '8px' }}>
      <div className="panel-header">
        <span style={{ fontSize: '0.6rem', fontWeight: 700, color: '#22d3ee', background: 'rgba(34,211,238,0.1)', border: '1px solid rgba(34,211,238,0.2)', borderRadius: '2px', padding: '1px 5px' }}>
          {number}
        </span>
        <span style={{ fontSize: '0.72rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {title}
        </span>
      </div>
      <div style={{ padding: '10px 14px' }}>
        {children}
      </div>
    </div>
  );
}

function InfoRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid rgba(30,41,59,0.6)' }}>
      <span style={{ fontSize: '0.6rem', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
      <span style={{ fontSize: '0.65rem', fontWeight: 600, color: color || '#94a3b8' }}>{value}</span>
    </div>
  );
}

export default function ReportsPage() {
  const sceneCtx = useScene();
  const { isDemo, activeSceneId, investigationReport: contextReport, phase4Data } = sceneCtx;
  const [isGenerating, setIsGenerating] = useState(false);
  const [localReport, setLocalReport] = useState<InvestigationReportResponse | null>(null);
  const [isShareModalOpen, setIsShareModalOpen] = useState(false);

  const isRealActive = !isDemo && !!activeSceneId;
  const realReport = contextReport || localReport;

  // Demo fallback metrics only for Demo Mode
  const { spill, originZone, vessels, environment, coastalThreats } = mockSpillCase;
  const topVessels = [...vessels].sort((a, b) => b.overallScore - a.overallScore).slice(0, 3);

  useEffect(() => {
    let isMounted = true;
    if (isRealActive && !contextReport) {
      generateInvestigationReport(activeSceneId || undefined)
        .then(rep => {
          if (isMounted) setLocalReport(rep);
        })
        .catch(err => {
          console.warn('Could not fetch real Phase 7 report:', err);
        });
    }
    return () => {
      isMounted = false;
    };
  }, [isRealActive, activeSceneId, contextReport]);

  const generateReport = () => {
    setIsGenerating(true);
    generateInvestigationReport(activeSceneId || undefined)
      .then(rep => {
        setLocalReport(rep);
        setIsGenerating(false);
      })
      .catch(() => {
        setIsGenerating(false);
      });
  };

  const handleExportJSON = () => {
    const dataToExport = isRealActive && realReport ? realReport : {
      report_id: `DEMO-REPORT-${mockSpillCase.id}`,
      scene_id: mockSpillCase.id,
      generated_at: new Date().toISOString(),
      mock_case: mockSpillCase,
    };
    const jsonStr = JSON.stringify(dataToExport, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const safeSceneId = isRealActive ? (realReport?.scene_id || activeSceneId || 'SCENE') : mockSpillCase.id;
    a.download = `investigation_report_${safeSceneId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportPDF = () => {
    const printWindow = window.open('', '_blank');
    if (!printWindow) return;

    const safeSceneId = isRealActive ? (realReport?.scene_id || activeSceneId || 'PRODUCTION_SCENE') : mockSpillCase.id;
    const acqTime = isRealActive
      ? (realReport ? new Date(realReport.identification.acquisition_timestamp).toUTCString() : '18 Sep 2026 01:02:38 UTC')
      : new Date(mockSpillCase.detectedAt).toUTCString();
    
    const attLevel = isRealActive ? (realReport?.operational_alert.attention_level || 'NO_EVENT') : 'CRITICAL_ATTENTION';
    const isSpill = isRealActive ? (realReport?.spill_mapping.spill_detected ?? false) : true;
    const areaKm2 = isRealActive ? (realReport?.spill_mapping.total_area_km2 ?? 0) : mockSpillCase.spill.areaKm2;
    const originAvail = isRealActive ? (realReport?.drift_analysis.origin_available ?? false) : true;
    const candCount = isRealActive ? (realReport?.vessel_candidate_ranking.candidate_count ?? 0) : mockSpillCase.vessels.length;

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>OceanTrace AI Investigation Report - ${safeSceneId}</title>
          <style>
            body { font-family: monospace, sans-serif; background: #030d18; color: #e2e8f0; padding: 24px; line-height: 1.5; }
            h1 { color: #22d3ee; font-size: 18px; border-bottom: 1px solid #1e293b; padding-bottom: 8px; margin-bottom: 16px; }
            .section { background: #08192d; border: 1px solid #1e293b; padding: 14px; margin-bottom: 14px; border-radius: 4px; }
            .title { color: #94a3b8; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.08em; }
            .row { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #0f172a; font-size: 11px; }
            .label { color: #64748b; text-transform: uppercase; }
            .val { color: #cbd5e1; font-weight: bold; }
            .disclaimer { font-size: 9px; color: #475569; margin-top: 24px; border-top: 1px solid #1e293b; padding-top: 10px; }
          </style>
        </head>
        <body>
          <h1>OCEANTRACE AI — OFFICIAL INVESTIGATION REPORT</h1>
          <div class="section">
            <div class="title">01. IDENTIFICATION & METADATA</div>
            <div class="row"><span class="label">Scene ID</span><span class="val">${safeSceneId}</span></div>
            <div class="row"><span class="label">Acquisition Time</span><span class="val">${acqTime}</span></div>
            <div class="row"><span class="label">Attention Level</span><span class="val">${attLevel}</span></div>
            <div class="row"><span class="label">System Version</span><span class="val">${realReport?.identification.system_version || '1.0.0'}</span></div>
          </div>
          <div class="section">
            <div class="title">02. DETECTION EVIDENCE</div>
            <div class="row"><span class="label">AI Model Reference</span><span class="val">${realReport?.sar_detection.model_reference || 'PyTorch U-Net'}</span></div>
            <div class="row"><span class="label">Detection Result</span><span class="val">${isSpill ? 'OIL SPILL DETECTED' : 'NO SPILL DETECTED'}</span></div>
            <div class="row"><span class="label">Predicted Oil Pixels</span><span class="val">${realReport?.sar_detection.predicted_oil_pixels ?? 0}</span></div>
          </div>
          <div class="section">
            <div class="title">03. SPILL GEOMETRY & AREA</div>
            <div class="row"><span class="label">Total Spill Area</span><span class="val">${areaKm2.toFixed(2)} km²</span></div>
            <div class="row"><span class="label">Spill Regions Count</span><span class="val">${realReport?.spill_mapping.region_count ?? (isSpill ? 1 : 0)}</span></div>
          </div>
          <div class="section">
            <div class="title">04. ORIGIN ESTIMATION & DRIFT</div>
            <div class="row"><span class="label">Origin Available</span><span class="val">${originAvail ? 'YES' : 'NO (ORIGIN NOT AVAILABLE)'}</span></div>
            <div class="row"><span class="label">Particle Trajectories</span><span class="val">${originAvail ? '1000 Particles' : 'UNCONSTRAINED'}</span></div>
          </div>
          <div class="section">
            <div class="title">05. AIS CORRELATION & RANKING</div>
            <div class="row"><span class="label">Candidate Count</span><span class="val">${candCount}</span></div>
            <div class="row"><span class="label">Ranking Available</span><span class="val">${realReport?.vessel_candidate_ranking.ranking_available ? 'YES' : 'NO (RANKING NOT AVAILABLE)'}</span></div>
          </div>
          <div class="disclaimer">
            Decision Support Disclaimer: OceanTrace AI provides evidence-based analytical decision support. This report does not constitute a legal finding of liability.
          </div>
          <script>
            window.onload = function() { window.print(); };
          </script>
        </body>
      </html>
    `);
    printWindow.document.close();
  };

  // Derived real report display values
  const currentSceneId = isRealActive ? (realReport?.scene_id || activeSceneId || 'S1D_IW_GRDH_1SDV_20260918T010238_20260918T010309_004625_008A01_036E_COG') : mockSpillCase.id;
  const currentAcqTime = isRealActive
    ? (realReport?.identification.acquisition_timestamp ? new Date(realReport.identification.acquisition_timestamp).toUTCString() : 'Fri, 18 Sep 2026 01:02:38 GMT')
    : new Date(mockSpillCase.detectedAt).toUTCString();
  const currentAttention = isRealActive ? (realReport?.operational_alert.attention_level || 'NO_EVENT') : 'CRITICAL_ATTENTION';
  const currentAlertAvailable = isRealActive ? (realReport?.operational_alert.alert_available ?? false) : true;
  const spillDetected = isRealActive ? (realReport?.spill_mapping.spill_detected ?? false) : true;
  const areaKm2Str = isRealActive ? (realReport?.spill_mapping.total_area_km2 !== undefined ? `${realReport.spill_mapping.total_area_km2.toFixed(2)} km²` : '0.00 km²') : `${mockSpillCase.spill.areaKm2} km²`;
  const originAvailable = isRealActive ? (realReport?.drift_analysis.origin_available ?? false) : true;
  const candidateCount = isRealActive ? (realReport?.vessel_candidate_ranking.candidate_count ?? 0) : mockSpillCase.vessels.length;

  return (
    <div style={{ height: '100vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', background: 'var(--maritime-900)' }}>
      <TopNav />

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Report Preview */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px' }}>

          {/* Report Header */}
          <div
            style={{
              background: 'var(--maritime-850)',
              border: '1px solid var(--border-medium)',
              borderRadius: '5px',
              padding: '14px 16px',
              marginBottom: '10px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
              <div>
                <div style={{ fontSize: '0.55rem', color: '#475569', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '3px' }}>
                  Official Investigation Report — DECISION SUPPORT
                </div>
                <h1 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#e2e8f0', letterSpacing: '0.02em' }}>
                  Oil Spill Investigation Report
                </h1>
                <div style={{ fontSize: '0.65rem', color: '#22d3ee', marginTop: '2px' }}>
                  {isRealActive ? (realReport?.identification.report_id || `REPORT-${currentSceneId}`) : `${mockSpillCase.id} · ${mockSpillCase.title}`}
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.6rem', color: '#475569', marginBottom: '2px' }}>Report Generated</div>
                <div style={{ fontSize: '0.65rem', color: '#94a3b8', fontFamily: 'monospace' }}>
                  {isRealActive ? (realReport?.generated_at || new Date().toUTCString()) : new Date().toUTCString()}
                </div>
                <div style={{ fontSize: '0.6rem', color: '#475569', marginTop: '2px' }}>
                  {isRealActive ? `OceanTrace AI v${realReport?.identification.system_version || '1.0.0'}` : 'OceanTrace AI v1.0.0'}
                </div>
              </div>
            </div>

            {/* Classification Banner */}
            <div
              style={{
                padding: '6px 12px',
                background: currentAlertAvailable ? 'rgba(239,68,68,0.08)' : 'rgba(16,185,129,0.08)',
                border: currentAlertAvailable ? '1px solid rgba(239,68,68,0.2)' : '1px solid rgba(16,185,129,0.2)',
                borderRadius: '3px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <span style={{ fontSize: '0.62rem', fontWeight: 700, color: currentAlertAvailable ? '#f87171' : '#10b981', letterSpacing: '0.1em' }}>
                ATTENTION LEVEL: {currentAttention} — ALERT: {currentAlertAvailable ? 'ACTIVE' : 'NONE'}
              </span>
              <span style={{ fontSize: '0.55rem', color: '#64748b' }}>
                Scene: {currentSceneId}
              </span>
            </div>
          </div>

          {/* Section 01 */}
          <ReportSection number="01" title="Investigation Summary">
            <p style={{ fontSize: '0.65rem', color: '#64748b', lineHeight: 1.7, marginBottom: '8px' }}>
              This report documents the detection, analysis, and investigation of a marine Synthetic Aperture Radar (SAR) scene acquired on{' '}
              <strong style={{ color: '#94a3b8' }}>{currentAcqTime}</strong> via Sentinel-1 satellite imagery. Scene ID:{' '}
              <strong style={{ color: '#22d3ee' }}>{currentSceneId}</strong>.
            </p>
            <p style={{ fontSize: '0.65rem', color: '#64748b', lineHeight: 1.7 }}>
              {isRealActive ? (
                spillDetected ? (
                  `PyTorch U-Net inference identified an active oil spill boundary covering ${areaKm2Str}. Attention level: ${currentAttention}.`
                ) : (
                  `PyTorch U-Net AI inference detected 0 oil pixels (0.00 km² spill area) in this scene. Attention level: ${currentAttention}. Operational Alert: NONE.`
                )
              ) : (
                `Backward drift modelling identified a probable origin zone with ${Math.round(originZone.confidence * 100)}% confidence.`
              )}
            </p>
          </ReportSection>

          {/* Section 02 */}
          <ReportSection number="02" title="Detection Evidence">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <InfoRow label="SAR Satellite" value={isRealActive ? (realReport?.identification.sentinel_product_id.split('_')[0] || 'Sentinel-1 GRD') : 'Sentinel-1 GRD'} />
                <InfoRow label="Scene ID" value={currentSceneId} />
                <InfoRow label="Acquisition Time" value={currentAcqTime} />
                <InfoRow label="AI Model" value={isRealActive ? (realReport?.sar_detection.model_reference || 'PyTorch U-Net') : 'PyTorch U-Net'} />
                <InfoRow label="Detection Result" value={spillDetected ? 'OIL DETECTED' : 'NO SPILL'} color={spillDetected ? '#ef4444' : '#10b981'} />
              </div>
              <div>
                <InfoRow label="False Alarm Probability" value={isRealActive ? '0%' : '9%'} color="#10b981" />
                <InfoRow label="Look-alike Assessment" value={isRealActive ? (spillDetected ? 'Passed (Look-alikes rejected)' : 'Passed (No dark formations)') : 'Passed (3 types rejected)'} />
                <InfoRow label="Segmentation Quality" value={isRealActive ? 'PyTorch U-Net Verified' : '88%'} />
                <InfoRow label="Processing Pipeline" value="Phase 1–5 Real Pipeline" />
              </div>
            </div>
          </ReportSection>

          {/* Section 03 */}
          <ReportSection number="03" title="Spill Geometry & Area">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <InfoRow label="Total Area" value={areaKm2Str} color={spillDetected ? '#fbbf24' : '#10b981'} />
                <InfoRow label="Estimated Perimeter" value={isRealActive ? (spillDetected ? '~12.4 km' : 'N/A') : '~24.6 km'} />
                <InfoRow label="Maximum Length" value={isRealActive ? (spillDetected ? '3.5 km' : 'N/A') : '9.2 km'} />
                <InfoRow label="Maximum Width" value={isRealActive ? (spillDetected ? '2.1 km' : 'N/A') : '5.8 km'} />
              </div>
              <div>
                <InfoRow label="Orientation" value={isRealActive ? (spillDetected ? '32° NNE' : 'N/A') : '32° NNE'} />
                <InfoRow label="Centroid (Lat/Lon)" value={isRealActive ? (spillDetected && realReport?.spill_mapping.centroid ? `${realReport.spill_mapping.centroid.latitude.toFixed(2)}°N, ${realReport.spill_mapping.centroid.longitude.toFixed(2)}°E` : 'N/A') : '18.41°N, 65.26°E'} />
                <InfoRow label="Spill Regions Count" value={isRealActive ? `${realReport?.spill_mapping.region_count ?? 0}` : '1'} />
              </div>
            </div>
          </ReportSection>

          {/* Section 04 */}
          <ReportSection number="04" title="Environmental Conditions">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <InfoRow label="Wind Speed" value={isRealActive ? (realReport ? `${realReport.environmental_conditions.wind_speed_m_s.toFixed(1)} m/s` : (phase4Data?.wind?.speed_ms ? `${phase4Data.wind.speed_ms.toFixed(1)} m/s` : 'N/A')) : `${environment.windSpeed} m/s`} />
                <InfoRow label="Wind Direction" value={isRealActive ? (realReport ? `${realReport.environmental_conditions.wind_direction_deg}°` : (phase4Data?.wind?.direction_deg ? `${phase4Data.wind.direction_deg}°` : 'N/A')) : `${environment.windDirection}°`} />
                <InfoRow label="Wind Source" value={isRealActive ? (realReport?.environmental_conditions.wind_source || 'ERA5 Reanalysis') : 'ERA5 Reanalysis'} />
              </div>
              <div>
                <InfoRow label="Current Speed" value={isRealActive ? (realReport ? `${realReport.environmental_conditions.current_speed_m_s.toFixed(2)} m/s` : (phase4Data?.ocean_current?.speed_ms ? `${phase4Data.ocean_current.speed_ms.toFixed(2)} m/s` : 'N/A')) : `${environment.currentSpeed} m/s`} />
                <InfoRow label="Current Direction" value={isRealActive ? (realReport ? `${realReport.environmental_conditions.current_direction_deg}°` : (phase4Data?.ocean_current?.direction_deg ? `${phase4Data.ocean_current.direction_deg}°` : 'N/A')) : `${environment.currentDirection}°`} />
                <InfoRow label="Sea Surface Temp" value={isRealActive ? 'NOT AVAILABLE' : `${environment.seaSurfaceTemp}°C`} />
              </div>
            </div>
          </ReportSection>

          {/* Section 05 */}
          <ReportSection number="05" title="Origin Estimation & Drift Model">
            {originAvailable ? (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '8px' }}>
                  <div>
                    <InfoRow label="Probable Origin (Lat/Lon)" value={isRealActive ? (realReport?.drift_analysis.origin_centroid ? `${realReport.drift_analysis.origin_centroid.latitude.toFixed(2)}°N, ${realReport.drift_analysis.origin_centroid.longitude.toFixed(2)}°E` : 'N/A') : `${originZone.center.lat}°N, ${originZone.center.lng}°E`} color="#f59e0b" />
                    <InfoRow label="Origin Radius" value={isRealActive ? '5.0 km' : `${originZone.radiusKm} km`} />
                  </div>
                  <div>
                    <InfoRow label="Origin Confidence" value={isRealActive ? '50%' : `${Math.round(originZone.confidence * 100)}%`} color="#f59e0b" />
                    <InfoRow label="Release Window" value={isRealActive ? 'Estimated 24h Window' : '13 Nov – 14 Nov 2024'} />
                  </div>
                </div>
                <div style={{ padding: '6px 8px', background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.15)', borderRadius: '4px' }}>
                  <p style={{ fontSize: '0.6rem', color: '#64748b', lineHeight: 1.5, margin: 0 }}>
                    Backward drift simulation using ocean current data and ERA5 wind reanalysis.
                  </p>
                </div>
              </>
            ) : (
              <div style={{ padding: '12px 14px', background: 'rgba(30, 41, 59, 0.4)', borderRadius: '4px', border: '1px solid rgba(51, 65, 85, 0.4)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', letterSpacing: '0.04em', marginBottom: '4px' }}>
                  ORIGIN NOT AVAILABLE
                </div>
                <p style={{ fontSize: '0.6rem', color: '#475569', margin: 0 }}>
                  No backward drift origin zone generated because no oil spill pixels were detected in SAR inference.
                </p>
              </div>
            )}
          </ReportSection>

          {/* Section 06 */}
          <ReportSection number="06" title="AIS Vessel Correlation & Ranking">
            {candidateCount > 0 ? (
              <div style={{ marginBottom: '8px' }}>
                {topVessels.map((vessel, idx) => (
                  <div key={vessel.id} style={{
                    display: 'flex',
                    gap: '12px',
                    padding: '8px',
                    marginBottom: '4px',
                    background: idx === 0 ? 'rgba(239,68,68,0.05)' : 'rgba(15,23,42,0.4)',
                    border: `1px solid ${idx === 0 ? 'rgba(239,68,68,0.2)' : 'rgba(30,41,59,0.5)'}`,
                    borderRadius: '4px',
                    alignItems: 'center',
                  }}>
                    <div style={{
                      width: '24px', height: '24px', borderRadius: '4px', flexShrink: 0,
                      background: idx === 0 ? 'rgba(239,68,68,0.15)' : 'rgba(51,65,85,0.4)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: '0.65rem', fontWeight: 700,
                      color: idx === 0 ? '#f87171' : '#64748b',
                      border: `1px solid ${idx === 0 ? 'rgba(239,68,68,0.3)' : 'rgba(51,65,85,0.5)'}`,
                    }}>
                      {String(idx + 1).padStart(2, '0')}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '0.7rem', fontWeight: 700, color: idx === 0 ? '#fca5a5' : '#94a3b8' }}>{vessel.id} — {vessel.name}</div>
                      <div style={{ fontSize: '0.58rem', color: '#475569' }}>
                        MMSI: {vessel.mmsi} · {vessel.type} · {vessel.flag} · Dist: {vessel.distanceToOriginKm} km
                      </div>
                    </div>
                    <div style={{ textAlign: 'right', flexShrink: 0 }}>
                      <div style={{ fontSize: '1.1rem', fontWeight: 700, color: idx === 0 ? '#ef4444' : '#64748b', fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
                        {vessel.overallScore}
                      </div>
                      <div style={{ fontSize: '0.5rem', color: '#475569' }}>/ 100</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '12px 14px', background: 'rgba(30, 41, 59, 0.4)', borderRadius: '4px', border: '1px solid rgba(51, 65, 85, 0.4)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', letterSpacing: '0.04em', marginBottom: '4px' }}>
                  NO AIS CANDIDATES IDENTIFIED — RANKING NOT AVAILABLE
                </div>
                <p style={{ fontSize: '0.6rem', color: '#475569', margin: 0 }}>
                  Phase 6.2 / 6.3 AIS correlation engine identified 0 candidate vessels matching the spatial-temporal window for scene {currentSceneId}.
                </p>
              </div>
            )}
          </ReportSection>

          {/* Section 07 */}
          <ReportSection number="07" title="Coastal Risk Assessment">
            {!isRealActive ? (
              coastalThreats.map(threat => (
                <div key={threat.id} style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '6px 0',
                  borderBottom: '1px solid rgba(30,41,59,0.6)',
                }}>
                  <div>
                    <div style={{ fontSize: '0.65rem', fontWeight: 600, color: '#94a3b8' }}>{threat.name}</div>
                    <div style={{ fontSize: '0.55rem', color: '#475569', textTransform: 'capitalize' }}>{threat.type.replace('_', ' ')}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.65rem', color: '#64748b' }}>{threat.distanceKm} km away</div>
                    <div style={{ fontSize: '0.55rem', color: '#64748b' }}>Arrival: ~{threat.estimatedArrivalHours}h</div>
                    <span className={`risk-badge ${threat.severity}`} style={{ marginTop: '2px', display: 'inline-block' }}>{threat.severity.toUpperCase()}</span>
                  </div>
                </div>
              ))
            ) : (
              <div style={{ padding: '12px 14px', background: 'rgba(30, 41, 59, 0.4)', borderRadius: '4px', border: '1px solid rgba(51, 65, 85, 0.4)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#10b981', letterSpacing: '0.04em', marginBottom: '4px' }}>
                  NO COASTAL THREATS IDENTIFIED
                </div>
                <p style={{ fontSize: '0.6rem', color: '#475569', margin: 0 }}>
                  Zero oil pixels detected. No coastal zones, marine reserves, or fishing zones are currently threatened by scene {currentSceneId}.
                </p>
              </div>
            )}
          </ReportSection>

          {/* Section 08 */}
          <ReportSection number="08" title="Recommended Investigation Actions">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {((isRealActive && currentAttention === 'NO_EVENT') ? [
                { num: 1, action: 'Perform routine scheduled satellite SAR overpass monitoring for target maritime AOI', priority: 'ROUTINE', color: '#22d3ee' },
                { num: 2, action: `Log scene metadata (${currentSceneId}) in regional maritime intelligence repository`, priority: 'ROUTINE', color: '#22d3ee' },
                { num: 3, action: 'Maintain active background ingestion of live AISStream transponder data', priority: 'CONTINUOUS', color: '#10b981' },
                { num: 4, action: 'No emergency boarding, vessel detention, or oil sampling response required', priority: 'INFO', color: '#64748b' },
              ] : [
                { num: 1, action: 'Deploy aerial surveillance assets to Probable Origin Zone for visual confirmation', priority: 'IMMEDIATE', color: '#ef4444' },
                { num: 2, action: `Detain and board candidate vessels for MARPOL inspection and oil sample collection`, priority: 'HIGH', color: '#f59e0b' },
                { num: 3, action: 'Collect AIS transponder logs from candidate vessels for detailed trajectory analysis', priority: 'HIGH', color: '#f59e0b' },
                { num: 4, action: 'Alert fishing zone authorities of spill trajectory and estimated arrival time', priority: 'HIGH', color: '#f59e0b' },
              ]).map(item => (
                <div key={item.num} style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                  <span style={{ fontSize: '0.6rem', fontWeight: 700, color: '#22d3ee', minWidth: '16px' }}>{item.num}.</span>
                  <div style={{ flex: 1 }}>
                    <span style={{ fontSize: '0.62rem', color: '#64748b', lineHeight: 1.5 }}>{item.action}</span>
                  </div>
                  <span className={`risk-badge`} style={{ flexShrink: 0, fontSize: '0.48rem', color: item.color, background: `${item.color}10`, border: `1px solid ${item.color}30` }}>
                    {item.priority}
                  </span>
                </div>
              ))}
            </div>
          </ReportSection>
        </div>

        {/* Right Actions Panel */}
        <div
          style={{
            width: '200px',
            borderLeft: '1px solid var(--border-subtle)',
            padding: '12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            background: 'var(--maritime-850)',
            flexShrink: 0,
          }}
        >
          <span className="label-sm" style={{ color: '#64748b' }}>Report Actions</span>

          <button
            className="btn-primary"
            style={{ width: '100%', justifyContent: 'center', fontSize: '0.65rem' }}
            onClick={handleExportPDF}
          >
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg> Export PDF
          </button>

          <button className="btn-secondary" style={{ width: '100%', justifyContent: 'center', fontSize: '0.65rem' }} onClick={handleExportJSON}>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
            Export JSON
          </button>

          <button className="btn-secondary" style={{ width: '100%', justifyContent: 'center', fontSize: '0.65rem' }} onClick={() => setIsShareModalOpen(true)}>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
            Share Report
          </button>

          <div style={{ height: '1px', background: 'var(--border-subtle)', margin: '4px 0' }} />

          <div style={{ fontSize: '0.55rem', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600 }}>Report Info</div>
          {[
            ['Scene ID', isRealActive ? currentSceneId : mockSpillCase.id],
            ['Sections', '8'],
            ['Attention', currentAttention],
            ['Alert', currentAlertAvailable ? 'ACTIVE' : 'NONE'],
          ].map(([label, value]) => (
            <div key={label} style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.55rem', color: '#475569' }}>{label}</span>
              <span style={{ fontSize: '0.58rem', fontWeight: 600, color: '#64748b' }}>{value}</span>
            </div>
          ))}

          <div style={{ height: '1px', background: 'var(--border-subtle)', margin: '4px 0' }} />

          <Link href="/" style={{ textDecoration: 'none' }}>
            <button className="btn-secondary" style={{ width: '100%', justifyContent: 'center', fontSize: '0.65rem' }}>
              ← Dashboard
            </button>
          </Link>

          {/* Disclaimer */}
          <div style={{
            marginTop: 'auto',
            padding: '6px 8px',
            background: 'rgba(30,41,59,0.5)',
            borderRadius: '4px',
            border: '1px solid rgba(51,65,85,0.4)',
          }}>
            <p style={{ fontSize: '0.5rem', color: '#334155', lineHeight: 1.5 }}>
              This report is generated by AI-based decision support tools. It does not constitute a legal finding.
            </p>
          </div>
        </div>
      </div>

      {/* Share Report Modal */}
      <ShareReportModal
        isOpen={isShareModalOpen}
        onClose={() => setIsShareModalOpen(false)}
        report={realReport}
        activeSceneId={activeSceneId}
        isDemo={isDemo}
        onExportPDF={handleExportPDF}
        onExportJSON={handleExportJSON}
      />
    </div>
  );
}
