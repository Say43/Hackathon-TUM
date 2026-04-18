export type LabelSource = "gladl" | "glads2" | "radd";
export type Split = "train" | "test";
export type ScatterMethod = "pca" | "umap";
export type ClassifierKind = "svm" | "mlp";

export type NavKey =
  | "overview"
  | "embedding-map"
  | "channels"
  | "scatter"
  | "classifier";

export interface BBox {
  minLon: number;
  minLat: number;
  maxLon: number;
  maxLat: number;
}

export interface AefTile {
  tileId: string;
  split: Split;
  years: number[];
  hasLabels: boolean;
  labelSources: LabelSource[];
  bbox: BBox | null;
  centroid: { lon: number; lat: number } | null;
  originSrid?: string | null;
}

export interface AefTileSummary {
  tileId: string;
  year: number;
  split: Split;
  bands: number;
  height: number;
  width: number;
  bbox: BBox;
  labelCounts: Record<
    LabelSource,
    {
      valid: number;
      positive: number;
      negative: number;
      height: number;
      width: number;
    }
  >;
}

export interface AefChannelStat {
  dim: number;
  min: number | null;
  max: number | null;
  mean: number | null;
  std: number | null;
  validFraction: number;
}

export interface AefChannelStatsResponse {
  tileId: string;
  year: number;
  split: Split;
  channels: AefChannelStat[];
}

export interface ScatterPoint {
  x: number;
  y: number;
  label: 0 | 1;
  tile: string;
}

export interface ScatterResponse {
  method: ScatterMethod;
  labelSource: LabelSource;
  points: ScatterPoint[];
  samples: number;
  tilesUsed: string[];
}

export interface ClassifierMetrics {
  supported: boolean;
  reason?: string;
  samples?: number;
  precision?: number;
  recall?: number;
  f1?: number;
  rocAuc?: number;
  confusion?: { tn: number; fp: number; fn: number; tp: number };
}

export interface ClassifierRunResponse {
  modelId: string;
  request: Record<string, unknown>;
  trainSamples: number;
  trainPositive: number;
  valMetrics: ClassifierMetrics | null;
  testMetrics: ClassifierMetrics;
  tile: {
    id: string;
    year: number;
    split: Split;
    height: number;
    width: number;
  };
  fromCache: boolean;
}

export interface MislabelRegion {
  id: number;
  areaPixels: number;
  labelClass: 0 | 1;
  predictedClass: 0 | 1;
  meanConfidence: number;
  score: number;
  bbox: BBox;
  centroid: { lon: number; lat: number };
}

export interface MislabelResponse {
  modelId: string;
  regions: MislabelRegion[];
  top: number;
}

export interface AefTileListResponse {
  split: Split;
  count: number;
  tiles: AefTile[];
}

export interface HealthResponse {
  status: string;
  dataDir: string | null;
  datasetPresent: boolean;
  aefDirPresent: boolean;
  labelsDirPresent: boolean;
  cacheDir: string;
  cacheDirPresent: boolean;
  labelSources: LabelSource[];
  error?: string | null;
}

export interface ClassifyRequestBody {
  model: ClassifierKind;
  train_tiles: string[];
  val_tile?: string | null;
  test_tile: string;
  label_source: LabelSource;
  sample_per_tile?: number;
  refresh?: boolean;
}
