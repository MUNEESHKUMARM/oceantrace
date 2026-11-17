'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { SpillCase, Vessel, MapLayer, Phase1Result, Phase3Result, Phase4Result, Phase5Result } from '@/types';

interface Props {
  spillCase: SpillCase;
  selectedVessel: Vessel | null;
  onSelectVessel: (v: Vessel) => void;
  activeLayers: Record<MapLayer, boolean>;
  analysisComplete: boolean;
  phase1Data?: Phase1Result | null;
  phase3Data?: Phase3Result | null;
  phase4Data?: Phase4Result | null;
  phase5Data?: Phase5Result | null;
  isDemo?: boolean;
}

// ─── SVG Arrow Helper ──────────────────────────────────────────────────────────
function WindArrow({ x, y, angle, speed, type }: { x: number; y: number; angle: number; speed: number; type: 'wind' | 'current' }) {
  const len = type === 'wind' ? 14 + speed * 1.2 : 12 + speed * 8;
  const color = type === 'wind' ? '#64748b' : '#06b6d4';
  const opacity = type === 'wind' ? 0.55 : 0.65;
  const rad = (angle - 90) * Math.PI / 180;
  const ex = x + Math.cos(rad) * len;
  const ey = y + Math.sin(rad) * len;

  return (
    <g opacity={opacity}>
      <line x1={x} y1={y} x2={ex} y2={ey} stroke={color} strokeWidth={type === 'wind' ? 1 : 1.2} />
      <polygon
        points={`${ex},${ey} ${ex - Math.cos(rad - 0.5) * 5},${ey - Math.sin(rad - 0.5) * 5} ${ex - Math.cos(rad + 0.5) * 5},${ey - Math.sin(rad + 0.5) * 5}`}
        fill={color}
      />
    </g>
  );
}

// ─── Calculate Dynamic Case Bounds Helper ────────────────────────────────────
function calculateCaseBounds(spillCase: SpillCase): [[number, number], [number, number]] {
  let minLat = 90, maxLat = -90, minLng = 180, maxLng = -180;
  const add = (lat: number, lng: number) => {
    if (typeof lat === 'number' && typeof lng === 'number' && !isNaN(lat) && !isNaN(lng)) {
      if (lat < minLat) minLat = lat;
      if (lat > maxLat) maxLat = lat;
      if (lng < minLng) minLng = lng;
      if (lng > maxLng) maxLng = lng;
    }
  };

  if (spillCase.spill?.coordinates) {
    spillCase.spill.coordinates.forEach(p => add(p.lat, p.lng));
  }
  if (spillCase.originZone?.polygon) {
    spillCase.originZone.polygon.forEach(p => add(p.lat, p.lng));
  }
  if (spillCase.originZone?.center) {
    add(spillCase.originZone.center.lat, spillCase.originZone.center.lng);
  }
  if (spillCase.vessels) {
    spillCase.vessels.forEach(v => {
      if (v.lastKnownPosition) add(v.lastKnownPosition.lat, v.lastKnownPosition.lng);
      if (v.track) v.track.forEach(tp => add(tp.lat, tp.lng));
    });
  }

  if (minLat >= maxLat || minLng >= maxLng) {
    return [[17.5, 71.5], [19.0, 72.5]];
  }
  return [[minLat, minLng], [maxLat, maxLng]];
}

