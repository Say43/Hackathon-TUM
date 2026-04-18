import type { ClassifierMetrics } from "../types/aef";

export function ConfusionMatrix({ metrics }: { metrics: ClassifierMetrics | null }) {
  if (!metrics?.confusion) {
    return (
      <div className="panel p-4">
        <p className="label-upper">Confusion matrix</p>
        <p className="mt-2 text-sm text-slate-500">No labelled test data.</p>
      </div>
    );
  }
  const { tn, fp, fn, tp } = metrics.confusion;
  const cells = [
    { label: "TN", value: tn, tone: "bg-emerald-950/40 text-emerald-300" },
    { label: "FP", value: fp, tone: "bg-amber-950/40 text-amber-200" },
    { label: "FN", value: fn, tone: "bg-amber-950/40 text-amber-200" },
    { label: "TP", value: tp, tone: "bg-emerald-950/40 text-emerald-300" },
  ];
  return (
    <div className="panel p-4">
      <p className="label-upper">Confusion matrix</p>
      <div className="mt-3 grid grid-cols-[60px_1fr_1fr] gap-1 text-center text-xs">
        <div></div>
        <div className="text-slate-400">Pred 0</div>
        <div className="text-slate-400">Pred 1</div>
        <div className="self-center text-right text-slate-400">Truth 0</div>
        <Cell {...cells[0]} />
        <Cell {...cells[1]} />
        <div className="self-center text-right text-slate-400">Truth 1</div>
        <Cell {...cells[2]} />
        <Cell {...cells[3]} />
      </div>
    </div>
  );
}

function Cell({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className={`rounded-md border border-slate-800 px-2 py-3 ${tone}`}>
      <p className="font-mono text-base">{value.toLocaleString()}</p>
      <p className="text-[10px] uppercase tracking-wide text-slate-400">
        {label}
      </p>
    </div>
  );
}
