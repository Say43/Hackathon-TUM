import { Boxes, Database, Layers, MapPin, Sparkles } from "lucide-react";
import type { AefTile, AefTileSummary, HealthResponse } from "../types/aef";

export function InsightsPanel({
  health,
  tiles,
  selectedTile,
  selectedYear,
  summary,
  onSelectTile,
  onSelectYear,
}: {
  health: HealthResponse | null;
  tiles: AefTile[];
  selectedTile: string | null;
  selectedYear: number | null;
  summary: AefTileSummary | null;
  onSelectTile: (tileId: string) => void;
  onSelectYear: (year: number) => void;
}) {
  const tile = tiles.find((t) => t.tileId === selectedTile);
  return (
    <div className="flex h-full w-full flex-col overflow-y-auto border-l border-slate-800/80 bg-obsidian-950/40">
      <div className="border-b border-slate-800/80 p-4">
        <p className="label-upper">Selected tile</p>
        <p className="mt-1 font-mono text-sm font-semibold text-sky-300">
          {selectedTile ?? "—"}
        </p>
        <div className="mt-3 flex flex-wrap gap-1.5 text-[11px]">
          <Tag tone="violet" icon={<Sparkles className="h-3 w-3" />}>
            AEF · 64-band
          </Tag>
          {tile?.hasLabels ? (
            <Tag tone="emerald">
              {tile.labelSources.join(" · ")}
            </Tag>
          ) : (
            <Tag tone="slate">no labels</Tag>
          )}
          {tile?.years.length ? (
            <Tag tone="sky">{tile.years.length} years</Tag>
          ) : null}
        </div>
        {tile?.years.length ? (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {tile.years.map((y) => (
              <button
                key={y}
                type="button"
                onClick={() => onSelectYear(y)}
                className={`rounded-md border px-2 py-1 font-mono text-[11px] ${
                  y === selectedYear
                    ? "border-sky-500 bg-sky-600/20 text-sky-200"
                    : "border-slate-700 bg-obsidian-900 text-slate-400 hover:bg-obsidian-800"
                }`}
              >
                {y}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      <div className="border-b border-slate-800/80 p-4">
        <p className="label-upper">Tiles available</p>
        <ul className="mt-2 space-y-1">
          {tiles.map((t) => (
            <li key={t.tileId}>
              <button
                type="button"
                onClick={() => onSelectTile(t.tileId)}
                className={`flex w-full items-center justify-between rounded-md border px-2 py-1.5 text-xs ${
                  t.tileId === selectedTile
                    ? "border-sky-700/60 bg-sky-950/30 text-sky-200"
                    : "border-slate-800 bg-obsidian-900/40 text-slate-400 hover:bg-obsidian-900"
                }`}
              >
                <span className="font-mono">{t.tileId}</span>
                <span className="text-[10px] text-slate-500">
                  {t.years.length} yrs
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>

      {summary && (
        <div className="border-b border-slate-800/80 p-4">
          <p className="label-upper">Tile geometry</p>
          <Stat
            icon={<Layers className="h-3 w-3" />}
            label="Shape"
            value={`${summary.height} × ${summary.width} × ${summary.bands}`}
          />
          <Stat
            icon={<MapPin className="h-3 w-3" />}
            label="Centroid"
            value={`${((summary.bbox.minLat + summary.bbox.maxLat) / 2).toFixed(4)}°, ${((summary.bbox.minLon + summary.bbox.maxLon) / 2).toFixed(4)}°`}
          />
          {Object.entries(summary.labelCounts).map(([source, c]) => (
            <Stat
              key={source}
              icon={<Boxes className="h-3 w-3" />}
              label={`${source} positives`}
              value={`${c.positive.toLocaleString()} / ${(c.positive + c.negative).toLocaleString()}`}
            />
          ))}
        </div>
      )}

      <div className="mt-auto border-t border-slate-800/80 p-4 text-[11px] text-slate-500">
        <div className="flex items-center gap-2">
          <Database className="h-3 w-3" />
          <span>{health?.cacheDir || "cache: ?"}</span>
        </div>
        <p className="mt-1">
          {health?.datasetPresent
            ? "Dataset reachable"
            : "Dataset missing — check /api/debug/paths"}
        </p>
      </div>
    </div>
  );
}

function Stat({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="mt-2 rounded-md border border-slate-800 bg-obsidian-900/60 px-2 py-1.5">
      <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase text-slate-500">
        {icon}
        {label}
      </div>
      <p className="mt-0.5 font-mono text-xs text-slate-200">{value}</p>
    </div>
  );
}

function Tag({
  tone,
  icon,
  children,
}: {
  tone: "violet" | "emerald" | "slate" | "sky";
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  const TONE: Record<string, string> = {
    violet: "border-violet-700/60 bg-violet-950/30 text-violet-200",
    emerald: "border-emerald-700/60 bg-emerald-950/30 text-emerald-200",
    sky: "border-sky-700/60 bg-sky-950/30 text-sky-200",
    slate: "border-slate-700 bg-obsidian-900 text-slate-400",
  };
  return (
    <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 ${TONE[tone]}`}>
      {icon}
      {children}
    </span>
  );
}
