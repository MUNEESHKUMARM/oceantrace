import { useEffect, useRef } from 'react';
import { SpillCase, Phase1Result, Phase2Result, Phase3Result, Phase4Result, Phase5Result } from '@/types';
import { getSARPreviewUrl } from '@/lib/api';

interface Props {
  spillCase: SpillCase;
  analysisComplete: boolean;
  phase1Data?: Phase1Result | null;
  phase2Data?: Phase2Result | null;
  phase3Data?: Phase3Result | null;
  isDemo?: boolean;
}


// ── Pending Card Canvas ───────────────────────────────────────────────────────
function PendingCardCanvas({ text, subtext }: { text: string; subtext?: string }) {
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#030d18',
        color: '#475569',
        fontSize: '0.58rem',
        letterSpacing: '0.08em',
        textAlign: 'center',
        padding: '8px',
      }}
    >
      <div style={{ color: '#64748b', fontWeight: 600, marginBottom: '2px' }}>{text}</div>
      {subtext && <div style={{ fontSize: '0.52rem', color: '#334155' }}>{subtext}</div>}
    </div>
  );
}

// ── SAR Image Canvas ──────────────────────────────────────────────────────────
function SARImageCanvas({ width, height, previewSrc }: { width: number; height: number; previewSrc?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;
    ctx.fillStyle = '#030d18';
    ctx.fillRect(0, 0, width, height);

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.src = previewSrc || '/sar_preview.png';

    img.onload = () => {
      ctx.drawImage(img, 0, 0, width, height);
      // Scan lines overlay
      ctx.strokeStyle = 'rgba(34, 211, 238, 0.05)';
      ctx.lineWidth = 1;
      for (let y = 0; y < height; y += 3) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }
    };

    img.onerror = () => {
      // Fallback texture
      const imageData = ctx.createImageData(width, height);
      for (let i = 0; i < imageData.data.length; i += 4) {
        const v = Math.random() * 120 + 20;
        const dark = Math.random() > 0.92 ? v * 0.05 : v;
        imageData.data[i] = dark;
        imageData.data[i + 1] = dark;
        imageData.data[i + 2] = dark;
        imageData.data[i + 3] = 255;
      }
      ctx.putImageData(imageData, 0, 0);
    };
  }, [width, height, previewSrc]);

  return <canvas ref={canvasRef} width={width} height={height} style={{ width: '100%', height: '100%', display: 'block' }} />;
}

// ── AI Detection Canvas ──────────────────────────────────────────────────────
function AIDetectionCanvas({ width, height }: { width: number; height: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;
    ctx.fillStyle = '#030d18';
    ctx.fillRect(0, 0, width, height);

    const drawOverlay = () => {
      // Dark spill area
      ctx.fillStyle = 'rgba(0,0,0,0.8)';
      ctx.beginPath();
      ctx.ellipse(width * 0.55, height * 0.45, width * 0.18, height * 0.28, 0.3, 0, Math.PI * 2);
      ctx.fill();
      // Red detection overlay
      ctx.strokeStyle = '#ef4444';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 2]);
      ctx.beginPath();
      ctx.ellipse(width * 0.55, height * 0.45, width * 0.2, height * 0.3, 0.3, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);
      // Fill with red tint
      ctx.fillStyle = 'rgba(239, 68, 68, 0.15)';
      ctx.beginPath();
      ctx.ellipse(width * 0.55, height * 0.45, width * 0.2, height * 0.3, 0.3, 0, Math.PI * 2);
      ctx.fill();
      // Detection label
      ctx.fillStyle = '#ef4444';
      ctx.font = `bold ${Math.floor(height * 0.12)}px monospace`;
      ctx.fillText('OIL SPILL', width * 0.28, height * 0.18);
      ctx.font = `${Math.floor(height * 0.09)}px monospace`;
      ctx.fillStyle = '#94a3b8';
      ctx.fillText(`${Math.round(91)}% CONF`, width * 0.38, height * 0.3);
    };

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.src = '/sar_preview.png';

    img.onload = () => {
      ctx.drawImage(img, 0, 0, width, height);
      drawOverlay();
    };

    img.onerror = () => {
      const imageData = ctx.createImageData(width, height);
      for (let i = 0; i < imageData.data.length; i += 4) {
        const v = Math.random() * 80 + 15;
        imageData.data[i] = v;
        imageData.data[i + 1] = v;
        imageData.data[i + 2] = v;
        imageData.data[i + 3] = 255;
      }
      ctx.putImageData(imageData, 0, 0);
      drawOverlay();
    };
  }, [width, height]);

  return <canvas ref={canvasRef} width={width} height={height} style={{ width: '100%', height: '100%', display: 'block' }} />;
}

