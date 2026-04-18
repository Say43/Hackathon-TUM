import { useMemo } from "react";
import { previewUrl } from "../lib/api";
import type { AefTile, AefTileSummary } from "../types/aef";
import { PcaPreviewImage } from "../components/PcaPreviewImage";
import { TileYearPicker } from "../components/TileYearPicker";

export function EmbeddingMapPage({
  tiles,
  selectedTile,
  selectedYear,
  onTileChange,
  onYearChange,
  summary,
}: {
  tiles: AefTile[];
  selectedTile: string | null;
  selectedYear: number | null;
  onTileChange: (t: string) => void;
  onYearChange: (y: number) => void;
  summary: AefTileSummary | null;
}) {
  const split = tiles.find((t) => t.tileId === selectedTile)?.split ?? "train";
  const url = useMemo(() => {
    if (!selectedTile || selectedYear === null) return null;
    return previewUrl(selectedTile, selectedYear, split);
  }, [selectedTile, selectedYear, split]);

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_320px]">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="label-upper">Embedding map</p>
            <h2 className="text-lg font-semibold text-white">
              PCA-3 false-colour preview
            </h2>
          </div>
          <TileYearPicker
            tiles={tiles}
            selectedTile={selectedTile}
            selectedYear={selectedYear}
            onTileChange={onTileChange}
            onYearChange={onYearChange}
            splitLabel={split}
          />
        </div>
        {url ? (
          <PcaPreviewImage src={url} alt={`${selectedTile} ${selectedYear}`} className="aspect-square max-h-[78vh]" />
        ) : (
          <div className="panel grid place-items-center p-8 text-sm text-slate-500">
            Pick a tile + year to render its PCA preview.
          </div>
        )}
        <p className="text-[11px] leading-relaxed text-slate-500">
          PCA is fit on the 64-dim embeddings of every valid pixel in the tile,
          then the top 3 components are min/max-stretched into RGB. Greenish
          regions tend to share the same dominant signal, while sharp colour
          shifts indicate land-cover changes — including, but not limited to,
          deforestation.
        </p>
      </div>

      <aside className="space-y-3">
        <div className="panel p-4">
          <p className="label-upper">Tile</p>
          <p className="mt-1 font-mono text-base text-sky-300">
            {selectedTile ?? "—"}
          </p>
          {summary && (
            <dl className="mt-3 grid grid-cols-2 gap-2 text-[11px] text-slate-400">
              <Field label="Year">{summary.year}</Field>
              <Field label="Bands">{summary.bands}</Field>
              <Field label="Height">{summary.height}</Field>
              <Field label="Width">{summary.width}</Field>
              <Field label="Min lon">{summary.bbox.minLon.toFixed(4)}°</Field>
              <Field label="Max lon">{summary.bbox.maxLon.toFixed(4)}°</Field>
              <Field label="Min lat">{summary.bbox.minLat.toFixed(4)}°</Field>
              <Field label="Max lat">{summary.bbox.maxLat.toFixed(4)}°</Field>
            </dl>
          )}
        </div>
        {summary && Object.keys(summary.labelCounts).length > 0 && (
          <div className="panel p-4">
            <p className="label-upper">Label coverage</p>
            <ul className="mt-2 space-y-1 text-xs">
              {Object.entries(summary.labelCounts).map(([source, c]) => {
                const total = c.positive + c.negative;
                const pct = total ? (c.positive / total) * 100 : 0;
                return (
                  <li key={source} className="rounded-md border border-slate-800 bg-obsidian-950/60 px-2 py-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-mono uppercase text-slate-300">
                        {source}
                      </span>
                      <span className="text-slate-500">
                        {pct.toFixed(2)}% positive
                      </span>
                    </div>
                    <div className="mt-1 h-1.5 w-full overflow-hidden rounded bg-slate-800">
                      <div
                        className="h-full bg-rose-500"
                        style={{ width: `${Math.min(100, pct)}%` }}
                      />
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </aside>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-slate-800 bg-obsidian-950/40 px-2 py-1.5">
      <p className="text-[10px] uppercase tracking-wider text-slate-500">
        {label}
      </p>
      <p className="mt-0.5 font-mono text-slate-200">{children}</p>
    </div>
  );
}
