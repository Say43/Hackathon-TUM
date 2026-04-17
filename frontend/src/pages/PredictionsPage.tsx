import type { LandPlot } from "../types";
import { PredictionCard } from "../components/PredictionCard";
import { LabelComparisonCard } from "../components/LabelComparisonCard";
import { PlotSelector } from "../components/PlotSelector";

export function PredictionsPage({
  plots,
  selectedPlot,
  search,
  onSelectPlot,
}: {
  plots: LandPlot[];
  selectedPlot: LandPlot;
  search: string;
  onSelectPlot: (p: LandPlot) => void;
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
      <div className="min-w-0 flex-1 space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-white">Model predictions</h2>
          <p className="text-sm text-slate-500">
            Fusion output vs weak supervision — agreement, conflict, uncertainty
          </p>
        </div>
        <PredictionCard plot={selectedPlot} />
        <LabelComparisonCard plot={selectedPlot} />
      </div>
    </div>
  );
}
