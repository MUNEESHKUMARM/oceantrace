// ─── Mock Data: Oil Spill Case ─────────────────────────────────────────────────
import { SpillCase } from '@/types';

export const mockSpillCase: SpillCase = {
  id: 'CASE-2024-0847',
  title: 'Arabian Sea Oil Spill — SAR Detection Event',
  location: 'Arabian Sea, 18.4°N 65.2°E',
  detectedAt: '2024-11-14T06:23:00Z',
  riskLevel: 'critical',

  spill: {
    id: 'SPILL-0847',
    areaKm2: 20.4,
    confidence: 0.91,
    detectedAt: '2024-11-14T06:23:00Z',
    riskLevel: 'critical',
    sarImageId: 'S1A_IW_GRDH_20241114',
    coordinates: [
      { lat: 18.42, lng: 65.18 },
      { lat: 18.45, lng: 65.22 },
      { lat: 18.47, lng: 65.28 },
      { lat: 18.44, lng: 65.33 },
      { lat: 18.40, lng: 65.35 },
      { lat: 18.36, lng: 65.31 },
      { lat: 18.34, lng: 65.25 },
      { lat: 18.36, lng: 65.19 },
      { lat: 18.39, lng: 65.16 },
      { lat: 18.42, lng: 65.18 },
    ],
  },

  originZone: {
    center: { lat: 18.55, lng: 65.05 },
    radiusKm: 12,
    confidence: 0.72,
    estimatedReleaseWindow: {
      start: '2024-11-13T18:00:00Z',
      end: '2024-11-14T00:00:00Z',
    },
    polygon: [
      { lat: 18.62, lng: 64.95 },
      { lat: 18.65, lng: 65.08 },
      { lat: 18.60, lng: 65.18 },
      { lat: 18.52, lng: 65.20 },
      { lat: 18.44, lng: 65.14 },
      { lat: 18.44, lng: 65.01 },
      { lat: 18.50, lng: 64.93 },
      { lat: 18.58, lng: 64.93 },
      { lat: 18.62, lng: 64.95 },
    ],
  },

  vessels: [
    {
      id: 'Vessel-04',
      mmsi: '123456789',
      name: 'MV Arafura Spirit',
      type: 'Tanker',
      flag: 'Liberia',
      length: 274,
      beam: 48,
      lastKnownPosition: { lat: 18.60, lng: 65.48 },
      distanceToOriginKm: 8.4,
      similarityScore: 0.87,
      behaviourScore: 0.82,
      confidence: 0.86,
      proximityScore: 0.91,
      timelineScore: 0.88,
      trajectoryScore: 0.87,
      anomalyScore: 0.79,
      environmentScore: 0.83,
      overallScore: 86,
      aisGapHours: 6.2,
      speedAnomaly: true,
      track: [
        { lat: 18.80, lng: 64.60, timestamp: '2024-11-13T12:00:00Z', speed: 14.2, heading: 142 },
        { lat: 18.72, lng: 64.72, timestamp: '2024-11-13T14:00:00Z', speed: 13.8, heading: 138 },
        { lat: 18.65, lng: 64.88, timestamp: '2024-11-13T16:00:00Z', speed: 8.1, heading: 135 },
        { lat: 18.58, lng: 65.00, timestamp: '2024-11-13T18:00:00Z', speed: 2.3, heading: 130 },
        { lat: 18.55, lng: 65.05, timestamp: '2024-11-13T20:00:00Z', speed: 0.4, heading: 125 },
        { lat: 18.54, lng: 65.12, timestamp: '2024-11-13T22:00:00Z', speed: 3.1, heading: 128 },
        { lat: 18.56, lng: 65.22, timestamp: '2024-11-14T00:00:00Z', speed: 10.2, heading: 112 },
        { lat: 18.58, lng: 65.35, timestamp: '2024-11-14T02:00:00Z', speed: 14.5, heading: 108 },
        { lat: 18.60, lng: 65.48, timestamp: '2024-11-14T04:00:00Z', speed: 14.8, heading: 105 },
      ],
    },
    {
      id: 'Vessel-01',
      mmsi: '987654321',
      name: 'MV Pacific Regent',
      type: 'Chemical Tanker',
      flag: 'Panama',
      length: 183,
      beam: 32,
      lastKnownPosition: { lat: 18.25, lng: 65.55 },
      distanceToOriginKm: 34.2,
      similarityScore: 0.62,
      behaviourScore: 0.58,
      confidence: 0.61,
      proximityScore: 0.65,
      timelineScore: 0.60,
      trajectoryScore: 0.62,
      anomalyScore: 0.55,
      environmentScore: 0.60,
      overallScore: 62,
      aisGapHours: 1.5,
      speedAnomaly: false,
      track: [
        { lat: 18.10, lng: 64.80, timestamp: '2024-11-13T12:00:00Z', speed: 12.0, heading: 60 },
        { lat: 18.14, lng: 64.95, timestamp: '2024-11-13T15:00:00Z', speed: 11.8, heading: 62 },
        { lat: 18.18, lng: 65.10, timestamp: '2024-11-13T18:00:00Z', speed: 12.2, heading: 58 },
        { lat: 18.21, lng: 65.28, timestamp: '2024-11-13T21:00:00Z', speed: 12.0, heading: 60 },
        { lat: 18.25, lng: 65.55, timestamp: '2024-11-14T02:00:00Z', speed: 11.5, heading: 62 },
      ],
    },
    {
      id: 'Vessel-05',
      mmsi: '456789123',
      name: 'MV Gulf Carrier',
      type: 'Tanker',
      flag: 'Marshall Islands',
      length: 228,
      beam: 42,
      lastKnownPosition: { lat: 18.70, lng: 65.62 },
      distanceToOriginKm: 52.1,
      similarityScore: 0.48,
      behaviourScore: 0.45,
      confidence: 0.47,
      proximityScore: 0.50,
      timelineScore: 0.46,
      trajectoryScore: 0.48,
      anomalyScore: 0.42,
      environmentScore: 0.46,
      overallScore: 48,
      aisGapHours: 0.8,
      speedAnomaly: false,
      track: [
        { lat: 18.90, lng: 65.20, timestamp: '2024-11-13T10:00:00Z', speed: 15.0, heading: 128 },
        { lat: 18.84, lng: 65.32, timestamp: '2024-11-13T13:00:00Z', speed: 14.8, heading: 125 },
        { lat: 18.78, lng: 65.44, timestamp: '2024-11-13T16:00:00Z', speed: 15.1, heading: 122 },
        { lat: 18.74, lng: 65.55, timestamp: '2024-11-13T19:00:00Z', speed: 14.5, heading: 120 },
        { lat: 18.70, lng: 65.62, timestamp: '2024-11-14T00:00:00Z', speed: 14.2, heading: 118 },
      ],
    },
    {
      id: 'Vessel-02',
      mmsi: '789123456',
      name: 'MV Horizon Star',
      type: 'Cargo',
      flag: 'Singapore',
      length: 156,
      beam: 28,
      lastKnownPosition: { lat: 18.15, lng: 65.70 },
      distanceToOriginKm: 68.5,
      similarityScore: 0.36,
      behaviourScore: 0.34,
      confidence: 0.35,
      proximityScore: 0.38,
      timelineScore: 0.35,
      trajectoryScore: 0.36,
      anomalyScore: 0.32,
      environmentScore: 0.34,
      overallScore: 36,
      aisGapHours: 0.3,
      speedAnomaly: false,
      track: [
        { lat: 18.05, lng: 65.40, timestamp: '2024-11-13T14:00:00Z', speed: 13.0, heading: 70 },
        { lat: 18.10, lng: 65.55, timestamp: '2024-11-13T18:00:00Z', speed: 12.8, heading: 68 },
        { lat: 18.15, lng: 65.70, timestamp: '2024-11-14T00:00:00Z', speed: 12.5, heading: 70 },
      ],
    },
    {
      id: 'Vessel-03',
      mmsi: '321654987',
      name: 'MV Eastern Wind',
      type: 'Bulk Carrier',
      flag: 'Greece',
      length: 189,
      beam: 34,
      lastKnownPosition: { lat: 18.90, lng: 65.10 },
      distanceToOriginKm: 40.8,
      similarityScore: 0.29,
      behaviourScore: 0.27,
      confidence: 0.28,
      proximityScore: 0.30,
      timelineScore: 0.28,
      trajectoryScore: 0.29,
      anomalyScore: 0.25,
      environmentScore: 0.28,
      overallScore: 29,
      aisGapHours: 0.2,
      speedAnomaly: false,
      track: [
        { lat: 19.10, lng: 65.00, timestamp: '2024-11-13T12:00:00Z', speed: 11.0, heading: 200 },
        { lat: 19.00, lng: 65.05, timestamp: '2024-11-13T16:00:00Z', speed: 10.8, heading: 198 },
        { lat: 18.90, lng: 65.10, timestamp: '2024-11-13T22:00:00Z', speed: 11.2, heading: 200 },
      ],
    },
    {
      id: 'Vessel-06',
      mmsi: '654987321',
      name: 'MV Sea Falcon',
      type: 'Fishing',
      flag: 'India',
      length: 45,
      beam: 10,
      lastKnownPosition: { lat: 18.35, lng: 65.42 },
      distanceToOriginKm: 22.1,
      similarityScore: 0.21,
      behaviourScore: 0.19,
      confidence: 0.20,
      proximityScore: 0.22,
      timelineScore: 0.20,
      trajectoryScore: 0.21,
      anomalyScore: 0.18,
      environmentScore: 0.20,
      overallScore: 21,
      aisGapHours: 0.1,
      speedAnomaly: false,
      track: [
        { lat: 18.30, lng: 65.30, timestamp: '2024-11-13T08:00:00Z', speed: 6.5, heading: 45 },
        { lat: 18.33, lng: 65.36, timestamp: '2024-11-13T14:00:00Z', speed: 5.8, heading: 50 },
        { lat: 18.35, lng: 65.42, timestamp: '2024-11-14T02:00:00Z', speed: 6.1, heading: 48 },
      ],
    },
  ],

  environment: {
    windSpeed: 8.4,
    windDirection: 245,
    currentSpeed: 0.6,
    currentDirection: 210,
    waveHeight: 1.8,
    seaSurfaceTemp: 28.4,
    windVectors: generateWindVectors(),
    currentVectors: generateCurrentVectors(),
  },

  driftParticles: generateDriftParticles(),

  coastalThreats: [
    {
      id: 'CT-001',
      name: 'Goa Fishing Zone',
      type: 'fishing_zone',
      severity: 'critical',
      distanceKm: 45.2,
      estimatedArrivalHours: 18,
      position: { lat: 15.5, lng: 73.8 },
    },
    {
      id: 'CT-002',
      name: 'Lakshadweep Marine Reserve',
      type: 'marine_reserve',
      severity: 'high',
      distanceKm: 120.4,
      estimatedArrivalHours: 48,
      position: { lat: 10.5, lng: 72.5 },
    },
    {
      id: 'CT-003',
      name: 'Oman Coastline',
      type: 'coastline',
      severity: 'high',
      distanceKm: 82.1,
      estimatedArrivalHours: 32,
      position: { lat: 22.5, lng: 59.5 },
    },
  ],
};

