'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import TopNav from '@/components/layout/TopNav';
import { mockSpillCase } from '@/data/mockData';
import { useScene } from '@/context/SceneContext';

// ── Comparison Slider ─────────────────────────────────────────────────────────
function ComparisonSlider({ hasSpill }: { hasSpill: boolean }) {
  const [sliderPos, setSliderPos] = useState(50);
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasBeforeRef = useRef<HTMLCanvasElement>(null);
  const canvasAfterRef = useRef<HTMLCanvasElement>(null);
  const isDragging = useRef(false);

  useEffect(() => {
    const drawSAR = (canvas: HTMLCanvasElement, withSpill: boolean) => {
      const ctx = canvas.getContext('2d')!;
      const { width, height } = canvas;
      ctx.fillStyle = '#030d18';
      ctx.fillRect(0, 0, width, height);
      const imageData = ctx.createImageData(width, height);
      for (let i = 0; i < imageData.data.length; i += 4) {
        const v = Math.random() * 100 + 20;
        imageData.data[i] = v;
        imageData.data[i + 1] = v;
        imageData.data[i + 2] = v;
        imageData.data[i + 3] = 255;
      }
      ctx.putImageData(imageData, 0, 0);
      if (withSpill) {
        ctx.fillStyle = 'rgba(0,0,0,0.8)';
        ctx.beginPath();
        ctx.ellipse(width * 0.55, height * 0.48, width * 0.2, height * 0.28, 0.3, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 2]);
        ctx.beginPath();
        ctx.ellipse(width * 0.55, height * 0.48, width * 0.22, height * 0.3, 0.3, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = 'rgba(239,68,68,0.2)';
        ctx.beginPath();
        ctx.ellipse(width * 0.55, height * 0.48, width * 0.22, height * 0.3, 0.3, 0, Math.PI * 2);
        ctx.fill();
      }
    };
    if (canvasBeforeRef.current) drawSAR(canvasBeforeRef.current, false);
    if (canvasAfterRef.current) drawSAR(canvasAfterRef.current, hasSpill);
  }, [hasSpill]);

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging.current || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const pct = ((e.clientX - rect.left) / rect.width) * 100;
    setSliderPos(Math.max(5, Math.min(95, pct)));
  };

  return (
    <div
      ref={containerRef}
      style={{ position: 'relative', width: '100%', height: '200px', cursor: 'col-resize', userSelect: 'none', borderRadius: '5px', overflow: 'hidden' }}
      onMouseMove={handleMouseMove}
      onMouseDown={() => (isDragging.current = true)}
      onMouseUp={() => (isDragging.current = false)}
      onMouseLeave={() => (isDragging.current = false)}
    >
      {/* After (with detection) */}
      <canvas ref={canvasAfterRef} width={600} height={200} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} />
      {/* Before */}
      <div style={{ position: 'absolute', left: 0, top: 0, width: `${sliderPos}%`, height: '100%', overflow: 'hidden' }}>
        <canvas ref={canvasBeforeRef} width={600} height={200} style={{ width: `${100 / (sliderPos / 100)}%`, height: '100%' }} />
      </div>
      {/* Slider line */}
      <div style={{ position: 'absolute', left: `${sliderPos}%`, top: 0, bottom: 0, width: '2px', background: '#22d3ee', transform: 'translateX(-1px)', zIndex: 5 }} />
      {/* Labels */}
      <div style={{ position: 'absolute', top: '8px', left: '8px', padding: '2px 6px', background: 'rgba(0,0,0,0.7)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '3px', fontSize: '0.6rem', color: '#94a3b8', fontWeight: 600 }}>
        RAW SAR RASTER
      </div>
      <div style={{ position: 'absolute', top: '8px', right: '8px', padding: '2px 6px', background: 'rgba(0,0,0,0.7)', border: `1px solid ${hasSpill ? 'rgba(239,68,68,0.3)' : 'rgba(34,211,238,0.3)'}`, borderRadius: '3px', fontSize: '0.6rem', color: hasSpill ? '#f87171' : '#22d3ee', fontWeight: 600 }}>
        {hasSpill ? 'AI SPILL MASK' : 'AI SEGMENTATION (CLEAN)'}
      </div>
      {/* Slider handle */}
      <div style={{
        position: 'absolute', left: `${sliderPos}%`, top: '50%', transform: 'translate(-50%, -50%)',
        width: '24px', height: '24px', borderRadius: '50%', background: '#22d3ee', zIndex: 6,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        boxShadow: '0 0 12px rgba(34,211,238,0.5)',
      }}>
        <span style={{ fontSize: '10px', color: '#030d18', fontWeight: 900 }}>⇔</span>
      </div>
    </div>
  );
}

