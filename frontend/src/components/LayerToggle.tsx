import { cn } from "../lib/cn";
import type { LayerId } from "../types";

const LAYERS: { id: LayerId; label: string }[] = [
  { id: "sentinel1", label: "Sentinel-1" },
  { id: "sentinel2", label: "Sentinel-2" },
  { id: "embeddings", label: "Embeddings" },
  { id: "weakLabels", label: "Weak Labels" },
  { id: "predictions", label: "Predictions" },
];

export function LayerToggle({
  active,
  onToggle,
}: {
  active: Record<LayerId, boolean>;
  onToggle: (id: LayerId) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {LAYERS.map((l) => {
        const on = active[l.id];
        return (
          <button
            key={l.id}
            type="button"
            onClick={() => onToggle(l.id)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-semibold transition",
              on
                ? "border-sky-600/60 bg-sky-600/20 text-sky-200"
                : "border-slate-700 bg-obsidian-950 text-slate-500 hover:border-slate-600 hover:text-slate-400",
            )}
          >
            {l.label}
          </button>
        );
      })}
    </div>
  );
}
