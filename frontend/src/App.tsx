import { useEffect, useMemo, useState } from "react";
import { Sidebar } from "./layouts/Sidebar";
import { Topbar } from "./layouts/Topbar";
import { InsightsPanel } from "./components/InsightsPanel";
import { OverviewPage } from "./pages/OverviewPage";
import { LandPlotsPage } from "./pages/LandPlotsPage";
import { TimeSeriesPage } from "./pages/TimeSeriesPage";
import { PredictionsPage } from "./pages/PredictionsPage";
import { RiskAnalysisPage } from "./pages/RiskAnalysisPage";
import { ValidationPage } from "./pages/ValidationPage";
import { LAND_PLOTS } from "./data/mock";
import type { LayerId, NavKey } from "./types";
import { regionMatches } from "./components/RegionFilter";

const DEFAULT_LAYERS: Record<LayerId, boolean> = {
  sentinel1: true,
  sentinel2: true,
  embeddings: true,
  weakLabels: true,
  predictions: true,
};

export default function App() {
  const [nav, setNav] = useState<NavKey>("overview");
  const [selectedPlotId, setSelectedPlotId] = useState(LAND_PLOTS[0].id);
  const [search, setSearch] = useState("");
  const [region, setRegion] = useState<string>("all");
  const [layers, setLayers] = useState<Record<LayerId, boolean>>(DEFAULT_LAYERS);
  const [monitoringActive, setMonitoringActive] = useState(true);

  const selectedPlot = useMemo(
    () => LAND_PLOTS.find((p) => p.id === selectedPlotId) ?? LAND_PLOTS[0],
    [selectedPlotId],
  );

  const plotsForRegion = useMemo(
    () => LAND_PLOTS.filter((p) => regionMatches(p.region, region)),
    [region],
  );

  const selectPlot = (p: (typeof LAND_PLOTS)[0]) => {
    setSelectedPlotId(p.id);
  };

  const selectPlotById = (id: string) => {
    const p = LAND_PLOTS.find((x) => x.id === id);
    if (p) setSelectedPlotId(p.id);
  };

  const onTileDropdown = (tileId: string) => {
    const p = LAND_PLOTS.find((x) => x.tileId === tileId);
    if (p) setSelectedPlotId(p.id);
  };

  const toggleLayer = (id: LayerId) => {
    setLayers((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  useEffect(() => {
    if (nav !== "plots") return;
    const filtered = LAND_PLOTS.filter((p) => regionMatches(p.region, region));
    if (
      filtered.length > 0 &&
      !filtered.some((p) => p.id === selectedPlotId)
    ) {
      setSelectedPlotId(filtered[0].id);
    }
  }, [region, nav, selectedPlotId]);

  const showInsights = nav !== "validation";

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
        />
        <div className="flex min-h-0 flex-1">
          <main className="min-w-0 flex-1 overflow-y-auto p-4 md:p-6">
            {nav === "overview" && (
              <OverviewPage
                plots={LAND_PLOTS}
                selectedPlot={selectedPlot}
                layers={layers}
                onToggleLayer={toggleLayer}
                onSelectPlot={selectPlot}
                onSelectPlotById={selectPlotById}
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
              />
            )}
            {nav === "timeseries" && (
              <TimeSeriesPage
                plots={LAND_PLOTS}
                selectedPlot={selectedPlot}
                search={search}
                onSelectPlot={selectPlot}
              />
            )}
            {nav === "predictions" && (
              <PredictionsPage
                plots={LAND_PLOTS}
                selectedPlot={selectedPlot}
                search={search}
                onSelectPlot={selectPlot}
              />
            )}
            {nav === "risk" && (
              <RiskAnalysisPage
                plots={LAND_PLOTS}
                selectedPlot={selectedPlot}
                search={search}
                onSelectPlot={selectPlot}
              />
            )}
            {nav === "validation" && (
              <ValidationPage
                plots={LAND_PLOTS}
                selectedPlot={selectedPlot}
                search={search}
                onSelectPlot={selectPlot}
              />
            )}
          </main>
          {showInsights && (
            <aside className="hidden w-[320px] shrink-0 xl:block">
              <InsightsPanel
                plot={selectedPlot}
                onNavigate={setNav}
                onSelectPlotFromFeed={selectPlotById}
              />
            </aside>
          )}
        </div>
      </div>
    </div>
  );
}
