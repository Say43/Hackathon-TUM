import { Crosshair, Layers } from "lucide-react";
import type { LandPlot, LayerId, MapOverlayRegion } from "../types";
import { cn } from "../lib/cn";

const LEGEND: { kind: MapOverlayRegion["kind"]; label: string; color: string }[] = [
  { kind: "stable_forest", label: "Stable forest", color: "#166534" },
  { kind: "predicted_change", label: "Predicted change", color: "#ea580c" },
  { kind: "weak_hint", label: "Weak label hint", color: "#fbbf24" },
  { kind: "water", label: "Water / mask", color: "#1e3a5f" },
];

export function PlotMapPanel({
  plot,
  layers,
  className,
  title,
}: {
  plot: LandPlot;
  layers: Record<LayerId, boolean>;
  className?: string;
  title?: string;
}) {
  const showPred = layers.predictions;
  const showWeak = layers.weakLabels;
  const showS1 = layers.sentinel1;
  const showS2 = layers.sentinel2;
  const showEmb = layers.embeddings;

  return (
    <div className={cn("panel flex min-h-[280px] flex-col overflow-hidden", className)}>
      <div className="panel-header bg-obsidian-850/50">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-sky-500" />
          <div>
            <p className="text-sm font-semibold text-white">
              {title ?? "Land plot — satellite workspace"}
            </p>
            <p className="font-mono text-[11px] text-slate-500">
              {plot.tileId} · {plot.centroidLat.toFixed(3)}°,{" "}
              {plot.centroidLng.toFixed(3)}°
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
          <Crosshair className="h-3.5 w-3.5" />
          <span>
            S1 {showS1 ? "on" : "off"} · S2 {showS2 ? "on" : "off"} · AEF{" "}
            {showEmb ? "on" : "off"}
          </span>
        </div>
      </div>

      <div className="relative flex-1 min-h-[220px]">
        {/* Synthetic satellite basemap */}
        <div
          className="absolute inset-0"
          style={{
            background: `
              radial-gradient(ellipse 120% 80% at 30% 20%, rgba(22,101,52,0.35) 0%, transparent 50%),
              radial-gradient(ellipse 100% 60% at 70% 60%, rgba(30,58,95,0.25) 0%, transparent 45%),
              linear-gradient(165deg, #0c1220 0%, #0f172a 40%, #1a1f2e 100%)
            `,
          }}
        />
        <div
          className="absolute inset-0 opacity-[0.12]"
          style={{
            backgroundImage: `linear-gradient(rgba(148,163,184,0.4) 1px, transparent 1px),
              linear-gradient(90deg, rgba(148,163,184,0.4) 1px, transparent 1px)`,
            backgroundSize: "24px 24px",
          }}
        />
        {/* Scanline hint */}
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-sky-500/[0.02] to-transparent" />

        {plot.overlays.map((o) => {
          if (o.kind === "predicted_change" && !showPred) return null;
          if (o.kind === "weak_hint" && !showWeak) return null;
          if (o.kind === "stable_forest" && !showS2) return null;
          if (o.kind === "water" && !showS2) return null;
          return (
            <div
              key={o.id}
              title={o.label}
              className="absolute rounded-md border border-white/10 backdrop-blur-[1px] transition"
              style={{
                left: `${o.x}%`,
                top: `${o.y}%`,
                width: `${o.w}%`,
                height: `${o.h}%`,
                backgroundColor: o.color,
                opacity: o.opacity,
                boxShadow: showEmb ? "0 0 20px rgba(56,189,248,0.15)" : undefined,
              }}
            />
          );
        })}

        <div className="absolute bottom-3 left-3 right-3 flex flex-wrap items-end justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            {LEGEND.map((item) => (
              <div
                key={item.kind}
                className="flex items-center gap-1.5 rounded border border-slate-800/80 bg-obsidian-950/90 px-2 py-1 text-[10px] font-medium text-slate-400"
              >
                <span
                  className="h-2 w-2 rounded-sm"
                  style={{ backgroundColor: item.color }}
                />
                {item.label}
              </div>
            ))}
          </div>
          <div className="rounded border border-slate-800 bg-obsidian-950/90 px-2 py-1 font-mono text-[10px] text-slate-500">
            {plot.areaHa.toLocaleString()} ha · forest {plot.forestCoverPct}%
          </div>
        </div>
      </div>
    </div>
  );
}
