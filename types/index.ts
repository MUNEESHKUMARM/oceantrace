// ─── Core Types for OceanTrace AI ─────────────────────────────────────────────

export interface LatLng {
  lat: number;
  lng: number;
}

export interface SpillPolygon {
  id: string;
  coordinates: LatLng[];
  areaKm2: number;
  confidence: number;
  detectedAt: string;
  riskLevel: 'low' | 'moderate' | 'high' | 'critical';
  sarImageId: string;
}

export interface OriginZone {
  center: LatLng;
  radiusKm: number;
  confidence: number;
  estimatedReleaseWindow: {
    start: string;
    end: string;
  };
  polygon: LatLng[];
}

export interface VesselTrackPoint {
  lat: number;
  lng: number;
  timestamp: string;
  speed: number;
  heading: number;
}

export interface Vessel {
  id: string;
  mmsi: string;
  name: string;
  type: 'Tanker' | 'Cargo' | 'Fishing' | 'Chemical Tanker' | 'Bulk Carrier';
  flag: string;
  length: number;
  beam: number;
  track: VesselTrackPoint[];
  lastKnownPosition: LatLng;
  distanceToOriginKm: number;
  similarityScore: number;
  behaviourScore: number;
  confidence: number;
  proximityScore: number;
  timelineScore: number;
  trajectoryScore: number;
  anomalyScore: number;
  environmentScore: number;
  overallScore: number;
  aisGapHours?: number;
  speedAnomaly?: boolean;
}

export interface WindVector {
  lat: number;
  lng: number;
  speed: number;
  direction: number;
}

export interface CurrentVector {
  lat: number;
  lng: number;
  speed: number;
  direction: number;
}

export interface DriftParticle {
  id: number;
  points: LatLng[];
  type: 'backward' | 'forward';
}

export interface EnvironmentData {
  windSpeed: number;
  windDirection: number;
  currentSpeed: number;
  currentDirection: number;
  waveHeight: number;
  seaSurfaceTemp: number;
  windVectors: WindVector[];
  currentVectors: CurrentVector[];
}

export interface SpillCase {
  id: string;
  title: string;
  location: string;
  detectedAt: string;
  spill: SpillPolygon;
  originZone: OriginZone;
  vessels: Vessel[];
  environment: EnvironmentData;
  driftParticles: DriftParticle[];
  riskLevel: 'low' | 'moderate' | 'high' | 'critical';
  coastalThreats: CoastalThreat[];
}

export interface CoastalThreat {
  id: string;
  name: string;
  type: 'fishing_zone' | 'marine_reserve' | 'coastline' | 'port';
  severity: 'low' | 'moderate' | 'high' | 'critical';
  distanceKm: number;
  estimatedArrivalHours: number;
  position: LatLng;
}

export type PipelineStage = {
  id: number;
  label: string;
  description: string;
  status: 'pending' | 'active' | 'completed' | 'warning' | 'critical' | 'not_available';
};

export type MapLayer = 
  | 'oilSpill'
  | 'vesselTracks'
  | 'wind'
  | 'oceanCurrent'
  | 'driftSimulation'
  | 'coastalRisk'
  | 'ports'
  | 'fishingZones';

export interface SystemStatus {
  satellite: 'online' | 'offline' | 'degraded';
  aiEngine: 'ready' | 'processing' | 'offline';
  ais: 'connected' | 'disconnected' | 'degraded';
  wind: 'online' | 'offline';
  current: 'online' | 'offline';
  driftModel: 'ready' | 'running' | 'offline';
}