// ── Wind Field Canvas ─────────────────────────────────────────────────────────
function WindFieldCanvas({ width, height, windSpeed, windDir }: { width: number; height: number; windSpeed: number; windDir: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;
    ctx.fillStyle = '#030d18';
    ctx.fillRect(0, 0, width, height);
    // Color gradient background
    const grad = ctx.createLinearGradient(0, 0, width, height);
    grad.addColorStop(0, 'rgba(6, 70, 110, 0.3)');
    grad.addColorStop(0.5, 'rgba(8, 100, 140, 0.2)');
    grad.addColorStop(1, 'rgba(4, 40, 70, 0.3)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, width, height);
    // Wind arrows
    const rad = (windDir - 90) * Math.PI / 180;
    const cols = 6, rows = 4;
    const cw = width / cols, ch = height / rows;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const x = cw * c + cw / 2;
        const y = ch * r + ch / 2;
        const len = 10 + windSpeed * 1.5;
        const jitter = (Math.random() - 0.5) * 0.2;
        const jrad = rad + jitter;
        const ex = x + Math.cos(jrad) * len;
        const ey = y + Math.sin(jrad) * len;
        const speed = windSpeed + (Math.random() - 0.5) * 2;
        const t = Math.min(1, speed / 15);
        const r_ = Math.round(100 + t * 155), g_ = Math.round(140 - t * 100), b_ = Math.round(220 - t * 170);
        ctx.strokeStyle = `rgba(${r_},${g_},${b_},0.7)`;
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(ex, ey);
        ctx.stroke();
        // Arrowhead
        ctx.fillStyle = `rgba(${r_},${g_},${b_},0.7)`;
        ctx.beginPath();
        ctx.moveTo(ex, ey);
        ctx.lineTo(ex - Math.cos(jrad - 0.5) * 5, ey - Math.sin(jrad - 0.5) * 5);
        ctx.lineTo(ex - Math.cos(jrad + 0.5) * 5, ey - Math.sin(jrad + 0.5) * 5);
        ctx.closePath();
        ctx.fill();
      }
    }
    // Speed label
    ctx.fillStyle = 'rgba(34,211,238,0.9)';
    ctx.font = `bold ${Math.floor(height * 0.15)}px monospace`;
    ctx.fillText(`${windSpeed.toFixed(1)} m/s`, 5, height - 6);
  }, [width, height, windSpeed, windDir]);
  return <canvas ref={canvasRef} width={width} height={height} style={{ width: '100%', height: '100%', display: 'block' }} />;
}

