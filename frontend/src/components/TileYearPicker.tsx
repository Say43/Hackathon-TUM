import type { AefTile, Split } from "../types/aef";

export function TileYearPicker({
  tiles,
  selectedTile,
  selectedYear,
  onTileChange,
  onYearChange,
  splitLabel,
  disabled,
}: {
  tiles: AefTile[];
  selectedTile: string | null;
  selectedYear: number | null;
  onTileChange: (tile: string) => void;
  onYearChange: (year: number) => void;
  splitLabel?: Split;
  disabled?: boolean;
}) {
  const tile = tiles.find((t) => t.tileId === selectedTile) ?? tiles[0];
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      {splitLabel && (
        <span className="rounded-md border border-slate-700 bg-obsidian-900 px-2 py-1 font-mono uppercase text-slate-400">
          {splitLabel}
        </span>
      )}
      <select
        value={selectedTile ?? ""}
        onChange={(e) => onTileChange(e.target.value)}
        className="input max-w-[220px] py-1 font-mono text-xs"
        disabled={disabled || tiles.length === 0}
      >
        {tiles.length === 0 && <option value="">no tiles</option>}
        {tiles.map((t) => (
          <option key={t.tileId} value={t.tileId}>
            {t.tileId} {t.hasLabels ? "·labels" : ""}
          </option>
        ))}
      </select>
      <select
        value={selectedYear ?? ""}
        onChange={(e) => onYearChange(Number(e.target.value))}
        className="input w-24 py-1 font-mono text-xs"
        disabled={disabled || !tile}
      >
        {(tile?.years ?? []).map((y) => (
          <option key={y} value={y}>
            {y}
          </option>
        ))}
      </select>
    </div>
  );
}
