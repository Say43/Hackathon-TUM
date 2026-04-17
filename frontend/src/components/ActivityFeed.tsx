import {
  AlertOctagon,
  Bell,
  GitBranch,
  Radar,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";
import type { ActivityItem } from "../types";
import { cn } from "../lib/cn";

const ICONS: Record<
  ActivityItem["type"],
  { Icon: typeof Bell; color: string }
> = {
  flagged: { Icon: AlertOctagon, color: "text-red-400" },
  label_conflict: { Icon: GitBranch, color: "text-amber-400" },
  confidence_shift: { Icon: TrendingUp, color: "text-sky-400" },
  human_review: { Icon: ShieldAlert, color: "text-violet-400" },
  risk_update: { Icon: Radar, color: "text-slate-400" },
  detection: { Icon: Bell, color: "text-emerald-400" },
};

export function ActivityFeed({
  items,
  onSelectPlot,
  compact,
}: {
  items: ActivityItem[];
  onSelectPlot?: (plotId: string) => void;
  compact?: boolean;
}) {
  return (
    <ul className={cn("space-y-2", compact && "max-h-64 overflow-y-auto pr-1")}>
      {items.map((item) => {
        const meta = ICONS[item.type];
        const Icon = meta.Icon;
        return (
          <li key={item.id}>
            <button
              type="button"
              disabled={!item.plotId || !onSelectPlot}
              onClick={() => item.plotId && onSelectPlot?.(item.plotId)}
              className={cn(
                "flex w-full gap-3 rounded-lg border border-slate-800/80 bg-obsidian-950/50 p-3 text-left transition",
                item.plotId && onSelectPlot && "hover:border-slate-600 cursor-pointer",
                (!item.plotId || !onSelectPlot) && "cursor-default",
              )}
            >
              <div
                className={cn(
                  "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-800 bg-obsidian-900",
                  meta.color,
                )}
              >
                <Icon className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-200">{item.title}</p>
                <p className="mt-0.5 text-xs text-slate-500">{item.detail}</p>
                <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[10px] text-slate-600">
                  {item.tileId && (
                    <span className="font-mono text-sky-600/90">{item.tileId}</span>
                  )}
                  <span>{formatTime(item.timestamp)}</span>
                  <span
                    className={cn(
                      "rounded px-1 py-0.5 font-semibold uppercase",
                      item.severity === "critical" && "bg-red-950/60 text-red-300",
                      item.severity === "warning" && "bg-amber-950/50 text-amber-300",
                      item.severity === "info" && "bg-slate-800 text-slate-400",
                    )}
                  >
                    {item.severity}
                  </span>
                </div>
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
