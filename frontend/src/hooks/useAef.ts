import { useCallback, useEffect, useState } from "react";
import {
  fetchClassifierRun,
  fetchHealth,
  fetchMislabels,
  fetchScatter,
  listTiles,
  postClassify,
  tileChannelStats,
  tileSummary,
} from "../lib/api";
import type {
  AefChannelStatsResponse,
  AefTile,
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

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

const idle = <T>(): AsyncState<T> => ({ data: null, loading: false, error: null });

function describeError(err: unknown): string {
  if (err instanceof Error) return err.message;
  return String(err);
}

export function useHealth(): AsyncState<HealthResponse> & { reload: () => void } {
  const [state, setState] = useState<AsyncState<HealthResponse>>({
    ...idle<HealthResponse>(),
    loading: true,
  });
  const reload = useCallback(() => {
    setState((s) => ({ ...s, loading: true }));
    fetchHealth()
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((err) => setState({ data: null, loading: false, error: describeError(err) }));
  }, []);
  useEffect(() => {
    reload();
  }, [reload]);
  return { ...state, reload };
}

export function useAefTiles(split: Split): AsyncState<AefTile[]> & { reload: () => void } {
  const [state, setState] = useState<AsyncState<AefTile[]>>({
    ...idle<AefTile[]>(),
    loading: true,
  });
  const reload = useCallback(() => {
    setState((s) => ({ ...s, loading: true }));
    listTiles(split)
      .then((res) => setState({ data: res.tiles, loading: false, error: null }))
      .catch((err) => setState({ data: null, loading: false, error: describeError(err) }));
  }, [split]);
  useEffect(() => {
    reload();
  }, [reload]);
  return { ...state, reload };
}

export function useTileSummary(
  tile: string | null,
  year: number | null,
  split: Split,
): AsyncState<AefTileSummary> {
  const [state, setState] = useState<AsyncState<AefTileSummary>>(idle());
  useEffect(() => {
    if (!tile || year === null) {
      setState(idle());
      return;
    }
    setState({ data: null, loading: true, error: null });
    let cancelled = false;
    tileSummary(tile, year, split)
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((err) => {
        if (!cancelled)
          setState({ data: null, loading: false, error: describeError(err) });
      });
    return () => {
      cancelled = true;
    };
  }, [tile, year, split]);
  return state;
}

export function useChannelStats(
  tile: string | null,
  year: number | null,
  split: Split,
): AsyncState<AefChannelStatsResponse> {
  const [state, setState] = useState<AsyncState<AefChannelStatsResponse>>(idle());
  useEffect(() => {
    if (!tile || year === null) {
      setState(idle());
      return;
    }
    setState({ data: null, loading: true, error: null });
    let cancelled = false;
    tileChannelStats(tile, year, split)
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((err) => {
        if (!cancelled)
          setState({ data: null, loading: false, error: describeError(err) });
      });
    return () => {
      cancelled = true;
    };
  }, [tile, year, split]);
  return state;
}

export interface ScatterParams {
  method: ScatterMethod;
  tiles: string[];
  labelSource: LabelSource;
  samplePerTile: number;
}

export function useScatter(
  params: ScatterParams | null,
): AsyncState<ScatterResponse> & { run: (p: ScatterParams) => void } {
  const [state, setState] = useState<AsyncState<ScatterResponse>>(idle());

  const run = useCallback((p: ScatterParams) => {
    setState({ data: null, loading: true, error: null });
    fetchScatter(p)
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((err) => setState({ data: null, loading: false, error: describeError(err) }));
  }, []);

  useEffect(() => {
    if (params) run(params);
    // run a scatter automatically only when explicitly initialised
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { ...state, run };
}

export interface ClassifierState extends AsyncState<ClassifierRunResponse> {
  run: (body: ClassifyRequestBody) => Promise<ClassifierRunResponse | null>;
}

export function useClassifier(): ClassifierState {
  const [state, setState] = useState<AsyncState<ClassifierRunResponse>>(idle());
  const run = useCallback(async (body: ClassifyRequestBody) => {
    setState({ data: null, loading: true, error: null });
    try {
      const data = await postClassify(body);
      setState({ data, loading: false, error: null });
      return data;
    } catch (err) {
      setState({ data: null, loading: false, error: describeError(err) });
      return null;
    }
  }, []);
  return { ...state, run };
}

export function useMislabels(
  modelId: string | null,
  top: number,
): AsyncState<MislabelResponse> & { reload: () => void } {
  const [state, setState] = useState<AsyncState<MislabelResponse>>(idle());
  const reload = useCallback(() => {
    if (!modelId) {
      setState(idle());
      return;
    }
    setState({ data: null, loading: true, error: null });
    fetchMislabels(modelId, top)
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((err) => setState({ data: null, loading: false, error: describeError(err) }));
  }, [modelId, top]);
  useEffect(() => {
    reload();
  }, [reload]);
  return { ...state, reload };
}

export function useClassifierLookup(
  modelId: string | null,
): AsyncState<ClassifierRunResponse> {
  const [state, setState] = useState<AsyncState<ClassifierRunResponse>>(idle());
  useEffect(() => {
    if (!modelId) {
      setState(idle());
      return;
    }
    setState({ data: null, loading: true, error: null });
    let cancelled = false;
    fetchClassifierRun(modelId)
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((err) => {
        if (!cancelled)
          setState({ data: null, loading: false, error: describeError(err) });
      });
    return () => {
      cancelled = true;
    };
  }, [modelId]);
  return state;
}
