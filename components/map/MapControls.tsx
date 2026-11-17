'use client';

import { MapLayer } from '@/types';

interface Props {
  activeLayers: Record<MapLayer, boolean>;
  onToggle: (layer: MapLayer) => void;
}

const LAYERS: { key: MapLayer; label: string; color: string }[] = [
  { key: 'oilSpill', label: 'Oil Spill', color: '#ef4444' },
  { key: 'vesselTracks', label: 'Vessel Tracks', color: '#22d3ee' },
  { key: 'wind', label: 'Wind', color: '#64748b' },
  { key: 'oceanCurrent', label: 'Ocean Current', color: '#06b6d4' },
  { key: 'driftSimulation', label: 'Drift Simulation', color: '#f59e0b' },
  { key: 'coastalRisk', label: 'Coastal Risk', color: '#f97316' },
  { key: 'ports', label: 'Ports', color: '#94a3b8' },
  { key: 'fishingZones', label: 'Fishing Zones', color: '#22c55e' },
];

export default function MapControls({ activeLayers, onToggle }: Props) {
  return (
    <div
      style={{
        position: 'absolute',
        top: '10px',
        right: '10px',
        background: 'rgba(6, 17, 31, 0.88)',
        border: '1px solid rgba(34, 211, 238, 0.15)',
        borderRadius: '5px',
        padding: '8px 10px',
        zIndex: 20,
        backdropFilter: 'blur(8px)',
        minWidth: '152px',
      }}
    >
      <div style={{ fontSize: '0.55rem', color: '#475569', letterSpacing: '0.12em', textTransform: 'uppercase', fontWeight: 700, marginBottom: '6px' }}>
        Map Layers
      </div>
      {LAYERS.map(layer => (
        <label
          key={layer.key}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            cursor: 'pointer',
            marginBottom: '4px',
            padding: '2px 0',
          }}
        >
          {/* Custom checkbox */}
          <div
            onClick={() => onToggle(layer.key)}
            style={{
              width: '12px', height: '12px',
              border: `1.5px solid ${activeLayers[layer.key] ? layer.color : '#334155'}`,
              borderRadius: '2px',
              background: activeLayers[layer.key] ? `${layer.color}30` : 'transparent',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
              transition: 'all 0.15s ease',
              cursor: 'pointer',
            }}
          >
            {activeLayers[layer.key] && (
              <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
                <path d="M1 4 L3 6 L7 2" stroke={layer.color} strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            )}
          </div>
          <span
            style={{
              fontSize: '0.58rem',
              color: activeLayers[layer.key] ? '#94a3b8' : '#475569',
              transition: 'color 0.15s ease',
              userSelect: 'none',
            }}
            onClick={() => onToggle(layer.key)}
          >
            {layer.label}
          </span>
          {/* Color dot */}
          <div
            style={{
              width: '5px', height: '5px', borderRadius: '50%',
              background: layer.color,
              marginLeft: 'auto',
              opacity: activeLayers[layer.key] ? 1 : 0.2,
              transition: 'opacity 0.15s ease',
            }}
          />
        </label>
      ))}
    </div>
  );
}
