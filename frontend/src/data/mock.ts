import type {
  ActivityItem,
  LandPlot,
  MapOverlayRegion,
  TimeSeriesPoint,
  WeakLabelSource,
} from "../types";

const baseOverlays: MapOverlayRegion[] = [
  {
    id: "pred-core",
    kind: "predicted_change",
    label: "Predicted change core",
    x: 28,
    y: 24,
    w: 20,
    h: 16,
    opacity: 0.82,
    color: "#f97316",
  },
  {
    id: "weak-radd",
    kind: "weak_hint",
    label: "RADD support",
    x: 33,
    y: 30,
    w: 16,
    h: 14,
    opacity: 0.45,
    color: "#38bdf8",
  },
  {
    id: "stable-forest",
    kind: "stable_forest",
    label: "Stable forest",
    x: 55,
    y: 18,
    w: 24,
    h: 22,
    opacity: 0.25,
    color: "#22c55e",
  },
];

function makeWeakLabels(tileId: string): WeakLabelSource[] {
  return [
    {
      labelSource: "RADD",
      label: "deforestation",
      confidence: 0.76,
      acquisitionMonth: "2024-08",
    },
    {
      labelSource: "GLAD-S2",
      label: "uncertain",
      confidence: 0.58,
      acquisitionMonth: "2024-09",
    },
    {
      labelSource: "GLAD-L",
      label: "stable",
      confidence: 0.63,
      acquisitionMonth: tileId.endsWith("_6") ? "2024-07" : "2024-06",
    },
  ];
}

export const LAND_PLOTS: LandPlot[] = [
  {
    id: "plot-48PWA-0-6",
    tileId: "48PWA_0_6",
    region: "Southeast Asia",
    country: "Indonesia",
    areaHa: 1004,
    forestCoverPct: 84,
    centroidLat: -2.187,
    centroidLng: 113.912,
    prediction: {
      deforestationDetected: true,
      confidence: 0.91,
      eventMonth: "2024-09",
      modelVersion: "abdul-baseline+filter",
      notes: "High-confidence cluster aligned with cached prediction raster.",
      labelAgreement: "agreement",
    },
    weakLabels: makeWeakLabels("48PWA_0_6"),
    riskScore: 86,
    eudrRiskTier: "critical",
    reviewStatus: "queued",
    signalStrength: 0.82,
    labelConsistency: 0.71,
    temporalConsistency: 0.77,
    regionAnomalyRisk: 0.66,
    evidenceCompleteness: 0.79,
    dataQualityConfidence: 0.83,
    humanReviewNeeded: true,
    complianceRelevance: "high",
    overlays: baseOverlays,
    changeWindowStart: "2024-07",
    changeWindowEnd: "2024-10",
  },
  {
    id: "plot-18NVJ-1-6",
    tileId: "18NVJ_1_6",
    region: "Amazon Basin",
    country: "Brazil",
    areaHa: 1004,
    forestCoverPct: 89,
    centroidLat: 3.061,
    centroidLng: -75.783,
    prediction: {
      deforestationDetected: true,
      confidence: 0.84,
      eventMonth: "2024-10",
      modelVersion: "abdul-baseline+filter",
      notes: "Sparse positive mask cleaned with morphological post-processing.",
      labelAgreement: "conflict",
    },
    weakLabels: makeWeakLabels("18NVJ_1_6"),
    riskScore: 74,
    eudrRiskTier: "high",
    reviewStatus: "pending",
    signalStrength: 0.74,
    labelConsistency: 0.58,
    temporalConsistency: 0.69,
    regionAnomalyRisk: 0.54,
    evidenceCompleteness: 0.72,
    dataQualityConfidence: 0.78,
    humanReviewNeeded: true,
    complianceRelevance: "high",
    overlays: [
      ...baseOverlays,
      {
        id: "water-edge",
        kind: "water",
        label: "River corridor",
        x: 68,
        y: 56,
        w: 18,
        h: 12,
        opacity: 0.28,
        color: "#60a5fa",
      },
    ],
    changeWindowStart: "2024-08",
    changeWindowEnd: "2024-11",
  },
  {
    id: "plot-47QMA-6-2",
    tileId: "47QMA_6_2",
    region: "Mekong Corridor",
    country: "Cambodia",
    areaHa: 1004,
    forestCoverPct: 71,
    centroidLat: 13.412,
    centroidLng: 106.875,
    prediction: {
      deforestationDetected: false,
      confidence: 0.36,
      eventMonth: "2024-09",
      modelVersion: "abdul-baseline+filter",
      notes: "Current evidence remains below alert threshold.",
      labelAgreement: "uncertain",
    },
    weakLabels: makeWeakLabels("47QMA_6_2"),
    riskScore: 41,
    eudrRiskTier: "medium",
    reviewStatus: "reviewed",
    signalStrength: 0.63,
    labelConsistency: 0.67,
    temporalConsistency: 0.61,
    regionAnomalyRisk: 0.37,
    evidenceCompleteness: 0.64,
    dataQualityConfidence: 0.76,
    humanReviewNeeded: false,
    complianceRelevance: "medium",
    overlays: [
      {
        id: "stable-forest-main",
        kind: "stable_forest",
        label: "Stable canopy",
        x: 22,
        y: 20,
        w: 54,
        h: 48,
        opacity: 0.22,
        color: "#22c55e",
      },
    ],
    changeWindowStart: "2024-06",
    changeWindowEnd: "2024-09",
  },
];