// ── Ocean Current Canvas ──────────────────────────────────────────────────────
function CurrentCanvas({ width, height, currentSpeed, currentDir }: { width: number; height: number; currentSpeed: number; currentDir: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;
    ctx.fillStyle = '#020a14';
    ctx.fillRect(0, 0, width, height);
    const grad = ctx.createRadialGradient(width / 2, height / 2, 0, width / 2, height / 2, width / 2);
    grad.addColorStop(0, 'rgba(6, 182, 212, 0.12)');
    grad.addColorStop(1, 'rgba(2, 12, 25, 0.0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, width, height);
    // Current streamlines
    const rad = (currentDir - 90) * Math.PI / 180;
    for (let i = 0; i < 20; i++) {
      const sx = Math.random() * width;
      const sy = Math.random() * height;
      ctx.beginPath();
      ctx.moveTo(sx, sy);
      let cx_ = sx, cy_ = sy;
      for (let s = 0; s < 8; s++) {
        const jitter = (Math.random() - 0.5) * 0.15;
        cx_ += Math.cos(rad + jitter) * 10;
        cy_ += Math.sin(rad + jitter) * 10;
        ctx.lineTo(cx_, cy_);
      }
      const alpha = 0.2 + Math.random() * 0.5;
      ctx.strokeStyle = `rgba(6, 182, 212, ${alpha})`;
      ctx.lineWidth = 0.8;
      ctx.stroke();
      // Endpoint dot
      ctx.fillStyle = `rgba(6, 182, 212, ${alpha * 0.8})`;
      ctx.beginPath();
      ctx.arc(cx_, cy_, 1.5, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.fillStyle = 'rgba(6,182,212,0.9)';
    ctx.font = `bold ${Math.floor(height * 0.15)}px monospace`;
    ctx.fillText(`${currentSpeed.toFixed(2)} m/s`, 5, height - 6);
  }, [width, height, currentSpeed, currentDir]);
  return <canvas ref={canvasRef} width={width} height={height} style={{ width: '100%', height: '100%', display: 'block' }} />;
}

// ── Backward Drift Canvas ─────────────────────────────────────────────────────
function DriftCanvas({ width, height, confidenceText }: { width: number; height: number; confidenceText?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;
    ctx.fillStyle = '#020a14';
    ctx.fillRect(0, 0, width, height);
    // Origin point (left side)
    const originX = width * 0.25, originY = height * 0.5;
    // Current spill (right side)
    const spillX = width * 0.78, spillY = height * 0.5;
    // Particle convergence
    for (let i = 0; i < 50; i++) {
      const startX = spillX + (Math.random() - 0.5) * width * 0.3;
      const startY = spillY + (Math.random() - 0.5) * height * 0.6;
      ctx.beginPath();
      ctx.moveTo(startX, startY);
      const cp1x = (startX + originX) / 2 + (Math.random() - 0.5) * 30;
      const cp1y = (startY + originY) / 2 + (Math.random() - 0.5) * 20;
      ctx.quadraticCurveTo(cp1x, cp1y, originX + (Math.random() - 0.5) * 15, originY + (Math.random() - 0.5) * 15);
      const alpha = 0.15 + Math.random() * 0.35;
      ctx.strokeStyle = `rgba(245, 158, 11, ${alpha})`;
      ctx.lineWidth = 0.7;
      ctx.stroke();
    }
    // Origin marker
    ctx.strokeStyle = 'rgba(245,158,11,0.7)';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([3, 2]);
    ctx.beginPath();
    ctx.arc(originX, originY, height * 0.25, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = '#f59e0b';
    ctx.beginPath();
    ctx.arc(originX, originY, 4, 0, Math.PI * 2);
    ctx.fill();
    // Spill marker
    ctx.fillStyle = '#ef4444';
    ctx.beginPath();
    ctx.arc(spillX, spillY, 5, 0, Math.PI * 2);
    ctx.fill();
    // Label
    ctx.fillStyle = 'rgba(245,158,11,0.9)';
    ctx.font = `bold ${Math.floor(height * 0.13)}px monospace`;
    ctx.fillText('ORIGIN', originX - width * 0.08, height * 0.12);
    ctx.fillStyle = 'rgba(239,68,68,0.9)';
    ctx.fillText('SPILL', spillX - width * 0.05, height * 0.12);
    ctx.fillStyle = 'rgba(245,158,11,0.9)';
    ctx.font = `${Math.floor(height * 0.11)}px monospace`;
    ctx.fillText(confidenceText || 'DEMO ORIGIN', originX - width * 0.1, height - 6);
  }, [width, height, confidenceText]);
  return <canvas ref={canvasRef} width={width} height={height} style={{ width: '100%', height: '100%', display: 'block' }} />;
}

// ── Card Wrapper ──────────────────────────────────────────────────────────────
function AnalysisCard({
  number,
  title,
  subtitle,
  children,
  badge,
}: {
  number: string;
  title: string;
  subtitle: string;
  children: React.ReactNode;
  badge?: { text: string; color: string };
}) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--maritime-850)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '5px',
        overflow: 'hidden',
        flex: 1,
        minWidth: 0,
        transition: 'border-color 0.2s ease',
      }}
      onMouseEnter={e => (e.currentTarget.style.borderColor = 'rgba(34,211,238,0.25)')}
      onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border-subtle)')}
    >
      {/* Card Header */}
      <div
        style={{
          padding: '4px 8px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          gap: '5px',
          flexShrink: 0,
        }}
      >
        <span
          style={{
            fontSize: '0.55rem',
            fontWeight: 700,
            color: '#22d3ee',
            background: 'rgba(34,211,238,0.1)',
            border: '1px solid rgba(34,211,238,0.2)',
            borderRadius: '2px',
            padding: '1px 4px',
            flexShrink: 0,
          }}
        >
          {number}
        </span>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: '0.62rem', fontWeight: 700, color: '#94a3b8', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {title}
          </div>
          <div style={{ fontSize: '0.52rem', color: '#475569' }}>{subtitle}</div>
        </div>
        {badge && (
          <div
            style={{
              marginLeft: 'auto',
              padding: '1px 5px',
              background: `${badge.color}15`,
              border: `1px solid ${badge.color}30`,
              borderRadius: '2px',
              fontSize: '0.5rem',
              fontWeight: 700,
              color: badge.color,
              letterSpacing: '0.08em',
              flexShrink: 0,
            }}
          >
            {badge.text}
          </div>
        )}
      </div>

      {/* Canvas Area */}
      <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
        {children}
      </div>
    </div>
  );
}

