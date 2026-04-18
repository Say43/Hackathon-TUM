import { useState } from "react";
import type { LandPlot } from "../types";
import { PlotSelector } from "../components/PlotSelector";
import { TimeSeriesChart, type TimeSeriesMode } from "../components/TimeSeriesChart";
import type { TimeSeriesPoint } from "../types";
import { cn } from "../lib/cn";

export function TimeSeriesPage({
  plots,
  selectedPlot,
  search,
  onSelectPlot,
  timeSeries,
}: {
  plots: LandPlot[];
  selectedPlot: LandPlot;
  search: string;
  onSelectPlot: (p: LandPlot) => void;
  timeSeries: TimeSeriesPoint[];
}) {
  const [mode, setMode] = useState<TimeSeriesMode>("both");
  const series = timeSeries;
  const n = Math.max(1, series.length);
  const confSeries = series.map((d, i) => ({
    ...d,
    conf: Math.min(0.95, 0.55 + (i / n) * 0.35 + (d.eventFlag ? 0.08 : 0)),
  }));

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 lg:flex-row">
      <div className="w-full shrink-0 lg:w-56">
        <PlotSelector
          plots={plots}
          selectedId={selectedPlot.id}
          onSelect={onSelectPlot}
          search={search}
        />
      </div>
      <div className="min-w-0 flex-1 space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-white">Time series inspection</h2>
          <p className="text-sm text-slate-500">
            Monthly multimodal signals · event markers · change window
          </p>
        </div>

        <div className="panel p-4">
          <p className="label-upper">Temporal evidence</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {(
              [
                ["both", "S1 + S2"],
                ["ndvi", "Optical NDVI"],
                ["radar", "SAR VV"],
                ["embedding", "AEF embedding"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setMode(id)}
                className={cn(
                  "rounded-md border px-3 py-1.5 text-xs font-semibold transition",
                  mode === id
                    ? "border-sky-600/60 bg-sky-600/20 text-sky-200"
                    : "border-slate-700 text-slate-500 hover:border-slate-600",
                )}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="mt-4">
            <TimeSeriesChart
              data={series}
              mode={mode}
              changeStart={selectedPlot.changeWindowStart}
              changeEnd={selectedPlot.changeWindowEnd}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="panel p-4">
            <p className="label-upper">Detected change window</p>
            <p className="mt-2 font-mono text-lg text-white">
              {selectedPlot.changeWindowStart} → {selectedPlot.changeWindowEnd}
            </p>
            <p className="mt-2 text-xs text-slate-500">
              Aligned structural break in NDVI / radar with AEF trajectory shift. Weak
              label aggregate peaks inside this window.
            </p>
          </div>
          <div className="panel p-4">
            <p className="label-upper">Confidence trend</p>
            <p className="mt-2 text-xs text-slate-500">
              Rolling fusion confidence after temporal aggregation (demo curve).
            </p>
            <div className="mt-3 h-28">
              <TimeSeriesChart
                data={confSeries.map((d) => ({
                  ...d,
                  sentinel2Ndvi: d.conf,
                  sentinel1Vvdb: d.conf * 0.92,
                }))}
                mode="ndvi"
                changeStart={selectedPlot.changeWindowStart}
                changeEnd={selectedPlot.changeWindowEnd}
                compact
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