export const REGIONS = Array.from(new Set(LAND_PLOTS.map((plot) => plot.region))).sort();

export const ACTIVITY_FEED: ActivityItem[] = [
  {
    id: "act-1",
    type: "detection",
    title: "Filtered positive mask promoted to alert",
    detail: "Post-processing preserved a dense positive cluster after small-object cleanup.",
    tileId: "18NVJ_1_6",
    plotId: "plot-18NVJ-1-6",
    timestamp: "2026-04-18T06:40:00Z",
    severity: "warning",
  },
  {
    id: "act-2",
    type: "label_conflict",
    title: "Weak-label disagreement detected",
    detail: "RADD and GLAD-S2 disagree on alert confidence for the selected tile.",
    tileId: "18NVJ_1_6",
    plotId: "plot-18NVJ-1-6",
    timestamp: "2026-04-18T06:31:00Z",
    severity: "warning",
  },
  {
    id: "act-3",
    type: "human_review",
    title: "Escalated for compliance review",
    detail: "Critical-risk plot routed to human validation before export.",
    tileId: "48PWA_0_6",
    plotId: "plot-48PWA-0-6",
    timestamp: "2026-04-18T06:25:00Z",
    severity: "critical",
  },
  {
    id: "act-4",
    type: "risk_update",
    title: "Portfolio risk baseline refreshed",
    detail: "Dashboard metrics updated after new cached raster import.",
    tileId: "47QMA_6_2",
    plotId: "plot-47QMA-6-2",
    timestamp: "2026-04-18T06:20:00Z",
    severity: "info",
  },
];

type SeriesRow = [string, number, number, number, number, boolean];

const SERIES_BY_PLOT: Record<string, TimeSeriesPoint[]> = {
  "plot-48PWA-0-6": ([
    ["2024-05", 0.78, -8.4, 0.73, 0.16, false],
    ["2024-06", 0.74, -8.8, 0.71, 0.22, false],
    ["2024-07", 0.69, -9.1, 0.66, 0.41, false],
    ["2024-08", 0.53, -10.8, 0.49, 0.74, true],
    ["2024-09", 0.41, -11.9, 0.38, 0.89, true],
    ["2024-10", 0.39, -12.1, 0.35, 0.82, true],
  ] as SeriesRow[]).map(toPoint),
  "plot-18NVJ-1-6": ([
    ["2024-06", 0.82, -7.2, 0.78, 0.11, false],
    ["2024-07", 0.79, -7.6, 0.76, 0.19, false],
    ["2024-08", 0.64, -8.9, 0.61, 0.37, false],
    ["2024-09", 0.49, -10.7, 0.44, 0.78, true],
    ["2024-10", 0.44, -11.2, 0.39, 0.86, true],
    ["2024-11", 0.43, -11.0, 0.41, 0.69, false],
  ] as SeriesRow[]).map(toPoint),
  "plot-47QMA-6-2": ([
    ["2024-04", 0.71, -9.3, 0.64, 0.12, false],
    ["2024-05", 0.72, -9.1, 0.65, 0.14, false],
    ["2024-06", 0.68, -9.7, 0.61, 0.21, false],
    ["2024-07", 0.63, -10.0, 0.57, 0.28, false],
    ["2024-08", 0.61, -9.8, 0.56, 0.24, false],
    ["2024-09", 0.6, -9.6, 0.55, 0.18, false],
  ] as SeriesRow[]).map(toPoint),
};

export function getTimeSeriesForPlot(plotId: string): TimeSeriesPoint[] {
  return SERIES_BY_PLOT[plotId] ?? SERIES_BY_PLOT["plot-18NVJ-1-6"];
}

function toPoint(row: SeriesRow): TimeSeriesPoint {
  const [month, sentinel2Ndvi, sentinel1Vvdb, embeddingNorm, weakLabelAggregate, eventFlag] =
    row;
  return {
    month,
    sentinel2Ndvi,
    sentinel1Vvdb,
    embeddingNorm,
    weakLabelAggregate,
    eventFlag,
  };
}
