import { AlertTriangle, Gauge, Scale, Shield } from "lucide-react";
import type { LandPlot, RiskTier } from "../types";
import { cn } from "../lib/cn";

const TIER_COLOR: Record<RiskTier, string> = {
  low: "text-emerald-400",
  medium: "text-amber-400",
  high: "text-orange-400",
  critical: "text-red-400",
};

export function RiskBreakdownPanel({ plot }: { plot: LandPlot }) {
  const rows: { label: string; value: number; hint: string }[] = [
    {
      label: "Deforestation signal strength",
      value: plot.signalStrength,
      hint: "Fused S1/S2 + AEF response",
    },
    {
      label: "Label consistency",
      value: plot.labelConsistency,
      hint: "Agreement across weak sources",
    },
    {
      label: "Temporal consistency",
      value: plot.temporalConsistency,
      hint: "Stability of monthly trajectory",
    },
    {
      label: "Region anomaly risk",
      value: plot.regionAnomalyRisk,
      hint: "Peer tiles & biome context",
    },
    {
      label: "Evidence completeness",
      value: plot.evidenceCompleteness,
      hint: "Cloud-free optical coverage",
    },
  ];

  return (
    <div className="panel p-4">
      <div className="mb-4 flex items-center gap-2">
        <Scale className="h-4 w-4 text-slate-400" />
        <h3 className="text-sm font-semibold text-white">Risk breakdown</h3>
      </div>
      <ul className="space-y-3">
        {rows.map((r) => (
          <li key={r.label}>
            <div className="flex items-center justify-between gap-2 text-xs">
              <span className="font-medium text-slate-300">{r.label}</span>
              <span className="font-mono text-sky-300">
                {(r.value * 100).toFixed(0)}%
              </span>
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-800">
              <div
                className={cn(
                  "h-full rounded-full",
                  r.value >= 0.75
                    ? "bg-red-500/80"
                    : r.value >= 0.5
                      ? "bg-amber-500/80"
                      : "bg-emerald-600/70",
                )}
                style={{ width: `${r.value * 100}%` }}
              />
            </div>
            <p className="mt-0.5 text-[10px] text-slate-600">{r.hint}</p>
          </li>
        ))}
      </ul>

      <div className="mt-4 grid grid-cols-2 gap-2 border-t border-slate-800 pt-4">
        <Mini
          icon={Gauge}
          label="Composite risk"
          value={`${plot.riskScore}`}
          sub="/ 100"
        />
        <Mini
          icon={Shield}
          label="Data quality"
          value={`${(plot.dataQualityConfidence * 100).toFixed(0)}%`}
          sub="confidence"
        />
        <Mini
          icon={AlertTriangle}
          label="Human review"
          value={plot.humanReviewNeeded ? "Required" : "Clear"}
          sub={plot.reviewStatus}
        />
        <div className="rounded-lg border border-slate-800 bg-obsidian-950/80 p-2">
          <p className="text-[10px] font-medium uppercase text-slate-500">
            EUDR tier
          </p>
          <p
            className={cn(
              "mt-1 font-mono text-sm font-bold capitalize",
              TIER_COLOR[plot.eudrRiskTier],
            )}
          >
            {plot.eudrRiskTier}
          </p>
        </div>
      </div>
    </div>
  );
}

function Mini({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: typeof Gauge;
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-slate-800 bg-obsidian-950/80 p-2">
      <Icon className="mt-0.5 h-3.5 w-3.5 text-slate-500" />
      <div>
        <p className="text-[10px] font-medium uppercase text-slate-500">{label}</p>
        <p className="font-mono text-sm font-semibold text-white">
          {value}
          <span className="text-[10px] font-normal text-slate-500"> {sub}</span>
        </p>
      </div>
    </div>
  );
}
