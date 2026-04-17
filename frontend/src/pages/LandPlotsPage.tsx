import type { LandPlot, LayerId } from "../types";
import { PlotMapPanel } from "../components/PlotMapPanel";
import { PlotSelector } from "../components/PlotSelector";
import { RegionFilter, regionMatches } from "../components/RegionFilter";
import { LayerToggle } from "../components/LayerToggle";

export function LandPlotsPage({
  plots,
  selectedPlot,
  region,
  onRegion,
  search,
  layers,
  onToggleLayer,
  onSelectPlot,
}: {
  plots: LandPlot[];
  selectedPlot: LandPlot;
  region: string;
  onRegion: (r: string) => void;
  search: string;
  layers: Record<LayerId, boolean>;
  onToggleLayer: (id: LayerId) => void;
  onSelectPlot: (p: LandPlot) => void;
}) {
  const filtered = plots.filter((p) => regionMatches(p.region, region));

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 lg:flex-row">
      <div className="flex w-full shrink-0 flex-col gap-3 lg:w-64">
        <RegionFilter value={region} onChange={onRegion} />
        <PlotSelector
          plots={filtered}
          selectedId={selectedPlot.id}
          onSelect={onSelectPlot}
          search={search}
        />
      </div>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold text-white">Land plot explorer</h2>
          <LayerToggle active={layers} onToggle={onToggleLayer} />
        </div>
        <PlotMapPanel
          plot={selectedPlot}
          layers={layers}
          className="min-h-[480px] flex-1"
        />
        <p className="text-[11px] text-slate-600">
          Demo visualization: synthetic basemap with vector overlays. Production would
          stream COG tiles, S1/S2 stacks, and embedding rasters for tile{" "}
          <span className="font-mono text-slate-500">{selectedPlot.tileId}</span>.
        </p>
      </div>
    </div>
  );
}
