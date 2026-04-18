import type { LandPlot, TimeSeriesPoint } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://129.212.191.202:8000";

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

function candidateApiBases(): string[] {
  const bases = [
    API_BASE,
    "",
  ];
  return [...new Set(bases.map((b) => b.trim()))];
}

async function apiFetch(path: string): Promise<Response | null> {
  for (const base of candidateApiBases()) {
    try {
      const r = await fetch(`${base}${path}`);
      if (r.ok) return r;
    } catch {
      continue;
    }
  }
  return null;
}

export async function fetchHealth(): Promise<HealthResponse | null> {
  const r = await apiFetch("/api/health");
  if (!r) return null;
  return (await r.json()) as HealthResponse;
}

export async function fetchPlots(): Promise<PlotsApiResponse | null> {
  const r = await apiFetch("/api/plots?split=test");
  if (!r) return null;
  return (await r.json()) as PlotsApiResponse;
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
  const r = await apiFetch(
    `/api/tiles/${encodeURIComponent(tileId)}/timeseries?split=test`,
  );
  if (!r) return null;
  const j = (await r.json()) as { points: TimeSeriesPoint[] };
  return j.points ?? null;
}