interface Props {
  spillCase: SpillCase;
  analysisComplete: boolean;
  phase1Data?: Phase1Result | null;
  phase2Data?: Phase2Result | null;
  phase3Data?: Phase3Result | null;
  phase4Data?: Phase4Result | null;
  phase5Data?: Phase5Result | null;
  isDemo?: boolean;
}

// ── Inside BottomAnalysisStrip ────────────────────────────────────────────────
export default function BottomAnalysisStrip({ spillCase, analysisComplete, phase1Data, phase2Data, phase3Data, phase4Data, phase5Data, isDemo = false }: Props) {

  const { environment } = spillCase;

  if (!analysisComplete) {
    return (
      <div
        style={{
          gridColumn: '1 / -1',
          display: 'flex',
          gap: '6px',
          padding: '6px 10px',
          background: 'var(--maritime-900)',
          borderTop: '1px solid var(--border-subtle)',
          height: '148px',
          flexShrink: 0,
          overflowX: 'auto',
        }}
      >
        {['01 SAR IMAGE', '02 AI DETECTION', '03 WIND FIELD', '04 OCEAN CURRENT', '05 BACKWARD DRIFT'].map((label, i) => (
          <div
            key={label}
            style={{
              flex: 1,
              minWidth: '160px',
              background: 'var(--maritime-850)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '5px',
              overflow: 'hidden',
              opacity: 0.4,
              animationDelay: `${i * 0.15}s`,
            }}
          >
            <div style={{
              padding: '4px 8px',
              borderBottom: '1px solid var(--border-subtle)',
              display: 'flex', alignItems: 'center', gap: '5px',
            }}>
              <span style={{ fontSize: '0.6rem', fontWeight: 700, color: '#334155' }}>{label.split(' ')[0]}</span>
              <span style={{ fontSize: '0.62rem', color: '#334155' }}>{label.split(' ').slice(1).join(' ')}</span>
            </div>
            <div style={{
              flex: 1, height: '108px',
              background: 'linear-gradient(90deg, var(--maritime-850) 25%, rgba(34,211,238,0.03) 50%, var(--maritime-850) 75%)',
              backgroundSize: '200% 100%',
              animation: 'shimmer 2s linear infinite',
              animationDelay: `${i * 0.2}s`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <span style={{ fontSize: '0.55rem', color: '#334155', letterSpacing: '0.08em' }}>AWAITING ANALYSIS</span>
            </div>
          </div>
        ))}
      </div>
    );
  }

  const sarPreviewSrc = phase1Data?.preview_filename
    ? getSARPreviewUrl(phase1Data.preview_filename)
    : '/sar_preview.png';

  const overlayFilename = phase2Data?.overlay_file
    ? phase2Data.overlay_file.split(/[/\\]/).pop()
    : undefined;

  const aiDetectionOverlaySrc = overlayFilename
    ? getSARPreviewUrl(overlayFilename)
    : undefined;

  const windSpeedVal = isDemo ? environment.windSpeed : (phase4Data?.wind.speed_ms ?? 0);
  const windDirVal = isDemo ? environment.windDirection : (phase4Data?.wind.direction_deg ?? 0);
  const currSpeedVal = isDemo ? environment.currentSpeed : (phase4Data?.ocean_current.speed_ms ?? 0);
  const currDirVal = isDemo ? environment.currentDirection : (phase4Data?.ocean_current.direction_deg ?? 0);

  return (
    <div
      style={{
        gridColumn: '1 / -1',
        display: 'flex',
        gap: '6px',
        padding: '6px 10px',
        background: 'var(--maritime-900)',
        borderTop: '1px solid var(--border-subtle)',
        height: '148px',
        flexShrink: 0,
        overflowX: 'auto',
      }}
    >
      {/* 01 SAR IMAGE */}
      <AnalysisCard
        number="01"
        title="SAR IMAGE"
        subtitle={isDemo ? "Sentinel-1 GRD" : (phase1Data ? `${phase1Data.raster_info.width}x${phase1Data.raster_info.height} · ${phase1Data.raster_info.crs}` : "Sentinel-1 GRD")}
        badge={isDemo ? { text: 'PROCESSED', color: '#22d3ee' } : { text: 'REAL SAR', color: '#22d3ee' }}
      >
        <SARImageCanvas width={220} height={108} previewSrc={sarPreviewSrc} />
      </AnalysisCard>

      {/* 02 AI DETECTION */}
      <AnalysisCard
        number="02"
        title="AI DETECTION"
        subtitle={isDemo ? "Oil spill boundary" : (phase2Data ? `PyTorch U-Net · ${(phase2Data.confidence * 100).toFixed(1)}% Conf` : "Phase 2 Model")}
        badge={isDemo ? { text: 'OIL SPILL', color: '#ef4444' } : (phase2Data ? (phase2Data.detected ? { text: 'OIL DETECTED', color: '#ef4444' } : { text: 'NO SPILL', color: '#10b981' }) : { text: 'NOT AVAILABLE', color: '#64748b' })}
      >
        {isDemo ? (
          <AIDetectionCanvas width={220} height={108} />
        ) : phase2Data && aiDetectionOverlaySrc ? (
          <SARImageCanvas width={220} height={108} previewSrc={aiDetectionOverlaySrc} />
        ) : (
          <PendingCardCanvas text="PHASE 2 NOT AVAILABLE" subtext="AI segmentation model pending execution" />
        )}
      </AnalysisCard>

      {/* 03 WIND FIELD */}
      <AnalysisCard
        number="03"
        title="WIND FIELD"
        subtitle={isDemo ? `${windDirVal}° at ${windSpeedVal} m/s` : (phase4Data ? `ERA5 10m · ${windDirVal.toFixed(0)}° FROM` : "Phase 4 Analysis")}
        badge={isDemo ? { text: `${windSpeedVal.toFixed(1)} m/s`, color: '#94a3b8' } : (phase4Data ? { text: `${windSpeedVal.toFixed(1)} m/s`, color: '#22d3ee' } : { text: 'NOT AVAILABLE', color: '#64748b' })}
      >
        {isDemo || phase4Data ? (
          <WindFieldCanvas width={220} height={108} windSpeed={windSpeedVal} windDir={windDirVal} />
        ) : (
          <PendingCardCanvas text="WIND DATA NOT AVAILABLE" subtext="Environmental vectors pending Phase 4" />
        )}
      </AnalysisCard>

      {/* 04 OCEAN CURRENT */}
      <AnalysisCard
        number="04"
        title="OCEAN CURRENT"
        subtitle={isDemo ? `${currDirVal}° at ${currSpeedVal} m/s` : (phase4Data ? `Copernicus PHY · ${currDirVal.toFixed(0)}° TOWARD` : "Phase 4 Analysis")}
        badge={isDemo ? { text: `${currSpeedVal.toFixed(2)} m/s`, color: '#06b6d4' } : (phase4Data ? { text: `${currSpeedVal.toFixed(2)} m/s`, color: '#06b6d4' } : { text: 'NOT AVAILABLE', color: '#64748b' })}
      >
        {isDemo || phase4Data ? (
          <CurrentCanvas width={220} height={108} currentSpeed={currSpeedVal} currentDir={currDirVal} />
        ) : (
          <PendingCardCanvas text="CURRENT DATA NOT AVAILABLE" subtext="Hydrodynamic data pending Phase 4" />
        )}
      </AnalysisCard>

      {/* 05 BACKWARD DRIFT */}
      <AnalysisCard
        number="05"
        title="BACKWARD DRIFT"
        subtitle={isDemo ? "Origin probability" : (phase5Data ? (phase5Data.origin_available ? `Origin: ${phase5Data.origin.area_km2.toFixed(1)} km²` : "Origin unavailable") : "Phase 5 Model")}
        badge={isDemo ? { text: 'DEMO MODE', color: '#f59e0b' } : (phase5Data ? (phase5Data.origin_available ? { text: `${(phase5Data.origin.confidence * 100).toFixed(1)}% CONF`, color: '#f59e0b' } : { text: 'NOT AVAILABLE', color: '#64748b' }) : { text: 'NOT AVAILABLE', color: '#64748b' })}
      >
        {isDemo ? (
          <DriftCanvas width={220} height={108} confidenceText="DEMO ORIGIN" />
        ) : phase5Data && phase5Data.origin_available ? (
          <DriftCanvas width={220} height={108} confidenceText={`${(phase5Data.origin.confidence * 100).toFixed(1)}% CONF`} />
        ) : (
          <PendingCardCanvas text="ORIGIN NOT AVAILABLE" subtext="No spill-conditioned origin generated" />
        )}
      </AnalysisCard>
    </div>
  );
}