export interface Phase1Result {
  status: string;
  product_type: string;
  output_file: string;
  output_filename: string;
  preview_file?: string;
  preview_filename?: string;
  thumbnail_file?: string;
  thumbnail_filename?: string;
  acquisition_time: string;
  polarization: string;
  processing: {
    radiometric_calibration: boolean;
    speckle_filtering: boolean;
    decibel_scaling: boolean;
    geometric_correction: boolean;
    land_sea_masking: boolean;
  };
  validation: {
    finite_pixels_count: number;
    nan_pixels_count: number;
    total_pixels_count: number;
    valid_pixels_pct: number;
    min_value_db: number;
    max_value_db: number;
    mean_value_db: number;
  };
  raster_info: {
    width: number;
    height: number;
    crs: string;
    bounds: {
      min_lon: number;
      min_lat: number;
      max_lon: number;
      max_lat: number;
    };
    min_value_db: number;
    max_value_db: number;
    mean_value_db: number;
  };
  visualization?: {
    preview_filename: string;
    thumbnail_filename: string;
    statistics: {
      source_min: number;
      source_max: number;
      p2: number;
      p98: number;
      preview_min: number;
      preview_max: number;
    };
  };
}

export interface Phase2Result {
  detected: boolean;
  confidence: number;
  mask_file: string;
  confidence_file: string;
  overlay_file: string;
  class_distribution: {
    background_pixels: number;
    oil_spill_pixels: number;
    lookalike_pixels: number;
  };
  oil_pixel_percentage?: number;
  predicted_oil_pixels?: number;
  model_info: {
    architecture: string;
    checkpoint: string;
    device: string;
  };
}

export interface Phase3Result {
  status: string;
  phase: number;
  spill_detected: boolean;
  regions_count: number;
  total_area_m2: number;
  total_area_km2: number;
  centroid?: {
    latitude: number;
    longitude: number;
  } | null;
  bbox?: {
    min_lat: number;
    min_lon: number;
    max_lat: number;
    max_lon: number;
  } | null;
  severity: {
    level: string;
    index: number;
    basis: string;
  };
  confidence: number;
  acquisition_time: string;
  processing_time: string;
  scene_id: string;
  spill_regions: Array<{
    region_id: number;
    area_m2: number;
    area_km2: number;
    centroid: { latitude: number; longitude: number };
    bbox: { min_lat: number; min_lon: number; max_lat: number; max_lon: number };
  }>;
  geojson_file: string;
  cleaned_mask_file: string;
  visualization_file: string;
}

export interface VectorFieldPointData {
  latitude: number;
  longitude: number;
  u: number;
  v: number;
  speed: number;
  direction: number;
}

export interface Phase4Result {
  status: string;
  phase: number;
  timestamp: {
    requested: string;
    wind_data: string;
    current_data: string;
    time_difference_sec: number;
  };
  wind: {
    u10_mean: number;
    v10_mean: number;
    speed_ms: number;
    direction_deg: number;
    direction_convention: string;
  };
  ocean_current: {
    u_mean: number;
    v_mean: number;
    speed_ms: number;
    direction_deg: number;
    direction_convention: string;
  };
  sources: {
    wind: string;
    current: string;
    classification: string;
  };
  vector_field: {
    wind: VectorFieldPointData[];
    current: VectorFieldPointData[];
  };
}

export interface Phase5Result {
  status: string;
  phase: number;
  origin_available?: boolean;
  backward_drift: {
    duration_hours: number;
    particle_count: number;
    trajectory_file: string;
    points_sample: Array<{
      particle_id: number;
      timestamp: string;
      latitude: number;
      longitude: number;
    }>;
  };
  forward_drift: {
    duration_hours: number;
    particle_count: number;
    trajectory_file: string;
  };
  origin: {
    zone_file: string;
    centroid: { latitude: number; longitude: number };
    area_km2: number;
    confidence: number;
    geojson_feature: any;
  };
  release_window: {
    start: string;
    end: string;
  };
  outputs: {
    backward_drift_geojson: string;
    forward_drift_geojson: string;
    origin_zone_geojson: string;
    drift_map_png: string;
  };
}