function generateWindVectors() {
  const vectors = [];
  for (let lat = 17.8; lat <= 19.2; lat += 0.3) {
    for (let lng = 64.5; lng <= 66.0; lng += 0.35) {
      vectors.push({
        lat,
        lng,
        speed: 7.5 + Math.random() * 2.5,
        direction: 240 + (Math.random() - 0.5) * 20,
      });
    }
  }
  return vectors;
}

function generateCurrentVectors() {
  const vectors = [];
  for (let lat = 17.8; lat <= 19.2; lat += 0.4) {
    for (let lng = 64.5; lng <= 66.0; lng += 0.45) {
      vectors.push({
        lat,
        lng,
        speed: 0.4 + Math.random() * 0.4,
        direction: 205 + (Math.random() - 0.5) * 15,
      });
    }
  }
  return vectors;
}

function generateDriftParticles() {
  const particles = [];
  const originLat = 18.55;
  const originLng = 65.05;
  for (let i = 0; i < 40; i++) {
    const offsetLat = (Math.random() - 0.5) * 0.2;
    const offsetLng = (Math.random() - 0.5) * 0.2;
    const points = [];
    let curLat = originLat + offsetLat;
    let curLng = originLng + offsetLng;
    for (let t = 0; t <= 8; t++) {
      curLat += (Math.random() - 0.55) * 0.04;
      curLng += (Math.random() + 0.2) * 0.05;
      points.push({ lat: curLat, lng: curLng });
    }
    particles.push({ id: i, points, type: 'backward' as const });
  }
  return particles;
}
