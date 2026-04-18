export type NavKey =
  | "overview"
  | "plots"
  | "timeseries"
  | "predictions"
  | "risk"
  | "validation";

export type ReviewStatus = "pending" | "queued" | "reviewed" | "escalated";

export type RiskTier = "low" | "medium" | "high" | "critical";

export type LabelAgreement = "agreement" | "conflict" | "uncertain";

export type WeakLabelClass = "deforestation" | "stable" | "uncertain";

export interface MapOverlayRegion {
  id: string;
  kind: "predicted_change" | "weak_hint" | "water" | "stable_forest";
  label: string;
  /** Normalized 0–100 for demo positioning inside map panel */
  x: number;
  y: number;
  w: number;
  h: number;
  opacity: number;
  color: string;
}

export interface WeakLabelSource {
  labelSource: string;
  label: WeakLabelClass;
  confidence: number;
  acquisitionMonth?: string;
}

export interface ModelPrediction {
  deforestationDetected: boolean;
  confidence: number;
  eventMonth: string;
  modelVersion: string;
  notes: string;
  labelAgreement: LabelAgreement;
}

export interface LandPlot {
  id: string;
  tileId: string;
  region: string;
  country: string;
  areaHa: number;
  forestCoverPct: number;
  centroidLat: number;
  centroidLng: number;
  prediction: ModelPrediction;
  weakLabels: WeakLabelSource[];
  riskScore: number;
  eudrRiskTier: RiskTier;
  reviewStatus: ReviewStatus;
  signalStrength: number;
  labelConsistency: number;
  temporalConsistency: number;
  regionAnomalyRisk: number;
  evidenceCompleteness: number;
  dataQualityConfidence: number;
  humanReviewNeeded: boolean;
  complianceRelevance: "high" | "medium" | "low";
  overlays: MapOverlayRegion[];
  changeWindowStart: string;
  changeWindowEnd: string;
  /** Downsampled model emphasis grid from API (optional). */
  heatmap?: number[][];
  /** `model` live inference or `cached_raster` from pred GeoTIFF. */
  apiSource?: string;
}

export interface TimeSeriesPoint {
  month: string;
  sentinel2Ndvi: number;
  sentinel1Vvdb: number;
  embeddingNorm: number;
  weakLabelAggregate: number;
  eventFlag?: boolean;
}

export interface ActivityItem {
  id: string;
  type:
    | "flagged"
    | "label_conflict"
    | "confidence_shift"
    | "human_review"
    | "risk_update"
    | "detection";
  title: string;
  detail: string;
  tileId?: string;
  plotId?: string;
  timestamp: string;
  severity: "info" | "warning" | "critical";
}

export interface ValidationQueueEntry {
  id: string;
  plotId: string;
  tileId: string;
  region: string;
  priority: number;
  reason: string;
  queuedAt: string;
}

export type LayerId =
  | "sentinel1"
  | "sentinel2"
  | "embeddings"
  | "weakLabels"
  | "predictions";