export interface PipelineResult {
  status: string;
  phase: number;
  phase1: Phase1Result;
  phase2: Phase2Result;
  phase3?: Phase3Result;
  phase4?: Phase4Result;
  phase5?: Phase5Result;
  environment?: Phase4Result;
  drift?: Phase5Result;
  scene: {
    id: string;
    satellite: string;
    product_type: string;
    polarization: string;
    acquisition_time: string;
  };
  raster: {
    width: number;
    height: number;
    dtype: string;
    crs: string;
  };
  preprocessing: {
    completed: boolean;
  };
  detection: {
    model: string;
    model_type: string;
    oil_detected: boolean;
    confidence: number;
  };
  mapping?: {
    spill_detected: boolean;
    total_area_km2: number;
    total_area_m2: number;
    regions_count: number;
    centroid?: { latitude: number; longitude: number } | null;
    bbox?: { min_lat: number; min_lon: number; max_lat: number; max_lon: number } | null;
    severity: { level: string; index: number; basis: string };
    geojson_file: string;
  };
  outputs: {
    sar_preview: string;
    mask: string;
    confidence: string;
    overlay: string;
    spill_polygon_geojson?: string;
    spill_map_png?: string;
  };
}

// ─── Phase 6.1 AISStream Collector Types ─────────────────────────────────────

export interface AISCollectorStatus {
  status: string;
  phase: number;
  collector_status: 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING' | 'DISABLED';
  connected: boolean;
  active: boolean;
  total_messages_received: number;
  position_reports_received: number;
  unique_mmsi_count: number;
  last_message_utc: string | null;
  uptime_seconds: number;
  api_key_configured: boolean;
  configured_aoi_bbox: number[][][];
}

export interface AISVesselPosition {
  id: number;
  mmsi: string;
  latitude: number;
  longitude: number;
  sog_knots: number | null;
  cog_degrees: number | null;
  heading_degrees: number | null;
  nav_status: number | null;
  timestamp_utc: string;
  received_at_utc: string;
}

// ─── Phase 6.2 AIS Correlation Types ──────────────────────────────────────────

export interface AISCorrelationCandidate {
  mmsi: string;
  observation_count: number;
  first_observation: string;
  last_observation: string;
  minimum_distance_to_origin_km: number | null;
  closest_approach_time: string | null;
  position_count_inside_origin_zone: number;
  track_intersects_origin_zone: boolean;
  temporal_overlap: boolean;
  track_geometry_available: boolean;
  mean_sog_knots: number | null;
  max_sog_knots: number | null;
  min_sog_knots: number | null;
  mean_cog_degrees: number | null;
  navigation_status_values: number[];
}

export interface AISCorrelationResponse {
  status: string;
  phase: number;
  scene_id: string;
  correlation_available: boolean;
  origin_available: boolean;
  origin_centroid: { latitude: number; longitude: number } | null;
  estimated_release_window: { start_time_utc: string; end_time_utc: string } | null;
  search_radius_km: number;
  candidate_count: number;
  candidates: AISCorrelationCandidate[];
  source_ais_phase: string;
  reason?: string;
}

// ─── Phase 6.3 Explainable Candidate Ranking Types ────────────────────────────

export interface AISRankedCandidate {
  rank: number;
  mmsi: string;
  candidate_score: number;
  score_type: string;
  evidence: {
    spatial_score: number;
    intersection_score: number;
    temporal_score: number;
    observation_score: number;
  };
  evidence_summary: string[];
  explanation: string;
  raw_evidence?: AISCorrelationCandidate;
}

export interface AISRankingResponse {
  status: string;
  phase: number;
  scene_id: string;
  ranking_title: string;
  ranking_available: boolean;
  ranking_methodology_version: string;
  ranking_configuration: Record<string, number>;
  configured_weights: Record<string, number>;
  normalized_weights: Record<string, number>;
  candidate_count: number;
  ranked_candidates: AISRankedCandidate[];
  interpretation: string;
  output_file?: string;
  reason?: string;
  source_correlation_phase?: string;
}

// ─── Phase 7 Automated Investigation Report Types ──────────────────────────────

export interface ReportSectionIdent {
  report_id: string;
  scene_id: string;
  sentinel_product_id: string;
  acquisition_timestamp: string;
  report_generated_at: string;
  system_version: string;
  methodology_versions: Record<string, string>;
  source_provenance: Record<string, string>;
  source_phase: string;
}

