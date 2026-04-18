import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, DatabaseZap } from "lucide-react";
import { Sidebar } from "./layouts/Sidebar";
import { Topbar } from "./layouts/Topbar";
import { InsightsPanel } from "./components/InsightsPanel";
import { OverviewPage } from "./pages/OverviewPage";
import { LandPlotsPage } from "./pages/LandPlotsPage";
import { TimeSeriesPage } from "./pages/TimeSeriesPage";
import { PredictionsPage } from "./pages/PredictionsPage";
import { RiskAnalysisPage } from "./pages/RiskAnalysisPage";
import { ValidationPage } from "./pages/ValidationPage";
import type { ActivityItem, LandPlot, LayerId, NavKey } from "./types";
import { regionMatches } from "./components/RegionFilter";
import { useBackendData, usePlotTimeseries } from "./hooks/useBackendData";

const DEFAULT_LAYERS: Record<LayerId, boolean> = {
  sentinel1: true,
  sentinel2: true,
  embeddings: true,
  weakLabels: true,
  predictions: true,
};

export default function App() {
  const { plots, source, health, loading, regions, error } = useBackendData();
  const [nav, setNav] = useState<NavKey>("overview");
  const [selectedPlotId, setSelectedPlotId] = useState("");
  const [search, setSearch] = useState("");
  const [region, setRegion] = useState<string>("all");
  const [layers, setLayers] = useState<Record<LayerId, boolean>>(DEFAULT_LAYERS);
  const [monitoringActive, setMonitoringActive] = useState(true);

  const selectedPlot = useMemo(
    () => plots.find((p) => p.id === selectedPlotId) ?? plots[0] ?? null,
    [plots, selectedPlotId],
  );

  const timeSeriesPoints = usePlotTimeseries(selectedPlot);

  const activityItems = useMemo(() => buildActivityFeed(plots), [plots]);

  const plotsForRegion = useMemo(
    () => plots.filter((p) => regionMatches(p.region, region)),
    [plots, region],
  );

  const selectPlot = (p: LandPlot) => {
    setSelectedPlotId(p.id);
  };

  const selectPlotById = (id: string) => {
    const p = plots.find((x) => x.id === id);
    if (p) setSelectedPlotId(p.id);
  };

  const onTileDropdown = (tileId: string) => {
    const p = plots.find((x) => x.tileId === tileId);
    if (p) setSelectedPlotId(p.id);
  };

  const toggleLayer = (id: LayerId) => {
    setLayers((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  useEffect(() => {
    if (plots.length && !plots.some((p) => p.id === selectedPlotId)) {
      setSelectedPlotId(plots[0].id);
    }
  }, [plots, selectedPlotId]);

  useEffect(() => {
    if (nav !== "plots") return;
    const filtered = plots.filter((p) => regionMatches(p.region, region));
    if (filtered.length > 0 && !filtered.some((p) => p.id === selectedPlotId)) {
      setSelectedPlotId(filtered[0].id);
    }
  }, [region, nav, selectedPlotId, plots]);

  const showInsights = nav !== "validation";

  if (!selectedPlot) {
    return (
      <div className="flex h-screen w-full overflow-hidden bg-obsidian-950 text-slate-200">
        <Sidebar current={nav} onNavigate={setNav} />
        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar
            search={search}
            onSearch={setSearch}
            tileValue=""
            onTileChange={() => undefined}
            monitoringActive={monitoringActive}
            onToggleMonitoring={() => setMonitoringActive((m) => !m)}
            tileOptions={[]}
            dataSource={source}
            apiLoading={loading}
            apiHealthy={health?.modelLoaded === true}
          />
          <main className="flex flex-1 items-center justify-center p-6">
            <div className="panel max-w-2xl p-6">
              <div className="flex items-center gap-3">
                <div className="grid h-11 w-11 place-items-center rounded-xl border border-rose-900/60 bg-rose-950/30 text-rose-300">
                  <DatabaseZap className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-white">
                    Live API data required
                  </h2>
                  <p className="text-sm text-slate-400">
                    The frontend is now API-only and will not fall back to mock plots.
                  </p>
                </div>
              </div>
              <div className="mt-5 space-y-3 text-sm text-slate-400">
                <p>
                  {error ??
                    "No plot payload was returned from the backend. Point the frontend to the running Jupyter backend URL and reload the app."}
                </p>
                <div className="rounded-lg border border-slate-800 bg-obsidian-950/70 p-4 font-mono text-xs text-sky-300">
                  VITE_API_BASE_URL=&lt;jupyter-backend-base-url&gt;
                </div>
                <div className="flex items-start gap-2 rounded-lg border border-amber-900/50 bg-amber-950/20 p-3 text-amber-200">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <p>
                    Local <code>localhost:8000</code> is no longer used as a hidden fallback.
                    The app will only render real API data once the configured backend is reachable.
                  </p>
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-obsidian-950 text-slate-200">
      <Sidebar current={nav} onNavigate={setNav} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          search={search}
          onSearch={setSearch}
          tileValue={selectedPlot.tileId}
          onTileChange={onTileDropdown}
          monitoringActive={monitoringActive}
          onToggleMonitoring={() => setMonitoringActive((m) => !m)}
          tileOptions={plots}
          dataSource={source}
          apiLoading={loading}
          apiHealthy={health?.modelLoaded === true}
        />
        <div className="flex min-h-0 flex-1">
          <main className="min-w-0 flex-1 overflow-y-auto p-4 md:p-6">
            {nav === "overview" && (
              <OverviewPage
                plots={plots}
                selectedPlot={selectedPlot}
                layers={layers}
                onToggleLayer={toggleLayer}
                onSelectPlot={selectPlot}
                onSelectPlotById={selectPlotById}
                previewTimeSeries={timeSeriesPoints}
                activityItems={activityItems}
              />
            )}
            {nav === "plots" && (
              <LandPlotsPage
                plots={plotsForRegion}
                selectedPlot={selectedPlot}
                region={region}
                onRegion={setRegion}
                search={search}
                layers={layers}
                onToggleLayer={toggleLayer}
                onSelectPlot={selectPlot}
                regionOptions={regions}
              />
            )}
            {nav === "timeseries" && (
              <TimeSeriesPage
                plots={plots}
                selectedPlot={selectedPlot}
                search={search}
                onSelectPlot={selectPlot}
                timeSeries={timeSeriesPoints}
              />
            )}
            {nav === "predictions" && (
              <PredictionsPage
                plots={plots}
                selectedPlot={selectedPlot}
                search={search}
                onSelectPlot={selectPlot}
              />
            )}
            {nav === "risk" && (
              <RiskAnalysisPage
                plots={plots}
                selectedPlot={selectedPlot}
                search={search}
                onSelectPlot={selectPlot}
              />
            )}
            {nav === "validation" && (
              <ValidationPage
                plots={plots}
                selectedPlot={selectedPlot}
                search={search}
                onSelectPlot={selectPlot}
                timeSeries={timeSeriesPoints}
              />
            )}
          </main>
          {showInsights && (
            <aside className="hidden w-[320px] shrink-0 xl:block">
              <InsightsPanel
                plot={selectedPlot}
                onNavigate={setNav}
                onSelectPlotFromFeed={selectPlotById}
                activityItems={activityItems}
              />
            </aside>
          )}
        </div>
      </div>
    </div>
  );
}

function buildActivityFeed(plots: LandPlot[]): ActivityItem[] {
  return [...plots]
    .sort((a, b) => b.prediction.confidence - a.prediction.confidence)
    .slice(0, 6)
    .map((plot, index) => ({
      id: `${plot.id}-activity`,
      type: plot.humanReviewNeeded
        ? "human_review"
        : plot.prediction.deforestationDetected
          ? "detection"
          : "risk_update",
      title: plot.prediction.deforestationDetected
        ? "API detection loaded"
        : "API tile state refreshed",
      detail: plot.prediction.notes,
      tileId: plot.tileId,
      plotId: plot.id,
      timestamp: new Date(Date.now() - index * 15 * 60 * 1000).toISOString(),
      severity:
        plot.eudrRiskTier === "critical"
          ? "critical"
          : plot.eudrRiskTier === "high"
            ? "warning"
            : "info",
    }));
}
