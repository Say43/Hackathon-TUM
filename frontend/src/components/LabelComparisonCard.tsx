import { GitCompare } from "lucide-react";
import type { LandPlot, WeakLabelClass } from "../types";
import { StatusBadge } from "./StatusBadge";
import { cn } from "../lib/cn";

const CLASS_COLOR: Record<WeakLabelClass, "emerald" | "rose" | "amber"> = {
  stable: "emerald",
  deforestation: "rose",
  uncertain: "amber",
};

export function LabelComparisonCard({ plot }: { plot: LandPlot }) {
  const model = plot.prediction;
  return (
    <div className="panel p-4">
      <div className="mb-4 flex items-center gap-2">
        <GitCompare className="h-4 w-4 text-slate-400" />
        <h3 className="text-sm font-semibold text-white">Weak supervision comparison</h3>
      </div>

      <div className="space-y-3">
        <Row
          title="Model prediction"
          subtitle={model.modelVersion}
          label={model.deforestationDetected ? "deforestation" : "stable"}
          confidence={model.confidence}
          highlight
        />
        {plot.weakLabels.map((w, i) => (
          <Row
            key={w.labelSource}
            title={`Weak label source ${i + 1}`}
            subtitle={w.labelSource}
            label={w.label}
            confidence={w.confidence}
          />
        ))}
      </div>
    </div>
  );
}

function Row({
  title,
  subtitle,
  label,
  confidence,
  highlight,
}: {
  title: string;
  subtitle: string;
  label: WeakLabelClass;
  confidence: number;
  highlight?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border border-slate-800 p-3",
        highlight && "border-sky-800/50 bg-sky-950/20",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold text-slate-200">{title}</p>
          <p className="mt-0.5 text-[11px] text-slate-500">{subtitle}</p>
        </div>
        <StatusBadge tone={CLASS_COLOR[label]} className="capitalize">
          {label}
        </StatusBadge>
      </div>
      <div className="mt-2 flex items-center justify-between">
        <span className="text-[10px] text-slate-600">Confidence</span>
        <span className="font-mono text-sm font-semibold text-slate-300">
          {(confidence * 100).toFixed(0)}%
        </span>
      </div>
      <div className="mt-1 h-1 overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-sky-500/70"
          style={{ width: `${confidence * 100}%` }}
        />
      </div>
    </div>
  );
}
