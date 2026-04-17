import {
  Activity,
  BarChart3,
  CheckSquare,
  Globe2,
  LayoutDashboard,
  LineChart,
  Radar,
  Satellite,
} from "lucide-react";
import type { NavKey } from "../types";
import { cn } from "../lib/cn";

const NAV: { id: NavKey; label: string; Icon: typeof LayoutDashboard }[] = [
  { id: "overview", label: "Overview", Icon: LayoutDashboard },
  { id: "plots", label: "Land Plots", Icon: Globe2 },
  { id: "timeseries", label: "Time Series", Icon: LineChart },
  { id: "predictions", label: "Predictions", Icon: Satellite },
  { id: "risk", label: "Risk Analysis", Icon: BarChart3 },
  { id: "validation", label: "Validation", Icon: CheckSquare },
];

export function Sidebar({
  current,
  onNavigate,
}: {
  current: NavKey;
  onNavigate: (k: NavKey) => void;
}) {
  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-slate-800/80 bg-obsidian-900/95">
      <div className="flex items-center gap-2 border-b border-slate-800/80 px-4 py-4">
        <div className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-sky-600 to-slate-900 text-white shadow-glow">
          <Radar className="h-5 w-5" />
        </div>
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
            osapiens
          </p>
          <p className="text-sm font-semibold text-white">EO Monitor</p>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 p-2">
        <p className="px-2 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
          Workspace
        </p>
        {NAV.map((item) => {
          const Icon = item.Icon;
          const active = item.id === current;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              className={cn(
                "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition",
                active
                  ? "bg-sky-600/15 text-sky-200"
                  : "text-slate-400 hover:bg-obsidian-800 hover:text-slate-200",
              )}
            >
              <Icon
                className={cn(
                  "h-4 w-4",
                  active ? "text-sky-400" : "text-slate-500",
                )}
              />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="m-2 rounded-lg border border-slate-800 bg-obsidian-950/80 p-3">
        <div className="flex items-center gap-2 text-slate-500">
          <Activity className="h-3.5 w-3.5" />
          <span className="text-[10px] font-semibold uppercase tracking-wide">
            Makeathon 2026
          </span>
        </div>
        <p className="mt-1 text-[11px] leading-snug text-slate-600">
          Multimodal deforestation monitoring — Sentinel-1, Sentinel-2, AEF
          embeddings, weak labels.
        </p>
      </div>
    </aside>
  );
}
