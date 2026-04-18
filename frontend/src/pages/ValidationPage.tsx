import type { LandPlot, TimeSeriesPoint } from "../types";
import { ValidationPanel } from "../components/ValidationPanel";
import { PlotSelector } from "../components/PlotSelector";

export function ValidationPage({
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
      <div className="min-w-0 flex-1">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-white">Validation workspace</h2>
          <p className="text-sm text-slate-500">
            Human-in-the-loop review for EUDR-aligned deforestation decisions
          </p>
        </div>
        <ValidationPanel plot={selectedPlot} timeSeries={timeSeries} />
      </div>
    </div>
  );
}
