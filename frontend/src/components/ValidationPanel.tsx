import { useState } from "react";
import { Check, Download, HelpCircle, XCircle } from "lucide-react";
import type { LandPlot } from "../types";
import { PlotMapPanel } from "./PlotMapPanel";
import { TimeSeriesChart, type TimeSeriesMode } from "./TimeSeriesChart";
import { LabelComparisonCard } from "./LabelComparisonCard";
import { PredictionCard } from "./PredictionCard";
import type { LayerId, TimeSeriesPoint } from "../types";

const DEFAULT_LAYERS: Record<LayerId, boolean> = {
  sentinel1: true,
  sentinel2: true,
  embeddings: true,
  weakLabels: true,
  predictions: true,
};

export function ValidationPanel({
  plot,
  timeSeries,
  onExport,
}: {
  plot: LandPlot;
  timeSeries: TimeSeriesPoint[];
  onExport?: () => void;
}) {
  const [feedback, setFeedback] = useState<string | null>(null);
  const [tsMode, setTsMode] = useState<TimeSeriesMode>("both");
  const series = timeSeries;

  const act = (msg: string) => {
    setFeedback(msg);
    window.setTimeout(() => setFeedback(null), 3200);
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <PlotMapPanel plot={plot} layers={DEFAULT_LAYERS} title="Validation preview" />
        <div className="panel p-4">
          <p className="label-upper">Temporal evidence</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {(
              [
                ["both", "S1 + S2"],
                ["ndvi", "NDVI only"],
                ["radar", "Radar only"],
                ["embedding", "AEF only"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setTsMode(id)}
                className={`rounded-md border px-2 py-1 text-xs font-semibold transition ${
                  tsMode === id
                    ? "border-sky-600/60 bg-sky-600/20 text-sky-200"
                    : "border-slate-700 text-slate-500 hover:text-slate-400"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="mt-3">
            <TimeSeriesChart
              data={series}
              mode={tsMode}
              changeStart={plot.changeWindowStart}
              changeEnd={plot.changeWindowEnd}
              compact
            />
          </div>
        </div>
      </div>

      <PredictionCard plot={plot} />
      <LabelComparisonCard plot={plot} />

      <div className="panel p-4">
        <p className="label-upper mb-3">Reviewer decision</p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="btn-danger"
            onClick={() => act("Confirmed as deforestation — case logged.")}
          >
            <Check className="h-4 w-4" />
            Confirm Deforestation
          </button>
          <button
            type="button"
            className="btn"
            onClick={() => act("Detection rejected — model false positive recorded.")}
          >
            <XCircle className="h-4 w-4" />
            Reject Detection
          </button>
          <button
            type="button"
            className="btn"
            onClick={() => act("Marked uncertain — queued for senior analyst.")}
          >
            <HelpCircle className="h-4 w-4" />
            Mark Uncertain
          </button>
          <button
            type="button"
            className="btn"
            onClick={() => act("More evidence requested — optical refresh scheduled.")}
          >
            Needs More Evidence
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={() => {
              act("Review packet exported (mock).");
              onExport?.();
            }}
          >
            <Download className="h-4 w-4" />
            Export Review
          </button>
        </div>
        {feedback && (
          <p className="mt-3 rounded-lg border border-emerald-900/50 bg-emerald-950/30 px-3 py-2 text-xs font-medium text-emerald-300">
            {feedback}
          </p>
        )}
      </div>
    </div>
  );
}