export interface ReportSectionDetection {
  oil_detected: boolean;
  predicted_oil_pixels: number;
  predicted_oil_percentage: number;
  model_reference: string;
  preprocessing_normalization: string;
  detection_output_path: string;
  summary: string;
  source_phase: string;
}

export interface ReportSectionMapping {
  spill_detected: boolean;
  region_count: number;
  total_area_km2: number;
  total_area_m2: number;
  severity: string | null;
  geojson_file: string;
  centroid?: { latitude: number; longitude: number } | null;
  bbox?: { min_lat: number; min_lon: number; max_lat: number; max_lon: number } | null;
  summary: string;
  source_phase: string;
}

export interface ReportSectionEnvironment {
  wind_u10: number;
  wind_v10: number;
  wind_speed_m_s: number;
  wind_direction_deg: number;
  wind_source: string;
  wind_timestamp: string;
  wind_offset_seconds: number;
  current_u: number;
  current_v: number;
  current_speed_m_s: number;
  current_direction_deg: number;
  current_source: string;
  current_timestamp: string;
  current_offset_seconds: number;
  summary: string;
  source_phase: string;
}

export interface ReportSectionDrift {
  drift_available: boolean;
  origin_available: boolean;
  particle_count: number;
  timestep_seconds: number;
  duration_hours: number;
  wind_leeway_coefficient: number;
  diffusion_coefficient: number;
  forward_drift_geojson: string;
  backward_drift_geojson: string;
  origin_centroid?: { latitude: number; longitude: number } | null;
  origin_area_km2?: number | null;
  estimated_release_window?: { start_time_utc: string; end_time_utc: string } | null;
  origin_confidence_score?: number | null;
  origin_confidence_semantics: string;
  summary: string;
  source_phase: string;
}

export interface ReportSectionAIS {
  ais_available: boolean;
  collector_status: string;
  ais_source: string;
  correlation_available: boolean;
  observations_considered: number;
  candidate_count: number;
  spatial_evidence: Record<string, any>;
  temporal_evidence: Record<string, any>;
  candidate_summary: Array<Record<string, any>>;
  summary: string;
  source_phase: string;
}

export interface ReportSectionRanking {
  ranking_available: boolean;
  ranking_title: string;
  ranking_methodology_version: string;
  configured_weights: Record<string, number>;
  normalized_weights: Record<string, number>;
  candidate_count: number;
  ranked_candidates: Array<Record<string, any>>;
  ranking_semantics: string;
  summary: string;
  source_phase: string;
}

export interface OperationalAlert {
  alert_available: boolean;
  attention_level: 'NO_EVENT' | 'LOW_ATTENTION' | 'MEDIUM_ATTENTION' | 'HIGH_ATTENTION' | 'CRITICAL_ATTENTION';
  alert_type: string;
  scene_id: string;
  generated_at: string;
  trigger_evidence: string[];
  requires_human_review: boolean;
  attention_rule_version: string;
  disclaimer: string;
}

export interface InvestigationReportResponse {
  status: string;
  phase: number;
  report_id: string;
  scene_id: string;
  generated_at: string;
  identification: ReportSectionIdent;
  sar_detection: ReportSectionDetection;
  spill_mapping: ReportSectionMapping;
  environmental_conditions: ReportSectionEnvironment;
  drift_analysis: ReportSectionDrift;
  ais_correlation: ReportSectionAIS;
  vessel_candidate_ranking: ReportSectionRanking;
  operational_alert: OperationalAlert;
  attention_threshold_configuration: Record<string, any>;
  output_files: {
    json_report: string;
    markdown_report: string;
  };
  scientific_limitation: string;
}

export interface InvestigationStatusResponse {
  scene_id: string;
  report_available: boolean;
  alert_available: boolean;
  attention_level: string;
  requires_human_review: boolean;
  generated_at?: string | null;
  report_json_path?: string | null;
  report_md_path?: string | null;
}




