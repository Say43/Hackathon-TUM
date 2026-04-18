import { AlertTriangle, MapPin } from "lucide-react";
import type { MislabelRegion } from "../types/aef";

export function MislabelList({
  regions,
  loading,
  error,
}: {
  regions: MislabelRegion[];
  loading: boolean;
  error: string | null;
}) {
  if (loading) {
    return (
      <div className="panel p-4 text-sm text-slate-500">Computing disagreement…</div>
    );
  }
  if (error) {
    return (
      <div className="panel p-4 text-sm text-rose-300">{error}</div>
    );
  }
  if (!regions.length) {
    return (
      <div className="panel p-4 text-sm text-slate-500">
        No high-confidence disagreement found between the trained model and the
        weak labels for this run.
      </div>
    );
  }
  return (
    <div className="panel">
      <div className="panel-header">
        <p className="label-upper">Likely mislabelled regions</p>
        <span className="text-[11px] text-slate-500">{regions.length} shown</span>
      </div>
      <ul className="divide-y divide-slate-800">
        {regions.map((r) => (
          <li key={r.id} className="flex items-start gap-3 px-4 py-3 text-xs">
            <AlertTriangle
              className={`mt-0.5 h-4 w-4 shrink-0 ${
                r.score > 1000 ? "text-rose-400" : "text-amber-400"
              }`}
            />
            <div className="min-w-0 flex-1">
              <p className="font-mono text-slate-200">
                region {r.id}
                <span className="ml-2 rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">
                  {r.areaPixels.toLocaleString()} px
                </span>
              </p>
              <p className="mt-0.5 text-slate-500">
                weak label
                <span className="mx-1 rounded bg-amber-900/40 px-1 text-amber-200">
                  {r.labelClass}
                </span>
                vs. model
                <span className="mx-1 rounded bg-sky-900/40 px-1 text-sky-200">
                  {r.predictedClass}
                </span>
                · confidence {(r.meanConfidence * 100).toFixed(0)}%
              </p>
              <p className="mt-0.5 flex items-center gap-1 font-mono text-[10px] text-slate-500">
                <MapPin className="h-3 w-3" />
                {r.centroid.lat.toFixed(4)}°, {r.centroid.lon.toFixed(4)}°
              </p>
            </div>
            <span className="self-start font-mono text-[11px] text-slate-400">
              {r.score.toFixed(0)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
