import {
  Phase1Result,
  Phase2Result,
  PipelineResult,
  AISCollectorStatus,
  AISVesselPosition,
  AISCorrelationResponse,
  AISRankingResponse,
  InvestigationReportResponse,
  InvestigationStatusResponse,
} from '@/types';

// Priority resolution for public API base URL
const RAW_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://localhost:8000/api';

/**
 * Safely normalizes endpoint URL construction to strictly prevent `/api/api/...` duplication.
 */
export function getApiEndpoint(path: string): string {
  const base = RAW_BASE_URL.replace(/\/+$/, '');
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  if (base.endsWith('/api') && cleanPath.startsWith('/api/')) {
    return `${base}${cleanPath.substring(4)}`;
  }
  return `${base}${cleanPath}`;
}

export interface ProcessSARParams {
  bbox?: [number, number, number, number];
  start_date?: string;
  end_date?: string;
  polarization?: string;
  width?: number;
  height?: number;
}

// ─── Phase 1: Sentinel-1 Acquisition & Preprocessing ───────────────────────

export async function processSentinel1SAR(params: ProcessSARParams = {}): Promise<Phase1Result> {
  const payload: Record<string, any> = {
    bbox: params.bbox || [71.5, 18.0, 72.5, 19.0],
    polarization: params.polarization || 'VV',
    width: params.width || 512,
    height: params.height || 512,
  };
  if (params.start_date) payload.start_date = params.start_date;
  if (params.end_date) payload.end_date = params.end_date;

  const url = getApiEndpoint('/sentinel1/process');
  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    throw new Error(
      `Cannot connect to FastAPI backend at ${url}. Please ensure the backend server is running.`
    );
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Backend processing failed' }));
    throw new Error(errorData.detail || `HTTP Error ${response.status}`);
  }

  return await response.json();
}

// ─── Phase 2: PyTorch U-Net AI Detection ────────────────────────────────────

export async function runOilDetection(geotiffPath: string): Promise<Phase2Result> {
  const url = getApiEndpoint('/detection/run');
  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ geotiff_path: geotiffPath }),
    });
  } catch (err) {
    throw new Error(
      `Cannot connect to FastAPI backend at ${url}. Please ensure the backend server is running.`
    );
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Detection inference failed' }));
    throw new Error(errorData.detail || `HTTP Error ${response.status}`);
  }

  return await response.json();
}

// ─── Phase 1-5 Pipeline Execution ──────────────────────────────────────────

export async function runFullPipeline(params: ProcessSARParams = {}): Promise<PipelineResult> {
  const payload: Record<string, any> = {
    bbox: params.bbox || [71.5, 18.0, 72.5, 19.0],
    polarization: params.polarization || 'VV',
    width: params.width || 512,
    height: params.height || 512,
  };
  if (params.start_date) payload.start_date = params.start_date;
  if (params.end_date) payload.end_date = params.end_date;

  const url = getApiEndpoint('/detection/run-pipeline');
  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    throw new Error(
      `Cannot connect to FastAPI backend at ${url}. Please ensure the backend server is running.`
    );
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Pipeline execution failed' }));
    throw new Error(errorData.detail || `HTTP Error ${response.status}`);
  }

  return await response.json();
}

export function getSARPreviewUrl(imageId?: string): string {
  if (!imageId) return '/sar_preview.png';
  if (imageId.startsWith('http://') || imageId.startsWith('https://')) return imageId;
  return getApiEndpoint(`/sentinel1/preview/${imageId}`);
}

// ─── Phase 6.1: Live AIS Collector Status & Recent Records ─────────────────

export async function getAISCollectorStatus(): Promise<AISCollectorStatus> {
  const url = getApiEndpoint('/ais/status');
  let response: Response;
  try {
    response = await fetch(url, { method: 'GET', cache: 'no-store' });
  } catch (err) {
    throw new Error(`Failed to connect to backend AIS status endpoint at ${url}`);
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch AIS status' }));
    throw new Error(errorData.detail || `HTTP Error ${response.status}`);
  }

  return await response.json();
}

export async function getRecentAISPositions(limit: number = 20): Promise<AISVesselPosition[]> {
  const url = getApiEndpoint(`/ais/recent?limit=${limit}`);
  let response: Response;
  try {
    response = await fetch(url, { method: 'GET', cache: 'no-store' });
  } catch (err) {
    throw new Error(`Failed to connect to backend recent AIS endpoint at ${url}`);
  }

  if (!response.ok) {
    return [];
  }

  return await response.json();
}

// ─── Phase 6.2: AIS Spatial & Temporal Correlation Engine ───────────────────

export async function correlateAISVessels(sceneId?: string): Promise<AISCorrelationResponse> {
  const url = getApiEndpoint('/ais/correlate');
  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scene_id: sceneId || null }),
    });
  } catch (err) {
    throw new Error(`Failed to connect to backend AIS correlation endpoint at ${url}`);
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'AIS correlation failed' }));
    throw new Error(errorData.detail || `HTTP Error ${response.status}`);
  }

  return await response.json();
}

// ─── Phase 6.3: Explainable Candidate Ranking Engine ────────────────────────

export async function rankAISCandidates(sceneId?: string): Promise<AISRankingResponse> {
  const url = getApiEndpoint('/ais/rank');
  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scene_id: sceneId || null }),
    });
  } catch (err) {
    throw new Error(`Failed to connect to backend candidate ranking endpoint at ${url}`);
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Candidate ranking failed' }));
    throw new Error(errorData.detail || `HTTP Error ${response.status}`);
  }

  return await response.json();
}

// ─── Phase 7: Automated Investigation Report & Alert Engine ─────────────────

export async function generateInvestigationReport(sceneId?: string): Promise<InvestigationReportResponse> {
  const url = getApiEndpoint('/investigation/report');
  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scene_id: sceneId || null }),
    });
  } catch (err) {
    throw new Error(`Failed to connect to backend investigation report endpoint at ${url}`);
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Report generation failed' }));
    throw new Error(errorData.detail || `HTTP Error ${response.status}`);
  }

  return await response.json();
}

export async function getInvestigationReport(sceneId: string): Promise<InvestigationReportResponse> {
  const url = getApiEndpoint(`/investigation/report/${sceneId}`);
  let response: Response;
  try {
    response = await fetch(url, { method: 'GET', cache: 'no-store' });
  } catch (err) {
    throw new Error(`Failed to retrieve investigation report at ${url}`);
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to retrieve report' }));
    throw new Error(errorData.detail || `HTTP Error ${response.status}`);
  }

  return await response.json();
}

export async function getInvestigationStatus(sceneId?: string): Promise<InvestigationStatusResponse> {
  const query = sceneId ? `?scene_id=${encodeURIComponent(sceneId)}` : '';
  const url = getApiEndpoint(`/investigation/status${query}`);
  let response: Response;
  try {
    response = await fetch(url, { method: 'GET', cache: 'no-store' });
  } catch (err) {
    throw new Error(`Failed to fetch investigation status at ${url}`);
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch status' }));
    throw new Error(errorData.detail || `HTTP Error ${response.status}`);
  }

  return await response.json();
}