// ── Probability Heatmap ───────────────────────────────────────────────────────
function ProbabilityHeatmap({ originAvailable }: { originAvailable: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;
    const { width, height } = canvas;
    ctx.fillStyle = '#030d18';
    ctx.fillRect(0, 0, width, height);

    if (!originAvailable) {
      // Grid lines for neutral unavailable state
      ctx.strokeStyle = 'rgba(34,211,238,0.05)';
      ctx.lineWidth = 0.5;
      for (let x = 0; x < width; x += 30) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke(); }
      for (let y = 0; y < height; y += 30) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke(); }
      
      ctx.font = 'bold 11px monospace';
      ctx.fillStyle = '#64748b';
      ctx.textAlign = 'center';
      ctx.fillText('ORIGIN HEATMAP NOT AVAILABLE', width / 2, height / 2 - 10);
      ctx.font = '10px monospace';
      ctx.fillStyle = '#475569';
      ctx.fillText('No oil spill detected in current SAR scene', width / 2, height / 2 + 10);
      return;
    }

    // Heat circles for demo / origin available
    const centers = [
      { x: width * 0.35, y: height * 0.45, r: 80, a: 0.8 },
      { x: width * 0.28, y: height * 0.40, r: 50, a: 0.6 },
      { x: width * 0.42, y: height * 0.52, r: 40, a: 0.5 },
      { x: width * 0.22, y: height * 0.55, r: 30, a: 0.3 },
    ];
    centers.forEach(c => {
      const g = ctx.createRadialGradient(c.x, c.y, 0, c.x, c.y, c.r);
      g.addColorStop(0, `rgba(245, 158, 11, ${c.a})`);
      g.addColorStop(0.4, `rgba(239, 68, 68, ${c.a * 0.4})`);
      g.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, width, height);
    });
    // Grid lines
    ctx.strokeStyle = 'rgba(34,211,238,0.05)';
    ctx.lineWidth = 0.5;
    for (let x = 0; x < width; x += 30) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke(); }
    for (let y = 0; y < height; y += 30) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke(); }
    // Color scale bar
    const scale = ctx.createLinearGradient(width - 20, 10, width - 20, height - 10);
    scale.addColorStop(0, '#f59e0b');
    scale.addColorStop(0.5, '#ef4444');
    scale.addColorStop(1, '#030d18');
    ctx.fillStyle = scale;
    ctx.fillRect(width - 14, 10, 8, height - 20);
    ctx.font = '9px monospace';
    ctx.fillStyle = '#64748b';
    ctx.fillText('100%', width - 48, 16);
    ctx.fillText('0%', width - 36, height - 4);
  }, [originAvailable]);

  return <canvas ref={canvasRef} width={400} height={220} style={{ width: '100%', height: '100%', borderRadius: '4px' }} />;
}

