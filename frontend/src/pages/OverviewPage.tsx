import { AlertTriangle, Globe2, Layers, Radar, Shield, TreePine } from "lucide-react";
import type { ActivityItem, LandPlot, LayerId } from "../types";
import { SummaryCard } from "../components/SummaryCard";
import { PlotMapPanel } from "../components/PlotMapPanel";
import { TimeSeriesChart } from "../components/TimeSeriesChart";
import { ActivityFeed } from "../components/ActivityFeed";
import { LayerToggle } from "../components/LayerToggle";
import { PredictionCard } from "../components/PredictionCard";
import type { TimeSeriesPoint } from "../types";
import { StatusBadge } from "../components/StatusBadge";

export function OverviewPage({
  plots,
  selectedPlot,
  layers,
  onToggleLayer,
  onSelectPlot,
  onSelectPlotById,
  previewTimeSeries,
  activityItems,
}: {
  plots: LandPlot[];
  selectedPlot: LandPlot;
  layers: Record<LayerId, boolean>;
  onToggleLayer: (id: LayerId) => void;
  onSelectPlot: (p: LandPlot) => void;
  onSelectPlotById?: (id: string) => void;
  previewTimeSeries: TimeSeriesPoint[];
  activityItems: ActivityItem[];
}) {
  const total = plots.length;
  const flagged = plots.filter((p) => p.prediction.deforestationDetected).length;
  const highRisk = plots.filter((p) => p.eudrRiskTier === "high" || p.eudrRiskTier === "critical").length;
  const regions = new Set(plots.map((p) => p.region)).size;
  const queue = plots.filter((p) => p.humanReviewNeeded).length;

  const detections = [...plots]
    .filter((p) => p.prediction.deforestationDetected)
    .sort((a, b) => b.prediction.confidence - a.prediction.confidence)
    .slice(0, 3);

  const series = previewTimeSeries;
  const avgRisk = Math.round(
    plots.reduce((s, p) => s + p.riskScore, 0) / Math.max(plots.length, 1),
  );

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <SummaryCard
          label="Total land plots"
          value={String(total)}
          sub="Sentinel tiles in scope"
          icon={Layers}
          accent="text-sky-400"
        />
        <SummaryCard
          label="Flagged deforestation"
          value={String(flagged)}
          sub="Model positive"
          icon={TreePine}
          accent="text-amber-400"
        />
        <SummaryCard
          label="High risk plots"
          value={String(highRisk)}
          sub="EUDR high + critical"
          icon={AlertTriangle}
          accent="text-orange-400"
        />
        <SummaryCard
          label="Regions monitored"
          value={String(regions)}
          sub="Biomes & supply sheds"
          icon={Globe2}
          accent="text-violet-400"
        />
        <SummaryCard
          label="Validation queue"
          value={String(queue)}
          sub="Human-in-the-loop"
          icon={Shield}
          accent="text-emerald-400"
          highlight
        />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="space-y-3 xl:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-semibold text-white">
                Live monitoring workspace
              </h2>
              <p className="text-xs text-slate-500">
                Selected:{" "}
                <span className="font-mono text-sky-400">{selectedPlot.tileId}</span>
              </p>
            </div>
            <LayerToggle active={layers} onToggle={onToggleLayer} />
          </div>
          <PlotMapPanel
            plot={selectedPlot}
            layers={layers}
            className="min-h-[340px] xl:min-h-[380px]"
            title="Satellite land plot — multimodal stack"
          />
        </div>

        <div className="panel flex flex-col p-4">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-white">Risk summary</h3>
            <StatusBadge tone="amber">Portfolio {avgRisk}</StatusBadge>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Composite EUDR-relevant risk across monitored tiles (demo aggregate).
          </p>
          <div className="mt-4 space-y-3">
            <RiskBar label="Deforestation pressure" value={72} />
            <RiskBar label="Weak-label volatility" value={58} />
            <RiskBar label="Evidence density" value={81} />
          </div>
          <div className="mt-4 border-t border-slate-800 pt-4">
            <p className="label-upper mb-2">Temporal evidence preview</p>
            <TimeSeriesChart
              data={series}
              mode="both"
              changeStart={selectedPlot.changeWindowStart}
              changeEnd={selectedPlot.changeWindowEnd}
              compact
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="panel p-4">
          <div className="mb-3 flex items-center gap-2">
            <Radar className="h-4 w-4 text-sky-500" />
            <h3 className="text-sm font-semibold text-white">Recent monitoring events</h3>
          </div>
          <ActivityFeed items={activityItems} onSelectPlot={onSelectPlotById} />
        </div>
        <div className="panel p-4">
          <h3 className="text-sm font-semibold text-white">Recent model detections</h3>
          <p className="mt-0.5 text-xs text-slate-500">
            Highest-confidence positive predictions — click to inspect plot.
          </p>
          <div className="mt-3 space-y-2">
            {detections.map((p) => (
              <PredictionCard
                key={p.id}
                plot={p}
                selected={p.id === selectedPlot.id}
                onClick={() => onSelectPlot(p)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function RiskBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs">
        <span className="text-slate-400">{label}</span>
        <span className="font-mono text-slate-300">{value}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-gradient-to-r from-sky-700 to-sky-500"
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}
