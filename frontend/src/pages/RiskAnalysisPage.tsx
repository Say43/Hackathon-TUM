import { useState } from "react";
import { FileWarning, Gauge, Scale, ShieldAlert, UserCheck } from "lucide-react";
import type { LandPlot } from "../types";
import { PlotSelector } from "../components/PlotSelector";
import { RiskBreakdownPanel } from "../components/RiskBreakdownPanel";
import { SummaryCard } from "../components/SummaryCard";
import { StatusBadge } from "../components/StatusBadge";

export function RiskAnalysisPage({
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
  const [bumped, setBumped] = useState(false);
  const displayScore = bumped
    ? Math.min(100, selectedPlot.riskScore + 4)
    : selectedPlot.riskScore;

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
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-white">EUDR risk analysis</h2>
            <p className="text-sm text-slate-500">
              Importer-facing decision support · compliance relevance
            </p>
          </div>
          <button
            type="button"
            className="btn text-xs"
            onClick={() => setBumped((v) => !v)}
          >
            Simulate risk refresh
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          <SummaryCard
            label="EUDR risk score"
            value={String(displayScore)}
            sub="0–100 composite"
            icon={Scale}
            accent="text-amber-400"
            highlight={displayScore >= 75}
          />
          <SummaryCard
            label="Forest change risk"
            value={`${(selectedPlot.signalStrength * 100).toFixed(0)}%`}
            sub="Fused EO signal"
            icon={FileWarning}
            accent="text-orange-400"
          />
          <SummaryCard
            label="Data quality confidence"
            value={`${(selectedPlot.dataQualityConfidence * 100).toFixed(0)}%`}
            sub="Observability-weighted"
            icon={Gauge}
            accent="text-sky-400"
          />
          <SummaryCard
            label="Human review"
            value={selectedPlot.humanReviewNeeded ? "Required" : "Clear"}
            sub={selectedPlot.reviewStatus}
            icon={UserCheck}
            accent="text-violet-400"
          />
          <SummaryCard
            label="Compliance relevance"
            value={selectedPlot.complianceRelevance.toUpperCase()}
            sub="Supply-chain tier"
            icon={ShieldAlert}
            accent="text-emerald-400"
          />
        </div>

        <div className="flex flex-wrap gap-2">
          <StatusBadge tone="slate">Deforestation signal strength</StatusBadge>
          <StatusBadge tone="sky">
            {(selectedPlot.signalStrength * 100).toFixed(0)}%
          </StatusBadge>
          <StatusBadge tone="amber">
            Label consistency {(selectedPlot.labelConsistency * 100).toFixed(0)}%
          </StatusBadge>
          <StatusBadge tone="violet">
            Temporal {(selectedPlot.temporalConsistency * 100).toFixed(0)}%
          </StatusBadge>
        </div>

        <RiskBreakdownPanel plot={{ ...selectedPlot, riskScore: displayScore }} />
      </div>
    </div>
  );
}
