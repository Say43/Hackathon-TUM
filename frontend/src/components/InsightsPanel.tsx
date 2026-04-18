import { Activity, Radar, TreeDeciduous } from "lucide-react";
import type { ActivityItem, LandPlot, NavKey } from "../types";
import { StatusBadge } from "./StatusBadge";
import { RiskBreakdownPanel } from "./RiskBreakdownPanel";
import { ActivityFeed } from "./ActivityFeed";

export function InsightsPanel({
  plot,
  onNavigate,
  onSelectPlotFromFeed,
  activityItems,
}: {
  plot: LandPlot;
  onNavigate: (key: NavKey) => void;
  onSelectPlotFromFeed?: (plotId: string) => void;
  activityItems: ActivityItem[];
}) {
  const p = plot.prediction;
  return (
    <div className="flex h-full w-full flex-col overflow-y-auto border-l border-slate-800/80 bg-obsidian-950/40">
      <div className="border-b border-slate-800/80 p-4">
        <p className="label-upper">Selected tile</p>
        <p className="mt-1 font-mono text-sm font-semibold text-sky-300">
          {plot.tileId}
        </p>
        <p className="mt-0.5 text-xs text-slate-500">{plot.region}</p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          <StatusBadge tone={p.deforestationDetected ? "rose" : "emerald"}>
            {p.deforestationDetected ? "Alert" : "Stable"}
          </StatusBadge>
          <StatusBadge tone="slate">{(p.confidence * 100).toFixed(0)}% conf.</StatusBadge>
          <StatusBadge tone="violet">{plot.complianceRelevance} EUDR</StatusBadge>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2">
          <Quick
            icon={TreeDeciduous}
            label="Forest cover"
            value={`${plot.forestCoverPct}%`}
          />
          <Quick
            icon={Radar}
            label="Signal strength"
            value={`${(plot.signalStrength * 100).toFixed(0)}%`}
          />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            className="btn flex-1 text-xs"
            onClick={() => onNavigate("plots")}
          >
            Open map
          </button>
          <button
            type="button"
            className="btn flex-1 text-xs"
            onClick={() => onNavigate("risk")}
          >
            Risk analysis
          </button>
          <button
            type="button"
            className="btn-primary flex-1 text-xs"
            onClick={() => onNavigate("validation")}
          >
            Validate
          </button>
        </div>
      </div>

      <div className="p-4">
        <RiskBreakdownPanel plot={plot} />
      </div>

      <div className="flex-1 border-t border-slate-800/80 p-4">
        <div className="mb-2 flex items-center gap-2">
          <Activity className="h-4 w-4 text-slate-500" />
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Monitoring feed
          </h3>
        </div>
        <ActivityFeed
          items={activityItems.slice(0, 4)}
          onSelectPlot={onSelectPlotFromFeed}
          compact
        />
      </div>
    </div>
  );
}

function Quick({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Radar;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-slate-800 bg-obsidian-900/60 px-2 py-2">
      <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase text-slate-500">
        <Icon className="h-3 w-3" />
        {label}
      </div>
      <p className="mt-0.5 font-mono text-sm font-semibold text-white">{value}</p>
    </div>
  );
}
