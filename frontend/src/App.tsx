import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Sidebar } from "./layouts/Sidebar";
import { Topbar } from "./layouts/Topbar";
import { InsightsPanel } from "./components/InsightsPanel";
import { OverviewPage } from "./pages/OverviewPage";
import { EmbeddingMapPage } from "./pages/EmbeddingMapPage";
import { ChannelExplorerPage } from "./pages/ChannelExplorerPage";
import { ScatterPage } from "./pages/ScatterPage";
import { ClassifierPage } from "./pages/ClassifierPage";
import {
  useAefTiles,
  useChannelStats,
  useHealth,
  useTileSummary,
} from "./hooks/useAef";
import { API_BASE, IS_API_CONFIGURED } from "./lib/api";
import type { NavKey } from "./types/aef";

export default function App() {
  const [nav, setNav] = useState<NavKey>("overview");
  const health = useHealth();
  const trainTilesQ = useAefTiles("train");
  const testTilesQ = useAefTiles("test");

  const trainTiles = trainTilesQ.data ?? [];
  const testTiles = testTilesQ.data ?? [];
  const allTiles = useMemo(() => [...trainTiles, ...testTiles], [trainTiles, testTiles]);

  const [selectedTile, setSelectedTile] = useState<string | null>(null);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);

  useEffect(() => {
    if (selectedTile && allTiles.some((t) => t.tileId === selectedTile)) return;
    if (allTiles.length === 0) return;
    const first = allTiles[0];
    setSelectedTile(first.tileId);
    setSelectedYear(first.years[0] ?? null);
  }, [allTiles, selectedTile]);

  useEffect(() => {
    const tile = allTiles.find((t) => t.tileId === selectedTile);
    if (!tile) return;
    if (selectedYear === null || !tile.years.includes(selectedYear)) {
      setSelectedYear(tile.years[0] ?? null);
    }
  }, [selectedTile, selectedYear, allTiles]);

  const tileSplit = useMemo(() => {
    return allTiles.find((t) => t.tileId === selectedTile)?.split ?? "train";
  }, [allTiles, selectedTile]);

  const summary = useTileSummary(selectedTile, selectedYear, tileSplit);
  const stats = useChannelStats(
    nav === "channels" ? selectedTile : null,
    nav === "channels" ? selectedYear : null,
    tileSplit,
  );

  if (!IS_API_CONFIGURED) {
    return (
      <ConfigErrorPage message="VITE_API_BASE_URL is not configured. Set it in frontend/.env (e.g. VITE_API_BASE_URL=http://127.0.0.1:8011) and restart the dev server." />
    );
  }

  if (health.data?.status === "unreachable") {
    return (
      <ConfigErrorPage
        message={`Could not reach the FastAPI backend at ${API_BASE}. Start it with: cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8011`}
        onRetry={health.reload}
      />
    );
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-obsidian-950 text-slate-200">
      <Sidebar current={nav} onNavigate={setNav} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar health={health.data} loading={health.loading} />
        <div className="flex min-h-0 flex-1">
          <main className="min-w-0 flex-1 overflow-y-auto p-4 md:p-6">
            {trainTilesQ.error && (
              <div className="panel mb-4 border-rose-900/60 bg-rose-950/20 p-3 text-xs text-rose-200">
                {trainTilesQ.error}
              </div>
            )}
            {nav === "overview" && (
              <OverviewPage
                health={health.data}
                tiles={trainTiles}
                testTiles={testTiles}
                onNavigate={setNav}
              />
            )}
            {nav === "embedding-map" && (
              <EmbeddingMapPage
                tiles={allTiles}
                selectedTile={selectedTile}
                selectedYear={selectedYear}
                onTileChange={setSelectedTile}
                onYearChange={setSelectedYear}
                summary={summary.data}
              />
            )}
            {nav === "channels" && (
              <ChannelExplorerPage
                tiles={allTiles}
                selectedTile={selectedTile}
                selectedYear={selectedYear}
                onTileChange={setSelectedTile}
                onYearChange={setSelectedYear}
                channels={stats.data?.channels ?? []}
              />
            )}
            {nav === "scatter" && <ScatterPage tiles={trainTiles} />}
            {nav === "classifier" && (
              <ClassifierPage trainTiles={trainTiles} testTiles={testTiles} />
            )}
          </main>
          {(nav === "embedding-map" || nav === "channels") && (
            <aside className="hidden w-[320px] shrink-0 xl:block">
              <InsightsPanel
                health={health.data}
                tiles={allTiles}
                selectedTile={selectedTile}
                selectedYear={selectedYear}
                summary={summary.data}
                onSelectTile={setSelectedTile}
                onSelectYear={setSelectedYear}
              />
            </aside>
          )}
        </div>
      </div>
    </div>
  );
}

function ConfigErrorPage({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex h-screen w-full items-center justify-center bg-obsidian-950 text-slate-200">
      <div className="panel max-w-2xl p-6">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-xl border border-rose-900/60 bg-rose-950/30 text-rose-300">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">
              AlphaEarth Explorer is offline
            </h2>
            <p className="text-sm text-slate-400">
              The frontend talks to the FastAPI backend over HTTP — no proxy,
              no mock data.
            </p>
          </div>
        </div>
        <p className="mt-5 text-sm text-slate-400">{message}</p>
        <div className="mt-4 rounded-lg border border-slate-800 bg-obsidian-950/70 p-4 font-mono text-xs text-sky-300">
          VITE_API_BASE_URL=&lt;your-backend-url&gt;
        </div>
        {onRetry && (
          <button type="button" className="btn-primary mt-4 text-xs" onClick={onRetry}>
            <RefreshCw className="h-3.5 w-3.5" /> Retry
          </button>
        )}
      </div>
    </div>
  );
}
