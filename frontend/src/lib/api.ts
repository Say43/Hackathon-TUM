import type { LandPlot, TimeSeriesPoint } from "../types";

/**
 * Single source of truth for the backend URL. Trailing slashes are trimmed so
 * concatenation with `/api/...` never produces `//api/...`.
 *
 * The frontend is API-only: if this is empty or unreachable, the UI shows an
 * explicit error instead of silently retrying against the Vite proxy or
 * localhost. Configure it via `frontend/.env`:
 *
 *     VITE_API_BASE_URL=<jupyter-backend-base-url>
 */
const RAW_API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").trim();
export const API_BASE = RAW_API_BASE.replace(/\/+$/, "");
export const IS_API_CONFIGURED = API_BASE.length > 0;

export type PlotsApiResponse = {
  split: string;
  plots: unknown[];
  errors?: string[];
};

export type HealthResponse = {
  status: string;
  modelLoaded: boolean;
  datasetPresent: boolean;
  cachedPredictionsPresent: boolean;
  testTiles: number;
  error?: string | null;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly cause?: unknown,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch(path: string): Promise<Response> {
  if (!IS_API_CONFIGURED) {
    throw new ApiError(
      "VITE_API_BASE_URL is not configured. Set it in frontend/.env and restart the dev server.",
    );
  }
  const url = `${API_BASE}${path}`;
  let response: Response;
  try {
    response = await fetch(url);
  } catch (err) {
    throw new ApiError(
      `Could not reach the backend at ${API_BASE}. Check VITE_API_BASE_URL and that the Jupyter backend is online.`,
      err,
    );
  }
  if (!response.ok) {
    throw new ApiError(
      `Backend responded with ${response.status} ${response.statusText} for ${path}`,
      undefined,
      response.status,
    );
  }
  return response;
}

export async function fetchHealth(): Promise<HealthResponse | null> {
  try {
    const r = await apiFetch("/api/health");
    return (await r.json()) as HealthResponse;
  } catch (err) {
    if (err instanceof ApiError) {
      return {
        status: "unreachable",
        modelLoaded: false,
        datasetPresent: false,
        cachedPredictionsPresent: false,
        testTiles: 0,
        error: err.message,
      };
    }
    throw err;
  }
}

export async function fetchPlots(): Promise<PlotsApiResponse | null> {
  try {
    const r = await apiFetch("/api/plots?split=test");
    return (await r.json()) as PlotsApiResponse;
  } catch {
    return null;
  }
}

/** Map API JSON to strict `LandPlot` (drops unknown keys). */
export function normalizeLandPlot(raw: unknown): LandPlot {
  const o = raw as Record<string, unknown>;
  const pred = o.prediction as LandPlot["prediction"];
  const weak = (o.weakLabels ?? []) as LandPlot["weakLabels"];
  const overlays = (o.overlays ?? []) as LandPlot["overlays"];
  return {
    id: String(o.id),
    tileId: String(o.tileId),
    region: String(o.region),
    country: String(o.country ?? ""),
    areaHa: Number(o.areaHa ?? 0),
    forestCoverPct: Number(o.forestCoverPct ?? 0),
    centroidLat: Number(o.centroidLat ?? 0),
    centroidLng: Number(o.centroidLng ?? 0),
    prediction: {
      deforestationDetected: Boolean(pred.deforestationDetected),
      confidence: Number(pred.confidence),
      eventMonth: String(pred.eventMonth ?? ""),
      modelVersion: String(pred.modelVersion ?? ""),
      notes: String(pred.notes ?? ""),
      labelAgreement: (["agreement", "conflict", "uncertain"].includes(
        String(pred.labelAgreement),
      )
        ? pred.labelAgreement
        : "uncertain") as LandPlot["prediction"]["labelAgreement"],
    },
    weakLabels: weak.map((w) => ({
      labelSource: String(w.labelSource),
      label: w.label,
      confidence: Number(w.confidence),
      acquisitionMonth: w.acquisitionMonth,
    })),
    riskScore: Number(o.riskScore ?? 0),
    eudrRiskTier: o.eudrRiskTier as LandPlot["eudrRiskTier"],
    reviewStatus: o.reviewStatus as LandPlot["reviewStatus"],
    signalStrength: Number(o.signalStrength ?? 0),
    labelConsistency: Number(o.labelConsistency ?? 0),
    temporalConsistency: Number(o.temporalConsistency ?? 0),
    regionAnomalyRisk: Number(o.regionAnomalyRisk ?? 0),
    evidenceCompleteness: Number(o.evidenceCompleteness ?? 0),
    dataQualityConfidence: Number(o.dataQualityConfidence ?? 0),
    humanReviewNeeded: Boolean(o.humanReviewNeeded),
    complianceRelevance: o.complianceRelevance as LandPlot["complianceRelevance"],
    overlays,
    changeWindowStart: String(o.changeWindowStart ?? ""),
    changeWindowEnd: String(o.changeWindowEnd ?? ""),
    heatmap: o.heatmap as number[][] | undefined,
    apiSource: o._apiSource as string | undefined,
  };
}

export async function fetchTileTimeseries(
  tileId: string,
): Promise<TimeSeriesPoint[] | null> {
  try {
    const r = await apiFetch(
      `/api/tiles/${encodeURIComponent(tileId)}/timeseries?split=test`,
    );
    const j = (await r.json()) as { points: TimeSeriesPoint[] };
    return j.points ?? null;
  } catch {
    return null;
  }
}
