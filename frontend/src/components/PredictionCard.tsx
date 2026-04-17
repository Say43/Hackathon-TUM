import { Brain, MapPin, Satellite } from "lucide-react";
import type { LandPlot } from "../types";
import { StatusBadge } from "./StatusBadge";
import { cn } from "../lib/cn";

const AGREEMENT_TONE = {
  agreement: "emerald" as const,
  conflict: "rose" as const,
  uncertain: "amber" as const,
};

const AGREEMENT_LABEL = {
  agreement: "Agreement",
  conflict: "Conflict",
  uncertain: "Uncertain",
};

export function PredictionCard({
  plot,
  selected,
  onClick,
}: {
  plot: LandPlot;
  selected?: boolean;
  onClick?: () => void;
}) {
  const p = plot.prediction;
  const cardClass = cn(
    "panel w-full p-4 text-left transition",
    onClick && "hover:border-slate-600 hover:bg-obsidian-850/30",
    selected && "ring-1 ring-sky-500/50 border-sky-800/60",
  );
  const inner = (
    <>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs text-sky-400">{plot.tileId}</span>
            <StatusBadge tone={AGREEMENT_TONE[p.labelAgreement]}>
              {AGREEMENT_LABEL[p.labelAgreement]}
            </StatusBadge>
          </div>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-slate-300">
            <MapPin className="h-3.5 w-3.5 text-slate-500" />
            {plot.region}
          </p>
        </div>
        <div className="text-right">
          <p className="label-upper">Confidence</p>
          <p className="font-mono text-xl font-semibold text-white">
            {(p.confidence * 100).toFixed(0)}%
          </p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Metric label="Deforestation" value={p.deforestationDetected ? "Yes" : "No"} />
        <Metric label="Event month" value={p.eventMonth} mono />
        <Metric label="Model" value={p.modelVersion} mono small />
        <Metric
          label="EUDR tier"
          value={plot.eudrRiskTier.toUpperCase()}
          accent
        />
      </div>

      <div className="mt-4 flex gap-2 rounded-lg border border-slate-800 bg-obsidian-950/80 p-3">
        <Brain className="mt-0.5 h-4 w-4 shrink-0 text-violet-400" />
        <p className="text-xs leading-relaxed text-slate-400">{p.notes}</p>
      </div>

      <div className="mt-3 flex items-center gap-2 text-[10px] text-slate-600">
        <Satellite className="h-3 w-3" />
        Multimodal fusion · S1 time series · S2 optical · AEF embeddings
      </div>
    </>
  );
  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={cardClass}>
        {inner}
      </button>
    );
  }
  return <div className={cardClass}>{inner}</div>;
}

function Metric({
  label,
  value,
  mono,
  small,
  accent,
}: {
  label: string;
  value: string;
  mono?: boolean;
  small?: boolean;
  accent?: boolean;
}) {
  return (
    <div className="rounded-lg border border-slate-800/80 bg-obsidian-950/50 px-2 py-2">
      <p className="text-[10px] font-medium uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p
        className={cn(
          "mt-0.5 font-semibold text-slate-200",
          mono && "font-mono text-xs",
          small && "text-xs",
          accent && "text-amber-400",
        )}
      >
        {value}
      </p>
    </div>
  );
}
