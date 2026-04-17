import { ChevronRight } from "lucide-react";
import type { LandPlot } from "../types";
import { cn } from "../lib/cn";

export function PlotSelector({
  plots,
  selectedId,
  onSelect,
  search,
}: {
  plots: LandPlot[];
  selectedId: string;
  onSelect: (p: LandPlot) => void;
  search: string;
}) {
  const q = search.trim().toLowerCase();
  const filtered = plots.filter(
    (p) =>
      !q ||
      p.tileId.toLowerCase().includes(q) ||
      p.region.toLowerCase().includes(q) ||
      p.id.toLowerCase().includes(q),
  );

  return (
    <div className="panel max-h-[420px] overflow-hidden flex flex-col">
      <div className="panel-header py-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Land plots
        </p>
        <span className="font-mono text-[10px] text-slate-600">
          {filtered.length} / {plots.length}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {filtered.map((p) => {
          const sel = p.id === selectedId;
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => onSelect(p)}
              className={cn(
                "mb-1 flex w-full items-center gap-2 rounded-lg border px-2 py-2 text-left transition",
                sel
                  ? "border-sky-700/60 bg-sky-950/30"
                  : "border-transparent hover:border-slate-800 hover:bg-obsidian-950/80",
              )}
            >
              <div className="min-w-0 flex-1">
                <p className="truncate font-mono text-[11px] text-sky-400/90">
                  {p.tileId}
                </p>
                <p className="truncate text-xs text-slate-400">{p.region}</p>
              </div>
              <ChevronRight
                className={cn(
                  "h-4 w-4 shrink-0 text-slate-600",
                  sel && "text-sky-400",
                )}
              />
            </button>
          );
        })}
      </div>
    </div>
  );
}
