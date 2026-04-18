import { CircleDot, Database, Server } from "lucide-react";
import type { HealthResponse } from "../types/aef";
import { API_BASE, IS_API_CONFIGURED } from "../lib/api";

export function Topbar({
  health,
  loading,
}: {
  health: HealthResponse | null;
  loading: boolean;
}) {
  const ok = health?.status === "ok";
  const tone = !IS_API_CONFIGURED
    ? "text-rose-300"
    : loading
      ? "text-slate-300"
      : ok
        ? "text-emerald-300"
        : "text-amber-300";
  const status = !IS_API_CONFIGURED
    ? "API URL not configured"
    : loading
      ? "Checking…"
      : health?.status === "unreachable"
        ? "API unreachable"
        : ok
          ? "API healthy"
          : "API degraded";
  return (
    <header className="sticky top-0 z-20 border-b border-slate-800/80 bg-obsidian-950/90 px-4 py-3 backdrop-blur-md">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-base font-semibold tracking-tight text-white">
            AlphaEarth Foundations Explorer
          </h1>
          <p className="text-[11px] text-slate-500">
            64-dim AEF embeddings · weak deforestation supervision · Makeathon
            2026
          </p>
        </div>

        <div className="flex items-center gap-2 text-[11px]">
          <div className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-obsidian-900 px-2 py-1">
            <Server className="h-3.5 w-3.5 text-slate-500" />
            <span className={tone}>
              <CircleDot className="mr-1 inline h-2.5 w-2.5" />
              {status}
            </span>
          </div>
          {IS_API_CONFIGURED && (
            <div
              className="hidden items-center gap-1.5 rounded-lg border border-slate-800 bg-obsidian-900 px-2 py-1 text-slate-500 md:flex"
              title="VITE_API_BASE_URL"
            >
              <Database className="h-3.5 w-3.5" />
              <span className="font-mono">{API_BASE}</span>
            </div>
          )}
          {health?.dataDir && (
            <div className="hidden max-w-[280px] items-center gap-1.5 truncate rounded-lg border border-slate-800 bg-obsidian-900 px-2 py-1 text-slate-500 lg:flex">
              <span className="truncate font-mono">{health.dataDir}</span>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