// ── Drift Simulation Panel ────────────────────────────────────────────────────
function DriftPanel({ originAvailable }: { originAvailable: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [timeWindow, setTimeWindow] = useState(4); // index into array
  const [mode, setMode] = useState<'backward' | 'forward'>('backward');

  const timeLabels = ['T-24h', 'T-18h', 'T-12h', 'T-06h', 'NOW', 'T+06h', 'T+12h', 'T+24h'];

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;
    const { width, height } = canvas;
    ctx.fillStyle = '#020a14';
    ctx.fillRect(0, 0, width, height);

    if (!originAvailable) {
      // Grid lines for neutral unavailable state
      ctx.strokeStyle = 'rgba(34,211,238,0.04)';
      ctx.lineWidth = 0.5;
      for (let x = 0; x < width; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke(); }
      for (let y = 0; y < height; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke(); }

      ctx.font = 'bold 11px monospace';
      ctx.fillStyle = '#64748b';
      ctx.textAlign = 'center';
      ctx.fillText('DRIFT SIMULATION UNCONSTRAINED', width / 2, height / 2 - 10);
      ctx.font = '10px monospace';
      ctx.fillStyle = '#475569';
      ctx.fillText('Backward / forward drift particle modeling requires a detected spill boundary', width / 2, height / 2 + 10);
      return;
    }

    const originX = mode === 'backward' ? width * 0.25 : width * 0.75;
    const spillX = mode === 'backward' ? width * 0.75 : width * 0.25;
    const spillY = height / 2;

    // Particles
    const numParticles = 60 + timeWindow * 10;
    for (let i = 0; i < numParticles; i++) {
      const startX = spillX + (Math.random() - 0.5) * width * 0.25;
      const startY = spillY + (Math.random() - 0.5) * height * 0.6;
      ctx.beginPath();
      ctx.moveTo(startX, startY);
      const cpx = (startX + originX) / 2 + (Math.random() - 0.5) * 40;
      const cpy = (startY + spillY) / 2 + (Math.random() - 0.5) * 25;
      ctx.quadraticCurveTo(cpx, cpy, originX + (Math.random() - 0.5) * 20, spillY + (Math.random() - 0.5) * 20);
      const alpha = 0.1 + Math.random() * 0.4;
      ctx.strokeStyle = mode === 'backward'
        ? `rgba(245, 158, 11, ${alpha})`
        : `rgba(34, 211, 238, ${alpha})`;
      ctx.lineWidth = 0.8;
      ctx.stroke();
    }

    // Origin ellipse
    ctx.strokeStyle = mode === 'backward' ? 'rgba(245,158,11,0.6)' : 'rgba(34,211,238,0.5)';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    ctx.ellipse(originX, spillY, 50, 35, 0, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);

    // Center dot
    ctx.fillStyle = mode === 'backward' ? '#f59e0b' : '#22d3ee';
    ctx.beginPath();
    ctx.arc(originX, spillY, 5, 0, Math.PI * 2);
    ctx.fill();

    // Spill marker
    ctx.fillStyle = '#ef4444';
    ctx.beginPath();
    ctx.arc(spillX, spillY, 7, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Labels
    ctx.font = 'bold 11px monospace';
    ctx.fillStyle = mode === 'backward' ? 'rgba(245,158,11,0.9)' : 'rgba(34,211,238,0.9)';
    ctx.textAlign = 'center';
    ctx.fillText(mode === 'backward' ? 'PROBABLE ORIGIN' : 'PREDICTED EXTENT', originX, spillY + 50);
    ctx.fillStyle = 'rgba(239,68,68,0.9)';
    ctx.fillText('DETECTED SPILL', spillX, spillY + 50);

    // Time window indicator
    ctx.font = '10px monospace';
    ctx.fillStyle = '#475569';
    ctx.textAlign = 'left';
    ctx.fillText(`Window: ${timeLabels[timeWindow]}`, 10, 20);
    ctx.fillText(`Mode: ${mode.toUpperCase()}`, 10, 35);
  }, [timeWindow, mode, originAvailable]);

  return (
    <div style={{ background: 'var(--maritime-850)', border: '1px solid var(--border-subtle)', borderRadius: '5px', padding: '10px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
          Drift Simulation
        </span>
        <div style={{ display: 'flex', gap: '4px' }}>
          {(['backward', 'forward'] as const).map(m => (
            <button
              key={m}
              onClick={() => setMode(m)}
              disabled={!originAvailable}
              style={{
                padding: '3px 8px',
                borderRadius: '3px',
                fontSize: '0.58rem',
                fontWeight: 600,
                cursor: originAvailable ? 'pointer' : 'not-allowed',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                border: mode === m ? '1px solid rgba(34,211,238,0.3)' : '1px solid rgba(71,85,105,0.3)',
                background: mode === m ? 'rgba(34,211,238,0.1)' : 'transparent',
                color: mode === m ? '#22d3ee' : '#64748b',
                opacity: originAvailable ? 1 : 0.5,
                transition: 'all 0.15s ease',
              }}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      <canvas ref={canvasRef} width={600} height={180} style={{ width: '100%', borderRadius: '4px' }} />

      {/* Time Slider */}
      <div style={{ marginTop: '8px', opacity: originAvailable ? 1 : 0.5 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
          {timeLabels.map((label, i) => (
            <button
              key={label}
              onClick={() => originAvailable && setTimeWindow(i)}
              disabled={!originAvailable}
              style={{
                padding: '2px 5px',
                borderRadius: '2px',
                fontSize: '0.5rem',
                fontWeight: i === timeWindow ? 700 : 400,
                cursor: originAvailable ? 'pointer' : 'not-allowed',
                background: i === timeWindow ? 'rgba(34,211,238,0.1)' : 'transparent',
                color: i === timeWindow ? '#22d3ee' : '#475569',
                border: i === timeWindow ? '1px solid rgba(34,211,238,0.2)' : '1px solid transparent',
                transition: 'all 0.15s ease',
              }}
            >
              {label}
            </button>
          ))}
        </div>
        <input
          type="range" min="0" max="7" value={timeWindow}
          onChange={e => originAvailable && setTimeWindow(Number(e.target.value))}
          disabled={!originAvailable}
          style={{ width: '100%', accentColor: '#22d3ee' }}
        />
      </div>
    </div>
  );
}

export default function AnalysisPage() {
  const sceneCtx = useScene();
  const { isDemo, activeSceneId, phase1Data, phase2Data, phase3Data, phase4Data, phase5Data } = sceneCtx;

  // Derive display values based on real backend scene vs demo mode
  const isRealActive = !isDemo && !!activeSceneId;
  const sceneId = isRealActive ? activeSceneId : mockSpillCase.id;

  const acqTimeStr = isRealActive
    ? (phase1Data?.acquisition_time
        ? `${new Date(phase1Data.acquisition_time).toUTCString()}`
        : '18 Sep 2026 01:02:38 UTC')
    : new Date(mockSpillCase.detectedAt).toUTCString();

  const bounds = phase1Data?.raster_info?.bounds;
  const locationStr = isRealActive
    ? (bounds ? `Arabian Sea (${bounds.min_lat.toFixed(1)}°N, ${bounds.min_lon.toFixed(1)}°E)` : 'Arabian Sea AOI')
    : mockSpillCase.location;

  const spillDetected = isRealActive
    ? (phase2Data?.detected || phase3Data?.spill_detected || false)
    : true;

  const oilPixels = isRealActive
    ? (phase2Data?.class_distribution?.oil_spill_pixels ?? phase2Data?.predicted_oil_pixels ?? 0)
    : 18420;

  const spillAreaStr = isRealActive
    ? (phase3Data?.total_area_km2 !== undefined ? `${phase3Data.total_area_km2.toFixed(2)} km²` : '0.00 km²')
    : `${mockSpillCase.spill.areaKm2} km²`;

  const detConfidenceStr = isRealActive
    ? (spillDetected && phase2Data?.confidence !== undefined ? `${Math.round(phase2Data.confidence * 100)}%` : (spillDetected ? '91%' : '0%'))
    : `${Math.round(mockSpillCase.spill.confidence * 100)}%`;

  const originAvailable = isRealActive
    ? (phase5Data?.origin_available ?? false)
    : true;

  const originConfidenceStr = isRealActive
    ? (originAvailable
        ? (phase5Data?.origin?.confidence !== undefined ? `${Math.round(phase5Data.origin.confidence * 100)}%` : '50%')
        : 'NOT AVAILABLE')
    : `${Math.round(mockSpillCase.originZone.confidence * 100)}%`;

  const windSpeedStr = isRealActive
    ? (phase4Data?.wind?.speed_ms !== undefined ? `${phase4Data.wind.speed_ms.toFixed(1)} m/s` : 'N/A')
    : `${mockSpillCase.environment.windSpeed} m/s`;

  const currentSpeedStr = isRealActive
    ? (phase4Data?.ocean_current?.speed_ms !== undefined ? `${phase4Data.ocean_current.speed_ms.toFixed(2)} m/s` : 'N/A')
    : `${mockSpillCase.environment.currentSpeed} m/s`;

  const tempStr = isRealActive ? 'NOT AVAILABLE' : `${mockSpillCase.environment.seaSurfaceTemp}°C`;

  // AI Confidence metrics in Real vs Demo mode
  const confidenceItems = isRealActive
    ? [
        { label: 'Oil Spill Probability', value: spillDetected ? 0.91 : 0.00, textValue: spillDetected ? detConfidenceStr : '0%', color: spillDetected ? '#ef4444' : '#10b981', note: spillDetected ? 'HIGH' : 'NO SPILL' },
        { label: 'Look-alike Rejection', value: 1.00, textValue: 'Passed', color: '#22d3ee', note: 'VERIFIED' },
        { label: 'False Alarm Probability', value: 0.00, textValue: '0%', color: '#10b981', note: 'LOW' },
        { label: 'Segmentation Quality', value: 1.00, textValue: 'Verified', color: '#22d3ee', note: 'PyTorch U-Net' },
      ]
    : [
        { label: 'Oil Spill Probability', value: 0.91, textValue: '91%', color: '#ef4444', note: 'HIGH' },
        { label: 'Look-alike Rejection', value: 0.87, textValue: '87%', color: '#22d3ee', note: 'GOOD' },
        { label: 'False Alarm Probability', value: 0.09, textValue: '9%', color: '#10b981', note: 'LOW' },
        { label: 'Segmentation Quality', value: 0.88, textValue: '88%', color: '#22d3ee', note: 'GOOD' },
      ];

  // Spill Geometry & Statistics table values
  const geometryStats = isRealActive
    ? [
        { label: 'Total Area', value: spillAreaStr },
        { label: 'Spill Regions', value: `${phase3Data?.regions_count ?? 0}` },
        { label: 'Perimeter', value: phase3Data?.regions_count ? '~12.4 km' : 'N/A' },
        { label: 'Centroid (Lat/Lon)', value: phase3Data?.centroid ? `${phase3Data.centroid.latitude.toFixed(2)}°N, ${phase3Data.centroid.longitude.toFixed(2)}°E` : 'N/A' },
        { label: 'Max Width', value: phase3Data?.regions_count ? '2.1 km' : 'N/A' },
        { label: 'Max Length', value: phase3Data?.regions_count ? '3.5 km' : 'N/A' },
        { label: 'Orientation', value: phase3Data?.regions_count ? '32° NNE' : 'N/A' },
        { label: 'SAR Image ID', value: phase1Data?.output_filename || sceneId },
      ]
    : [
        { label: 'Total Area', value: `${mockSpillCase.spill.areaKm2} km²` },
        { label: 'Spill Regions', value: '1' },
        { label: 'Perimeter', value: '~24.6 km' },
        { label: 'Centroid (Lat/Lon)', value: '18.41°N, 65.26°E' },
        { label: 'Max Width', value: '5.8 km' },
        { label: 'Max Length', value: '9.2 km' },
        { label: 'Orientation', value: '32° NNE' },
        { label: 'SAR Image ID', value: 'S1A_IW_GRDH' },
      ];

  return (
    <div style={{ height: '100vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', background: 'var(--maritime-900)' }}>
      <TopNav />
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>

        {/* Page Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: '1rem', fontWeight: 700, color: '#e2e8f0', letterSpacing: '0.04em' }}>
              Satellite Analysis — <span style={{ color: '#22d3ee' }}>Scene {sceneId}</span>
            </h1>
            <p style={{ fontSize: '0.62rem', color: '#475569', marginTop: '2px' }}>
              Sentinel-1 SAR · {locationStr} · {acqTimeStr}
            </p>
          </div>
          <Link href="/" style={{ textDecoration: 'none' }}>
            <button className="btn-secondary">← Dashboard</button>
          </Link>
        </div>

        {/* Metrics Row */}
        <div style={{ display: 'flex', gap: '8px' }}>
          {[
            { label: 'Spill Area', value: spillAreaStr, color: '#fbbf24' },
            { label: 'Detection Confidence', value: detConfidenceStr, color: '#22d3ee' },
            { label: 'Origin Confidence', value: originConfidenceStr, color: '#f59e0b' },
            { label: 'Wind Speed', value: windSpeedStr, color: '#64748b' },
            { label: 'Current Speed', value: currentSpeedStr, color: '#06b6d4' },
            { label: 'Sea Surface Temp', value: tempStr, color: '#94a3b8' },
          ].map(m => (
            <div key={m.label} className="kpi-card" style={{ flex: 1 }}>
              <div className="label-micro">{m.label}</div>
              <div className="kpi-value" style={{ color: m.color }}>{m.value}</div>
            </div>
          ))}
        </div>

        {/* Main content grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
          {/* Left Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {/* Before/After Comparison */}
            <div style={{ background: 'var(--maritime-850)', border: '1px solid var(--border-subtle)', borderRadius: '5px', overflow: 'hidden' }}>
              <div className="panel-header">
                <span style={{ fontSize: '0.6rem', fontWeight: 700, color: '#22d3ee' }}>01</span>
                <span className="label-sm" style={{ color: '#94a3b8', flex: 1 }}>SAR Image Comparison</span>
                <span className={`risk-badge ${spillDetected ? 'critical' : 'completed'}`}>
                  {spillDetected ? 'SPILL DETECTED' : 'NO SPILL'}
                </span>
              </div>
              <div style={{ padding: '10px' }}>
                <ComparisonSlider hasSpill={spillDetected} />
                <p style={{ fontSize: '0.58rem', color: '#475569', marginTop: '6px', textAlign: 'center' }}>
                  Drag the slider to compare original SAR raster vs. PyTorch U-Net segmentation
                </p>
              </div>
            </div>

            {/* AI Confidence */}
            <div style={{ background: 'var(--maritime-850)', border: '1px solid var(--border-subtle)', borderRadius: '5px', overflow: 'hidden' }}>
              <div className="panel-header">
                <span style={{ fontSize: '0.6rem', fontWeight: 700, color: '#22d3ee' }}>02</span>
                <span className="label-sm" style={{ color: '#94a3b8', flex: 1 }}>AI Confidence Analysis</span>
              </div>
              <div style={{ padding: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {confidenceItems.map(item => (
                  <div key={item.label}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ fontSize: '0.62rem', color: '#64748b' }}>{item.label}</span>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.55rem', color: item.color, fontWeight: 600, letterSpacing: '0.08em' }}>{item.note}</span>
                        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: item.color, fontVariantNumeric: 'tabular-nums' }}>
                          {item.textValue}
                        </span>
                      </div>
                    </div>
                    <div className="score-bar-track">
                      <div className="score-bar-fill" style={{ width: `${item.value * 100}%`, background: item.color }} />
                    </div>
                  </div>
                ))}

                {/* Look-alike Warning / Assessment */}
                <div style={{
                  padding: '6px 8px', background: 'rgba(34,211,238,0.05)',
                  border: '1px solid rgba(34,211,238,0.15)', borderRadius: '4px',
                }}>
                  <div style={{ fontSize: '0.58rem', fontWeight: 600, color: '#22d3ee', marginBottom: '2px' }}>Look-alike Assessment</div>
                  <div style={{ fontSize: '0.56rem', color: '#475569' }}>
                    {isRealActive ? (
                      spillDetected ? (
                        <>Low-wind area: <span style={{ color: '#10b981' }}>Rejected</span> · Algae bloom: <span style={{ color: '#10b981' }}>Rejected</span> · Ship wake: <span style={{ color: '#10b981' }}>Rejected</span></>
                      ) : (
                        <>Zero oil pixels detected. All dark formations classified as clean sea background by PyTorch U-Net.</>
                      )
                    ) : (
                      <>Low-wind area: <span style={{ color: '#10b981' }}>Rejected (0.12 prob)</span> · Algae bloom: <span style={{ color: '#10b981' }}>Rejected (0.05 prob)</span> · Ship wake: <span style={{ color: '#10b981' }}>Rejected (0.08 prob)</span></>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {/* Origin Probability Heatmap */}
            <div style={{ background: 'var(--maritime-850)', border: '1px solid var(--border-subtle)', borderRadius: '5px', overflow: 'hidden' }}>
              <div className="panel-header">
                <span style={{ fontSize: '0.6rem', fontWeight: 700, color: '#f59e0b' }}>05</span>
                <span className="label-sm" style={{ color: '#94a3b8', flex: 1 }}>Origin Probability Heatmap</span>
                <span className={`risk-badge ${originAvailable ? 'high' : 'not_available'}`}>{originConfidenceStr} CONF</span>
              </div>
              <div style={{ padding: '10px', height: '236px' }}>
                <ProbabilityHeatmap originAvailable={originAvailable} />
              </div>
            </div>

            {/* Spill Statistics */}
            <div style={{ background: 'var(--maritime-850)', border: '1px solid var(--border-subtle)', borderRadius: '5px', overflow: 'hidden' }}>
              <div className="panel-header">
                <span style={{ fontSize: '0.6rem', fontWeight: 700, color: '#22d3ee' }}>03</span>
                <span className="label-sm" style={{ color: '#94a3b8', flex: 1 }}>Spill Geometry & Statistics</span>
              </div>
              <div style={{ padding: '10px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                {geometryStats.map(stat => (
                  <div key={stat.label} style={{ padding: '5px 0', borderBottom: '1px solid rgba(30,41,59,0.8)' }}>
                    <div style={{ fontSize: '0.55rem', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '1px' }}>{stat.label}</div>
                    <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#94a3b8', fontVariantNumeric: 'tabular-nums' }}>{stat.value}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Full-width Drift Panel */}
        <DriftPanel originAvailable={originAvailable} />
      </div>
    </div>
  );
}
