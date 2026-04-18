import { useCallback, useEffect, useMemo, useState } from "react";
import type { LandPlot, TimeSeriesPoint } from "../types";
import {
  API_BASE,
  IS_API_CONFIGURED,
  fetchHealth,
  fetchPlots,
  fetchTileTimeseries,
  normalizeLandPlot,
} from "../lib/api";

export type DataSource = "api" | "unavailable";

const UNCONFIGURED_MSG =
  "VITE_API_BASE_URL is not set. Configure it in frontend/.env to the Jupyter backend URL and restart the dev server.";

export function useBackendData() {
  const [plots, setPlots] = useState<LandPlot[]>([]);
  const [source, setSource] = useState<DataSource>("unavailable");
  const [health, setHealth] = useState<Awaited<
    ReturnType<typeof fetchHealth>
  > | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(
    IS_API_CONFIGURED ? null : UNCONFIGURED_MSG,
  );

  const refresh = useCallback(async () => {
    if (!IS_API_CONFIGURED) {
      setPlots([]);
      setSource("unavailable");
      setHealth(null);
      setError(UNCONFIGURED_MSG);
      setLoading(false);
      return;
    }

    setLoading(true);
    const [h, data] = await Promise.all([fetchHealth(), fetchPlots()]);
    setHealth(h);
    if (data?.plots?.length) {
      try {
        const normalized = data.plots.map(normalizeLandPlot);
        setPlots(normalized);
        setSource("api");
        setError(null);
      } catch {
        setPlots([]);
        setSource("unavailable");
        setError(
          "The API returned plot data, but the payload could not be normalized.",
        );
      }
    } else {
      setPlots([]);
      setSource("unavailable");
      setError(
        h?.error ??
          `No live API plot data was returned from ${API_BASE}. Make sure the Jupyter backend is reachable from the frontend.`,
      );
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const regions = useMemo(
    () => [...new Set(plots.map((p) => p.region))].sort(),
    [plots],
  );

  return { plots, source, health, loading, refresh, regions, error };
}

export function usePlotTimeseries(plot: LandPlot | null) {
  const [points, setPoints] = useState<TimeSeriesPoint[]>([]);

  useEffect(() => {
    if (!plot) {
      setPoints([]);
      return;
    }
    let cancelled = false;
    setPoints([]);
    void fetchTileTimeseries(plot.tileId).then((apiPoints) => {
      if (!cancelled && apiPoints?.length) setPoints(apiPoints);
    });
    return () => {
      cancelled = true;
    };
  }, [plot?.id, plot?.tileId]);

  return points;
}