export default function OceanMap({ spillCase, selectedVessel, onSelectVessel, activeLayers, analysisComplete, phase1Data, phase3Data, phase4Data, phase5Data, isDemo = false }: Props) {
  const mapRef = useRef<any>(null);
  const leafletRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; content: string } | null>(null);
  const [svgSize, setSvgSize] = useState({ w: 800, h: 500 });
  const [mapProjection, setMapProjection] = useState<((latlng: { lat: number; lng: number }) => { x: number; y: number }) | null>(null);
  const [isMapReady, setIsMapReady] = useState(false);
  const [animFrame, setAnimFrame] = useState(0);
  const [mouseCoords, setMouseCoords] = useState<{ lat: number; lng: number } | null>(null);

  // ── Animate particles ──────────────────────────────────────────────────────
  useEffect(() => {
    if (!analysisComplete) return;
    let af: number;
    let frame = 0;
    const tick = () => {
      frame = (frame + 1) % 120;
      if (frame % 2 === 0) {
        setAnimFrame(frame);
      }
      af = requestAnimationFrame(tick);
    };
    af = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(af);
  }, [analysisComplete]);

  // ── Initialize Leaflet ─────────────────────────────────────────────────────
  useEffect(() => {
    if (typeof window === 'undefined' || !containerRef.current) return;

    const initLeaflet = async () => {
      const L = (await import('leaflet')).default;
      leafletRef.current = L;

      if (mapRef.current) return;

      const map = L.map(containerRef.current!, {
        zoomControl: false,
        attributionControl: false,
        minZoom: 4,
        maxZoom: 19,
        worldCopyJump: true,
      });

      // Enforce vertical-only latitude pan boundaries (top: 85.0511°N, bottom: -85.0511°S) without restricting longitude
      const MIN_LAT = -85.0511;
      const MAX_LAT = 85.0511;
      const enforceLatitudeBounds = () => {
        const center = map.getCenter();
        if (center.lat < MIN_LAT || center.lat > MAX_LAT) {
          const clampedLat = Math.max(MIN_LAT, Math.min(MAX_LAT, center.lat));
          map.setView([clampedLat, center.lng], map.getZoom(), { animate: false });
        }
      };
      map.on('drag move zoom zoomend', enforceLatitudeBounds);

      // Track mouse position for LAT/LON readout
      map.on('mousemove', (e: any) => {
        if (e?.latlng) {
          setMouseCoords({ lat: e.latlng.lat, lng: e.latlng.lng });
        }
      });
      map.on('move', () => {
        const center = map.getCenter();
        setMouseCoords(prev => prev || { lat: center.lat, lng: center.lng });
      });

      // Dynamically fit map bounds to the current investigation case data or Phase 1 bounds
      let boundsToFit: [[number, number], [number, number]] = [[17.5, 71.5], [19.0, 72.5]];
      if (phase1Data?.raster_info?.bounds) {
        const b = phase1Data.raster_info.bounds;
        boundsToFit = [[b.min_lat, b.min_lon], [b.max_lat, b.max_lon]];
      } else {
        boundsToFit = calculateCaseBounds(spillCase);
      }
      map.fitBounds(boundsToFit, { padding: [50, 50], maxZoom: 10 });

      // Modern High-Resolution Satellite Imagery Basemap
      L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        {
          maxZoom: 19,
          attribution: '&copy; Esri, Maxar, Earthstar Geographics',
        }
      ).addTo(map);

      // High-Contrast Maritime Reference Labels & Borders Overlay
      L.tileLayer(
        'https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png',
        { subdomains: 'abcd', maxZoom: 19, opacity: 0.9 }
      ).addTo(map);

      L.control.zoom({ position: 'bottomright' }).addTo(map);
      L.control.scale({ position: 'bottomleft', imperial: false }).addTo(map);

      mapRef.current = map;

      // Update SVG overlay size on map change
      const updateSize = () => {
        if (containerRef.current) {
          const rect = containerRef.current.getBoundingClientRect();
          setSvgSize({ w: rect.width, h: rect.height });
        }
        setMapProjection(() => (latlng: { lat: number; lng: number }) => {
          const point = map.latLngToContainerPoint([latlng.lat, latlng.lng]);
          return { x: point.x, y: point.y };
        });
      };

      map.on('load move zoom moveend zoomend', updateSize);
      setTimeout(() => {
        updateSize();
        setIsMapReady(true);
      }, 300);
    };

    initLeaflet();

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // ── Re-project on map move/zoom ────────────────────────────────────────────
  useEffect(() => {
    if (!mapRef.current) return;
    const map = mapRef.current;
    const handler = () => {
      setMapProjection(() => (latlng: { lat: number; lng: number }) => {
        const point = map.latLngToContainerPoint([latlng.lat, latlng.lng]);
        return { x: point.x, y: point.y };
      });
    };
    map.on('move zoom moveend zoomend viewreset', handler);
    return () => map.off('move zoom moveend zoomend viewreset', handler);
  }, [isMapReady]);

  // ── Resize observer ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(entries => {
      const e = entries[0];
      setSvgSize({ w: e.contentRect.width, h: e.contentRect.height });
      mapRef.current?.invalidateSize();
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  // ── Project helper ─────────────────────────────────────────────────────────
  const project = useCallback(
    (latlng: { lat: number; lng: number }) => {
      if (!mapRef.current) return { x: 0, y: 0 };
      try {
        const p = mapRef.current.latLngToContainerPoint([latlng.lat, latlng.lng]);
        return { x: p.x, y: p.y };
      } catch {
        return { x: 0, y: 0 };
      }
    },
    [mapProjection]
  );

  const toPath = (points: { lat: number; lng: number }[]) =>
    points.map((p, i) => {
      const { x, y } = project(p);
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ') + ' Z';

  const toPolyline = (points: { lat: number; lng: number }[]) =>
    points.map((p, i) => {
      const { x, y } = project(p);
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ');

  const { spill, originZone, vessels, environment, driftParticles } = spillCase;

  // Real SAR Scene Bounds Polygon (if available)
  const sarBoundsPolygon = phase1Data?.raster_info?.bounds
    ? [
        { lat: phase1Data.raster_info.bounds.max_lat, lng: phase1Data.raster_info.bounds.min_lon },
        { lat: phase1Data.raster_info.bounds.max_lat, lng: phase1Data.raster_info.bounds.max_lon },
        { lat: phase1Data.raster_info.bounds.min_lat, lng: phase1Data.raster_info.bounds.max_lon },
        { lat: phase1Data.raster_info.bounds.min_lat, lng: phase1Data.raster_info.bounds.min_lon },
      ]
    : null;

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden', background: '#030d18' }}>
      {/* Leaflet map container */}
      <div ref={containerRef} style={{ position: 'absolute', inset: 0, zIndex: 0 }} />

      {/* SVG Overlay */}
      {isMapReady && (
        <svg
          style={{
            position: 'absolute', inset: 0, pointerEvents: 'none',
            zIndex: 10, width: '100%', height: '100%',
          }}
          viewBox={`0 0 ${svgSize.w} ${svgSize.h}`}
          preserveAspectRatio="none"
        >
          <defs>
            <filter id="spill-glow">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
            <filter id="origin-glow">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>

          {/* ── REAL MODE: REAL SENTINEL-1 SAR Bounding Footprint Overlay ── */}
          {!isDemo && sarBoundsPolygon && (
            <g>
              <path
                d={toPath(sarBoundsPolygon)}
                fill="rgba(34, 211, 238, 0.08)"
                stroke="#22d3ee"
                strokeWidth="1.8"
                strokeDasharray="6 4"
              />
              {(() => {
                const c = project(sarBoundsPolygon[0]);
                return (
                  <g transform={`translate(${c.x + 8}, ${c.y + 12})`}>
                    <rect x="0" y="0" width="165" height="22" rx="3" fill="rgba(6, 17, 31, 0.85)" stroke="rgba(34, 211, 238, 0.4)" strokeWidth="1" />
                    <text x="8" y="14" fill="#22d3ee" fontSize="8" fontWeight="700" fontFamily="monospace">
                      SENTINEL-1 SAR SCENE BOUNDARY
                    </text>
                  </g>
                );
              })()}
            </g>
          )}

          {/* ── REAL MODE: REAL PHASE 3 SPILL POLYGONS OVERLAY ── */}
          {!isDemo && phase3Data && phase3Data.spill_detected && phase3Data.spill_regions.map((region) => {
            const c = project({ lat: region.centroid.latitude, lng: region.centroid.longitude });
            const bboxPolygon = [
              { lat: region.bbox.max_lat, lng: region.bbox.min_lon },
              { lat: region.bbox.max_lat, lng: region.bbox.max_lon },
              { lat: region.bbox.min_lat, lng: region.bbox.max_lon },
              { lat: region.bbox.min_lat, lng: region.bbox.min_lon },
            ];

            return (
              <g key={`real-spill-region-${region.region_id}`} filter="url(#spill-glow)">
                <path
                  d={toPath(bboxPolygon)}
                  fill="rgba(239, 68, 68, 0.2)"
                  stroke="#ef4444"
                  strokeWidth="2"
                  style={{ animation: 'pulse-spill 2.5s ease-in-out infinite' }}
                />
                <circle cx={c.x} cy={c.y} r="5" fill="#ef4444" />
                <text x={c.x + 8} y={c.y + 4} fill="#ef4444" fontSize="9" fontWeight="700" fontFamily="monospace">
                  SPILL REGION #{region.region_id} ({region.area_km2} km²)
                </text>
              </g>
            );
          })}

          {/* ── REAL MODE: REAL PHASE 5 BACKWARD DRIFT TRAJECTORIES ── */}
          {!isDemo && activeLayers.driftSimulation && phase5Data?.backward_drift?.points_sample && (
            <g>
              {(() => {
                const grouped: Record<number, Array<{ lat: number; lng: number }>> = {};
                phase5Data.backward_drift.points_sample.forEach((pt: any) => {
                  if (!grouped[pt.particle_id]) grouped[pt.particle_id] = [];
                  grouped[pt.particle_id].push({ lat: pt.latitude, lng: pt.longitude });
                });
                return Object.entries(grouped).map(([pid, pts]) => {
                  if (pts.length < 2) return null;
                  return (
                    <path
                      key={`real-drift-${pid}`}
                      d={toPolyline(pts)}
                      fill="none"
                      stroke="#f59e0b"
                      strokeWidth="1.2"
                      opacity="0.65"
                      strokeDasharray="4 3"
                    />
                  );
                });
              })()}
            </g>
          )}

          {/* ── REAL MODE: REAL PHASE 5 PROBABLE ORIGIN ZONE ── */}
          {!isDemo && activeLayers.driftSimulation && phase5Data?.origin?.centroid && (
            <g filter="url(#origin-glow)">
              {(() => {
                const c = project({ lat: phase5Data.origin.centroid.latitude, lng: phase5Data.origin.centroid.longitude });
                let geomCoords: Array<{ lat: number; lng: number }> = [];
                try {
                  const featGeom = phase5Data.origin.geojson_feature?.geometry;
                  if (featGeom?.type === 'Polygon' && featGeom.coordinates?.[0]) {
                    geomCoords = featGeom.coordinates[0].map((coord: number[]) => ({ lat: coord[1], lng: coord[0] }));
                  }
                } catch (e) {
                  // Fallback circle
                }
                return (
                  <g key="real-origin-zone">
                    {geomCoords.length > 2 ? (
                      <path
                        d={toPath(geomCoords)}
                        fill="rgba(245, 158, 11, 0.18)"
                        stroke="#f59e0b"
                        strokeWidth="2"
                        strokeDasharray="6 3"
                      />
                    ) : (
                      <circle cx={c.x} cy={c.y} r="18" fill="rgba(245, 158, 11, 0.18)" stroke="#f59e0b" strokeWidth="2" strokeDasharray="6 3" />
                    )}
                    <circle cx={c.x} cy={c.y} r="5" fill="#f59e0b" />
                    <text x={c.x + 8} y={c.y + 4} fill="#f59e0b" fontSize="9" fontWeight="700" fontFamily="monospace">
                      PROBABLE ORIGIN ZONE ({(phase5Data.origin.confidence * 100).toFixed(1)}% CONF)
                    </text>
                  </g>
                );
              })()}
            </g>
          )}


          {/* ── DEMO MODE: MOCK DRIFT TRAJECTORIES ── */}
          {isDemo && activeLayers.driftSimulation && analysisComplete && driftParticles.map((particle, pi) => {
            const progress = ((animFrame + pi * 3) % 120) / 120;
            const pointsToShow = Math.ceil(progress * particle.points.length);
            const pts = particle.points.slice(0, Math.max(2, pointsToShow));
            if (pts.length < 2) return null;
            return (
              <path
                key={`drift-${particle.id}`}
                d={toPolyline(pts)}
                fill="none"
                stroke="#f59e0b"
                strokeWidth="0.8"
                opacity={0.25 + progress * 0.3}
                strokeDasharray="3 3"
              />
            );
          })}

          {/* ── DEMO MODE: MOCK VESSEL TRACKS ── */}
          {isDemo && activeLayers.vesselTracks && vessels.map(vessel => {
            const isSelected = selectedVessel?.id === vessel.id;
            const isTop = vessel.id === 'Vessel-04';
            return (
              <g key={`track-${vessel.id}`}>
                <path
                  d={toPolyline(vessel.track)}
                  fill="none"
                  stroke={isTop || isSelected ? '#ef4444' : '#22d3ee'}
                  strokeWidth={isSelected ? 2.5 : isTop ? 2 : 1}
                  opacity={isSelected ? 1 : isTop ? 0.75 : 0.45}
                  strokeDasharray={isTop ? 'none' : '4 3'}
                />
                {(() => {
                  const last = vessel.track[vessel.track.length - 1];
                  const { x, y } = project(last);
                  return (
                    <circle
                      key={`dot-${vessel.id}`}
                      cx={x} cy={y} r={isSelected ? 6 : 4}
                      fill={isTop || isSelected ? '#ef4444' : '#22d3ee'}
                      opacity={isSelected ? 1 : 0.7}
                      style={{ pointerEvents: 'all', cursor: 'pointer' }}
                      onClick={() => {
                        const v = vessels.find(vv => vv.id === vessel.id);
                        if (v) onSelectVessel(v);
                      }}
                    >
                      <title>{vessel.id} — {vessel.name}</title>
                    </circle>
                  );
                })()}
              </g>
            );
          })}

          {/* ── DEMO MODE: MOCK SPILL POLYGON ── */}
          {isDemo && activeLayers.oilSpill && analysisComplete && (
            <g filter="url(#spill-glow)">
              <path
                d={toPath(spill.coordinates)}
                fill="rgba(239, 68, 68, 0.18)"
                stroke="#ef4444"
                strokeWidth="2"
                style={{ animation: 'pulse-spill 2.5s ease-in-out infinite' }}
              />
            </g>
          )}

          {/* ── DEMO MODE: MOCK ORIGIN ZONE ── */}
          {isDemo && activeLayers.oilSpill && analysisComplete && (
            <g filter="url(#origin-glow)">
              <path
                d={toPath(originZone.polygon)}
                fill="rgba(245, 158, 11, 0.1)"
                stroke="#f59e0b"
                strokeWidth="1.5"
                strokeDasharray="8 4"
                opacity={0.8}
              />
            </g>
          )}

          {/* ── REAL MODE: REAL PHASE 4 WIND & OCEAN CURRENT VECTOR FIELDS ── */}
          {!isDemo && activeLayers.wind && phase4Data?.vector_field?.wind && phase4Data.vector_field.wind.map((wv, i) => {
            const { x, y } = project({ lat: wv.latitude, lng: wv.longitude });
            if (x < 0 || y < 0 || x > svgSize.w || y > svgSize.h) return null;
            return <WindArrow key={`real-wind-${i}`} x={x} y={y} angle={wv.direction} speed={wv.speed} type="wind" />;
          })}

          {!isDemo && activeLayers.oceanCurrent && phase4Data?.vector_field?.current && phase4Data.vector_field.current.map((cv, i) => {
            const { x, y } = project({ lat: cv.latitude, lng: cv.longitude });
            if (x < 0 || y < 0 || x > svgSize.w || y > svgSize.h) return null;
            return <WindArrow key={`real-curr-${i}`} x={x} y={y} angle={cv.direction} speed={cv.speed} type="current" />;
          })}

          {/* ── DEMO MODE: WIND VECTORS ── */}
          {isDemo && activeLayers.wind && environment.windVectors.slice(0, 30).map((wv, i) => {
            const { x, y } = project(wv);
            if (x < 0 || y < 0 || x > svgSize.w || y > svgSize.h) return null;
            return <WindArrow key={`wind-${i}`} x={x} y={y} angle={wv.direction} speed={wv.speed} type="wind" />;
          })}

          {/* ── DEMO MODE: OCEAN CURRENT VECTORS ── */}
          {isDemo && activeLayers.oceanCurrent && environment.currentVectors.slice(0, 20).map((cv, i) => {
            const { x, y } = project(cv);
            if (x < 0 || y < 0 || x > svgSize.w || y > svgSize.h) return null;
            return <WindArrow key={`cur-${i}`} x={x} y={y} angle={cv.direction} speed={cv.speed} type="current" />;
          })}

          {/* ── NORTH INDICATOR ── */}
          <g transform={`translate(${svgSize.w - 45}, 14)`} style={{ pointerEvents: 'none' }}>
            <circle cx="16" cy="16" r="15" fill="rgba(6,17,31,0.8)" stroke="rgba(34,211,238,0.2)" strokeWidth="1" />
            <text x="16" y="11" textAnchor="middle" fill="#22d3ee" fontSize="8" fontWeight="700">N</text>
            <line x1="16" y1="13" x2="16" y2="24" stroke="#22d3ee" strokeWidth="1.5" />
            <polygon points="16,7 13,14 16,12 19,14" fill="#22d3ee" />
            <line x1="16" y1="24" x2="16" y2="28" stroke="#475569" strokeWidth="1" />
          </g>
        </svg>
      )}

      {/* ── MAP LEGEND ── */}
      <div
        style={{
          position: 'absolute',
          bottom: '36px',
          left: '10px',
          background: 'rgba(6, 17, 31, 0.88)',
          border: '1px solid rgba(34, 211, 238, 0.15)',
          borderRadius: '5px',
          padding: '8px 10px',
          zIndex: 20,
          backdropFilter: 'blur(8px)',
          minWidth: '148px',
        }}
      >
        <div style={{ fontSize: '0.55rem', color: '#475569', letterSpacing: '0.12em', textTransform: 'uppercase', fontWeight: 700, marginBottom: '5px' }}>
          Legend ({isDemo ? 'DEMO MODE' : 'REAL PHASE 1'})
        </div>
        {!isDemo ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div style={{ width: '14px', height: '10px', background: 'rgba(34, 211, 238, 0.15)', border: '1.5px dashed #22d3ee', borderRadius: '1px' }} />
            <span style={{ fontSize: '0.55rem', color: '#22d3ee' }}>Sentinel-1 SAR Footprint</span>
          </div>
        ) : (
          [
            { color: '#ef4444', label: 'Detected Oil Spill', fill: true },
            { color: '#f59e0b', label: 'Probable Origin Zone', fill: false, dashed: true },
            { color: '#ef4444', label: 'Top Candidate Track', fill: false },
            { color: '#22d3ee', label: 'AIS Vessel Track', fill: false },
          ].map(item => (
            <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '3px' }}>
              <div style={{ display: 'flex', alignItems: 'center', width: '20px', flexShrink: 0 }}>
                {item.fill ? (
                  <div style={{ width: '12px', height: '8px', background: `${item.color}30`, border: `1.5px solid ${item.color}`, borderRadius: '1px' }} />
                ) : (
                  <div style={{
                    width: '16px', height: '1.5px',
                    background: item.color,
                    borderTop: item.dashed ? `1.5px dashed ${item.color}` : `1.5px solid ${item.color}`,
                  }} />
                )}
              </div>
              <span style={{ fontSize: '0.55rem', color: '#64748b' }}>{item.label}</span>
            </div>
          ))
        )}
      </div>

      {/* ── LAT/LON READOUT OVERLAY ── */}
      <div
        style={{
          position: 'absolute',
          bottom: '10px',
          left: '140px',
          background: 'rgba(6, 17, 31, 0.88)',
          border: '1px solid rgba(34, 211, 238, 0.3)',
          borderRadius: '4px',
          padding: '3px 9px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          zIndex: 20,
          backdropFilter: 'blur(6px)',
          fontFamily: 'monospace',
          fontSize: '0.625rem',
          color: '#94a3b8',
          letterSpacing: '0.05em',
          pointerEvents: 'none',
        }}
      >
        <span>
          LAT{' '}
          <span style={{ color: '#22d3ee', fontWeight: 600 }}>
            {mouseCoords
              ? `${Math.abs(mouseCoords.lat).toFixed(4)}°${mouseCoords.lat >= 0 ? 'N' : 'S'}`
              : '18.4000°N'}
          </span>
        </span>
        <span>
          LON{' '}
          <span style={{ color: '#22d3ee', fontWeight: 600 }}>
            {mouseCoords
              ? `${Math.abs(mouseCoords.lng).toFixed(4)}°${mouseCoords.lng >= 0 ? 'E' : 'W'}`
              : '65.2000°E'}
          </span>
        </span>
      </div>

      {/* ── LAYER CONTROLS ────────────────────────────────────────────────────── */}
      {/* These are handled externally via the activeLayers prop */}

      {/* ── TOOLTIP ───────────────────────────────────────────────────────────── */}
      {tooltip && (
        <div
          style={{
            position: 'absolute',
            left: tooltip.x + 12,
            top: tooltip.y - 10,
            background: 'rgba(6,17,31,0.92)',
            border: '1px solid rgba(34,211,238,0.2)',
            borderRadius: '4px',
            padding: '4px 8px',
            fontSize: '0.62rem',
            color: '#94a3b8',
            zIndex: 30,
            pointerEvents: 'none',
            backdropFilter: 'blur(6px)',
            whiteSpace: 'nowrap',
          }}
        >
          {tooltip.content}
        </div>
      )}

      {/* ── PROCESSING OVERLAY ────────────────────────────────────────────────── */}
      {!analysisComplete && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(3, 13, 24, 0.5)',
            zIndex: 15,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '12px',
            pointerEvents: 'none',
          }}
        >
          <div
            style={{
              width: '40px', height: '40px',
              border: '2px solid rgba(34, 211, 238, 0.2)',
              borderTopColor: '#22d3ee',
              borderRadius: '50%',
              animation: 'spin-slow 1.2s linear infinite',
            }}
          />
          <div style={{ fontSize: '0.7rem', color: '#22d3ee', letterSpacing: '0.12em', fontWeight: 600, textTransform: 'uppercase' }}>
            Awaiting Analysis
          </div>
          <div style={{ fontSize: '0.6rem', color: '#475569', textAlign: 'center' }}>
            Run analysis to detect spill and correlate vessels
          </div>
        </div>
      )}
    </div>
  );
}
