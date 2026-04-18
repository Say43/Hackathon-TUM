import { useCallback, useEffect, useMemo, useState } from "react";
import { LAND_PLOTS } from "../data/mock";
import type { LandPlot, TimeSeriesPoint } from "../types";
import { getTimeSeriesForPlot } from "../data/mock";
import { fetchHealth, fetchPlots, fetchTileTimeseries, normalizeLandPlot } from "../lib/api";

export type DataSource = "api" | "mock";

export function useBackendData() {
  const [plots, setPlots] = useState<LandPlot[]>(LAND_PLOTS);
  const [source, setSource] = useState<DataSource>("mock");
  const [health, setHealth] = useState<Awaited<
    ReturnType<typeof fetchHealth>
  > | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    const [h, data] = await Promise.all([fetchHealth(), fetchPlots()]);
    setHealth(h);
    if (data?.plots?.length) {
      try {
        const normalized = data.plots.map(normalizeLandPlot);
        setPlots(normalized);
        setSource("api");
      } catch {
        setPlots(LAND_PLOTS);
        setSource("mock");
      }
    } else {
      setPlots(LAND_PLOTS);
      setSource("mock");
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

  return { plots, source, health, loading, refresh, regions };
}

export function usePlotTimeseries(plot: LandPlot) {
  const [points, setPoints] = useState<TimeSeriesPoint[]>(() =>
    getTimeSeriesForPlot(plot.id),
  );

  useEffect(() => {
    let cancelled = false;
    setPoints(getTimeSeriesForPlot(plot.id));
    void fetchTileTimeseries(plot.tileId).then((apiPoints) => {
      if (!cancelled && apiPoints?.length) setPoints(apiPoints);
    });
    return () => {
      cancelled = true;
    };
  }, [plot.id, plot.tileId]);

  return points;
}
