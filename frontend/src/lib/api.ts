/**
 * Strict API client for the AlphaEarth Explorer backend.
 *
 * The frontend talks ONLY to the URL in `VITE_API_BASE_URL` — no proxy, no
 * silent fallback. If the env is unset or the backend is unreachable, every
 * call throws an `ApiError` so the UI can render a clear message instead of
 * pretending data exists.
 */

import type {
  AefChannelStatsResponse,
  AefTileListResponse,
  AefTileSummary,
  ClassifierRunResponse,
  ClassifyRequestBody,
  HealthResponse,
  LabelSource,
  MislabelResponse,
  ScatterMethod,
  ScatterResponse,
  Split,
} from "../types/aef";

const RAW_API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").trim();
export const API_BASE = RAW_API_BASE.replace(/\/+$/, "");
export const IS_API_CONFIGURED = API_BASE.length > 0;

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

function ensureConfigured() {
  if (!IS_API_CONFIGURED) {
    throw new ApiError(
      "VITE_API_BASE_URL is not configured. Set it in frontend/.env and restart the dev server.",
    );
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  ensureConfigured();
  const url = `${API_BASE}${path}`;
  let response: Response;
  try {
    response = await fetch(url, init);
  } catch (err) {
    throw new ApiError(
      `Could not reach the backend at ${API_BASE}. Is the FastAPI server running?`,
      err,
    );
  }
  if (!response.ok) {
    let detail = "";
    try {
      const body = await response.json();
      detail = (body as { detail?: string })?.detail ?? "";
    } catch {
      detail = await response.text().catch(() => "");
    }
    throw new ApiError(
      `Backend ${response.status} ${response.statusText}: ${detail || path}`,
      undefined,
      response.status,
    );
  }
  return (await response.json()) as T;
}

export function imageUrl(path: string): string {
  ensureConfigured();
  return `${API_BASE}${path}`;
}

export async function fetchHealth(): Promise<HealthResponse> {
  try {
    return await request<HealthResponse>("/api/health");
  } catch (err) {
    if (err instanceof ApiError) {
      return {
        status: "unreachable",
        dataDir: null,
        datasetPresent: false,
        aefDirPresent: false,
        labelsDirPresent: false,
        cacheDir: "",
        cacheDirPresent: false,
        labelSources: [],
        error: err.message,
      };
    }
    throw err;
  }
}

export function listTiles(split: Split = "train"): Promise<AefTileListResponse> {
  return request(`/api/aef/tiles?split=${split}`);
}

export function tileSummary(
  tile: string,
  year: number,
  split: Split = "train",
): Promise<AefTileSummary> {
  return request(`/api/aef/tiles/${encodeURIComponent(tile)}/${year}/summary?split=${split}`);
}

export function tileChannelStats(
  tile: string,
  year: number,
  split: Split = "train",
): Promise<AefChannelStatsResponse> {
  return request(`/api/aef/tiles/${encodeURIComponent(tile)}/${year}/stats?split=${split}`);
}

export function previewUrl(tile: string, year: number, split: Split = "train"): string {
  return imageUrl(
    `/api/aef/tiles/${encodeURIComponent(tile)}/${year}/preview.png?split=${split}`,
  );
}

export function bandsUrl(
  tile: string,
  year: number,
  bands: { r: number; g: number; b: number },
  mode: "rgb" | "gray",
  split: Split = "train",
): string {
  const params = new URLSearchParams({
    split,
    mode,
    r: String(bands.r),
    g: String(bands.g),
    b: String(bands.b),
  });
  return imageUrl(
    `/api/aef/tiles/${encodeURIComponent(tile)}/${year}/bands.png?${params.toString()}`,
  );
}

export function fetchScatter(args: {
  method: ScatterMethod;
  tiles: string[];
  labelSource: LabelSource;
  samplePerTile?: number;
}): Promise<ScatterResponse> {
  const params = new URLSearchParams({
    method: args.method,
    tiles: args.tiles.join(","),
    label_source: args.labelSource,
  });
  if (args.samplePerTile !== undefined) {
    params.set("sample_per_tile", String(args.samplePerTile));
  }
  return request(`/api/aef/scatter?${params.toString()}`);
}

export function postClassify(body: ClassifyRequestBody): Promise<ClassifierRunResponse> {
  return request(`/api/aef/classify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function fetchClassifierRun(modelId: string): Promise<ClassifierRunResponse> {
  return request(`/api/aef/classify/${encodeURIComponent(modelId)}`);
}

export function classifierPredictionUrl(modelId: string): string {
  return imageUrl(`/api/aef/classify/${encodeURIComponent(modelId)}/prediction.png`);
}

export function classifierProbabilityUrl(modelId: string): string {
  return imageUrl(`/api/aef/classify/${encodeURIComponent(modelId)}/probability.png`);
}

export function fetchMislabels(
  modelId: string,
  top = 20,
): Promise<MislabelResponse> {
  return request(
    `/api/aef/classify/${encodeURIComponent(modelId)}/mislabels?top=${top}`,
  );
}
