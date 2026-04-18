import type { ClassifierMetrics } from "../types/aef";

export function MetricsCard({
  title,
  metrics,
}: {
  title: string;
  metrics: ClassifierMetrics | null;
}) {
  return (
    <div className="panel p-4">
      <p className="label-upper">{title}</p>
      {!metrics || !metrics.supported ? (
        <p className="mt-2 text-sm text-slate-500">
          Not available
          {metrics?.reason ? ` (${metrics.reason.replace(/_/g, " ")})` : ""}.
        </p>
      ) : (
        <div className="mt-3 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
          <Metric label="Precision" value={metrics.precision} />
          <Metric label="Recall" value={metrics.recall} />
          <Metric label="F1" value={metrics.f1} />
          <Metric label="ROC AUC" value={metrics.rocAuc} />
        </div>
      )}
      {metrics?.samples !== undefined && (
        <p className="mt-2 text-[11px] text-slate-500">
          n = {metrics.samples.toLocaleString()} pixels
        </p>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value?: number | null }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-obsidian-950/80 px-3 py-2">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </p>
      <p className="mt-0.5 font-mono text-base text-white">
        {value === undefined || value === null
          ? "—"
          : (value * 100).toFixed(1) + "%"}
      </p>
    </div>
  );
}
