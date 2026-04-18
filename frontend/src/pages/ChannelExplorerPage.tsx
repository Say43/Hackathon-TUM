import { useMemo, useState } from "react";
import { Eye, Palette } from "lucide-react";
import { bandsUrl } from "../lib/api";
import type { AefChannelStat, AefTile } from "../types/aef";
import { BandSlider } from "../components/BandSlider";
import { PcaPreviewImage } from "../components/PcaPreviewImage";
import { TileYearPicker } from "../components/TileYearPicker";

export function ChannelExplorerPage({
  tiles,
  selectedTile,
  selectedYear,
  onTileChange,
  onYearChange,
  channels,
}: {
  tiles: AefTile[];
  selectedTile: string | null;
  selectedYear: number | null;
  onTileChange: (t: string) => void;
  onYearChange: (y: number) => void;
  channels: AefChannelStat[];
}) {
  const split = tiles.find((t) => t.tileId === selectedTile)?.split ?? "train";
  const [r, setR] = useState(0);
  const [g, setG] = useState(21);
  const [b, setB] = useState(42);
  const [mode, setMode] = useState<"rgb" | "gray">("rgb");

  const url = useMemo(() => {
    if (!selectedTile || selectedYear === null) return null;
    return bandsUrl(selectedTile, selectedYear, { r, g, b }, mode, split);
  }, [selectedTile, selectedYear, r, g, b, mode, split]);

  const stat = (dim: number) =>
    channels.find((c) => c.dim === dim) ?? null;

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="label-upper">Channel explorer</p>
            <h2 className="text-lg font-semibold text-white">
              Compose 3 of 64 bands as RGB
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
          <PcaPreviewImage src={url} alt={`bands ${r}/${g}/${b}`} className="aspect-square max-h-[78vh]" />
        ) : (
          <div className="panel grid place-items-center p-8 text-sm text-slate-500">
            Pick a tile to render bands.
          </div>
        )}
      </div>

      <aside className="space-y-3">
        <div className="panel p-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="label-upper">Composition</p>
            <div className="inline-flex rounded-md border border-slate-800 bg-obsidian-950 p-0.5 text-[11px]">
              <Mode current={mode} onChange={setMode} mode="rgb" icon={<Palette className="h-3 w-3" />}>
                RGB
              </Mode>
              <Mode current={mode} onChange={setMode} mode="gray" icon={<Eye className="h-3 w-3" />}>
                Gray
              </Mode>
            </div>
          </div>
          <div className="space-y-3">
            <BandSlider label="Red / luminance" value={r} onChange={setR} accent="rose" />
            {mode === "rgb" && (
              <>
                <BandSlider label="Green" value={g} onChange={setG} accent="emerald" />
                <BandSlider label="Blue" value={b} onChange={setB} accent="sky" />
              </>
            )}
          </div>
          <p className="mt-3 text-[11px] leading-relaxed text-slate-500">
            Each band is a single dimension of the AEF embedding. Bands have
            already been dequantised, so values are continuous floats.
          </p>
        </div>

        <div className="panel">
          <div className="panel-header">
            <p className="label-upper">Per-channel stats</p>
            <span className="text-[11px] text-slate-500">{channels.length} bands</span>
          </div>
          <div className="max-h-[40vh] overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-obsidian-900/95 text-[10px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-3 py-2 text-left">Dim</th>
                  <th className="px-2 py-2 text-right">Min</th>
                  <th className="px-2 py-2 text-right">Mean</th>
                  <th className="px-2 py-2 text-right">Max</th>
                </tr>
              </thead>
              <tbody>
                {channels.map((c) => (
                  <tr
                    key={c.dim}
                    className={`border-t border-slate-800/60 ${
                      c.dim === r || c.dim === g || c.dim === b
                        ? "bg-sky-950/30"
                        : ""
                    }`}
                  >
                    <td className="px-3 py-1.5 font-mono text-slate-300">
                      {c.dim}
                    </td>
                    <td className="px-2 py-1.5 text-right font-mono text-slate-400">
                      {c.min !== null ? c.min.toFixed(2) : "—"}
                    </td>
                    <td className="px-2 py-1.5 text-right font-mono text-slate-200">
                      {c.mean !== null ? c.mean.toFixed(3) : "—"}
                    </td>
                    <td className="px-2 py-1.5 text-right font-mono text-slate-400">
                      {c.max !== null ? c.max.toFixed(2) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {channels.length === 0 && (
              <p className="px-4 py-3 text-xs text-slate-500">
                Loading per-channel stats…
              </p>
            )}
          </div>
        </div>

        <div className="panel p-4 text-[11px] text-slate-500">
          Selected bands:{" "}
          {mode === "rgb" ? (
            <span className="font-mono text-slate-300">
              R={r} · G={g} · B={b}
            </span>
          ) : (
            <span className="font-mono text-slate-300">band {r}</span>
          )}
          {(() => {
            const s = stat(r);
            if (!s || s.min === null) return null;
            return (
              <p className="mt-1">
                R-band range:{" "}
                <span className="font-mono text-slate-300">
                  [{s.min.toFixed(2)}, {s.max!.toFixed(2)}]
                </span>{" "}
                · valid {(s.validFraction * 100).toFixed(1)}%
              </p>
            );
          })()}
        </div>
      </aside>
    </div>
  );
}

function Mode({
  current,
  mode,
  onChange,
  icon,
  children,
}: {
  current: "rgb" | "gray";
  mode: "rgb" | "gray";
  onChange: (m: "rgb" | "gray") => void;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  const active = current === mode;
  return (
    <button
      type="button"
      onClick={() => onChange(mode)}
      className={`flex items-center gap-1 rounded px-2 py-1 ${
        active ? "bg-sky-600/30 text-sky-200" : "text-slate-400 hover:text-slate-200"
      }`}
    >
      {icon}
      {children}
    </button>
  );
}
