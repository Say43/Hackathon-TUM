import { useEffect, useMemo, useState } from "react";
import { Loader2, Play } from "lucide-react";
import {
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { fetchScatter } from "../lib/api";
import type {
  AefTile,
  LabelSource,
  ScatterPoint,
  ScatterResponse,
} from "../types/aef";

const LABEL_SOURCES: LabelSource[] = ["gladl", "glads2", "radd"];

interface AsyncSlot {
  loading: boolean;
  error: string | null;
  data: ScatterResponse | null;
}

const empty: AsyncSlot = { loading: false, error: null, data: null };

export function ScatterPage({ tiles }: { tiles: AefTile[] }) {
  const trainTiles = useMemo(() => tiles.filter((t) => t.hasLabels), [tiles]);
  const [selected, setSelected] = useState<string[]>([]);
  const [labelSource, setLabelSource] = useState<LabelSource>("gladl");
  const [sample, setSample] = useState(2000);
  const [pca, setPca] = useState<AsyncSlot>(empty);
  const [umap, setUmap] = useState<AsyncSlot>(empty);

  useEffect(() => {
    if (selected.length === 0 && trainTiles.length > 0) {
      const first = trainTiles[0];
      const lastTwoYears = first.years.slice(-2);
      setSelected(lastTwoYears.map((y) => `${first.tileId}:${y}:${first.split}`));
    }
  }, [trainTiles, selected.length]);

  const allTileYears = useMemo(() => {
    const out: { key: string; tile: string; year: number; split: string }[] = [];
    for (const t of trainTiles) {
      for (const y of t.years) {
        out.push({ key: `${t.tileId}:${y}:${t.split}`, tile: t.tileId, year: y, split: t.split });
      }
    }
    return out;
  }, [trainTiles]);

  const toggle = (key: string) =>
    setSelected((cur) =>
      cur.includes(key) ? cur.filter((k) => k !== key) : [...cur, key],
    );

  const run = async () => {
    if (selected.length === 0) return;
    setPca({ loading: true, error: null, data: null });
    setUmap({ loading: true, error: null, data: null });
    fetchScatter({
      method: "pca",
      tiles: selected,
      labelSource,
      samplePerTile: sample,
    })
      .then((data) => setPca({ loading: false, error: null, data }))
      .catch((err) => setPca({ loading: false, error: String(err), data: null }));
    fetchScatter({
      method: "umap",
      tiles: selected,
      labelSource,
      samplePerTile: sample,
    })
      .then((data) => setUmap({ loading: false, error: null, data }))
      .catch((err) => setUmap({ loading: false, error: String(err), data: null }));
  };

  return (
    <div className="space-y-4">
      <section className="panel p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <p className="label-upper">Label source</p>
            <select
              value={labelSource}
              onChange={(e) => setLabelSource(e.target.value as LabelSource)}
              className="input mt-1 w-32 py-1 font-mono text-xs"
            >
              {LABEL_SOURCES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <p className="label-upper">Pixels / tile</p>
            <input
              type="number"
              min={200}
              max={10000}
              step={200}
              value={sample}
              onChange={(e) => setSample(Number(e.target.value))}
              className="input mt-1 w-28 py-1 font-mono text-xs"
            />
          </div>
          <button
            type="button"
            className="btn-primary text-xs"
            onClick={run}
            disabled={pca.loading || umap.loading || selected.length === 0}
          >
            {pca.loading || umap.loading ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Computing
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5" /> Run scatter
              </>
            )}
          </button>
          <p className="ml-auto text-[11px] text-slate-500">
            Cached on the backend after the first run.
          </p>
        </div>
        <div className="mt-3">
          <p className="label-upper">Tiles included ({selected.length})</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {allTileYears.map((ty) => {
              const active = selected.includes(ty.key);
              return (
                <button
                  key={ty.key}
                  type="button"
                  onClick={() => toggle(ty.key)}
                  className={`rounded-md border px-2 py-1 font-mono text-[11px] ${
                    active
                      ? "border-sky-500 bg-sky-600/20 text-sky-200"
                      : "border-slate-700 bg-obsidian-900 text-slate-400 hover:bg-obsidian-800"
                  }`}
                >
                  {ty.tile}:{ty.year}
                </button>
              );
            })}
            {allTileYears.length === 0 && (
              <p className="text-xs text-slate-500">No labelled tiles available.</p>
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <ScatterPanel title="PCA-2D" slot={pca} />
        <ScatterPanel title="UMAP-2D" slot={umap} />
      </section>
    </div>
  );
}

function ScatterPanel({ title, slot }: { title: string; slot: AsyncSlot }) {
  const points = slot.data?.points ?? [];
  const positives = points.filter((p) => p.label === 1);
  const negatives = points.filter((p) => p.label === 0);
  return (
    <div className="panel p-4">
      <div className="flex items-center justify-between">
        <p className="label-upper">{title}</p>
        <span className="text-[11px] text-slate-500">
          {slot.data ? `${points.length.toLocaleString()} pts` : ""}
        </span>
      </div>
      {slot.error ? (
        <p className="mt-3 text-sm text-rose-300">{slot.error}</p>
      ) : slot.loading ? (
        <div className="mt-6 flex h-72 items-center justify-center text-slate-500">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      ) : points.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">
          No scatter computed yet — pick tiles + a label source and press Run.
        </p>
      ) : (
        <div className="mt-2 h-80">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart
              margin={{ top: 8, right: 12, bottom: 8, left: 12 }}
            >
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
              <XAxis
                type="number"
                dataKey="x"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                stroke="#334155"
                name="x"
              />
              <YAxis
                type="number"
                dataKey="y"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                stroke="#334155"
                name="y"
              />
              <ZAxis range={[12, 12]} />
              <Tooltip
                cursor={{ stroke: "#475569" }}
                contentStyle={{
                  background: "#0b1220",
                  border: "1px solid #1e293b",
                  fontSize: 11,
                }}
                formatter={(value: ScatterPoint["x"]) => Number(value).toFixed(3)}
                labelFormatter={() => ""}
              />
              <Legend wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />
              <Scatter
                name="No alert"
                data={negatives}
                fill="#10b981"
                opacity={0.7}
              />
              <Scatter
                name="Alert"
                data={positives}
                fill="#ef4444"
                opacity={0.85}
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
