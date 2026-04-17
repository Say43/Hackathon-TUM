import { Bell, Search, User } from "lucide-react";
import { LAND_PLOTS } from "../data/mock";
import { StatusBadge } from "../components/StatusBadge";
import { cn } from "../lib/cn";

export function Topbar({
  search,
  onSearch,
  tileValue,
  onTileChange,
  monitoringActive,
  onToggleMonitoring,
}: {
  search: string;
  onSearch: (v: string) => void;
  tileValue: string;
  onTileChange: (tileId: string) => void;
  monitoringActive: boolean;
  onToggleMonitoring?: () => void;
}) {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-800/80 bg-obsidian-950/90 px-4 py-3 backdrop-blur-md">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-base font-semibold tracking-tight text-white">
            osapiens Deforestation Monitor
          </h1>
          <p className="text-[11px] text-slate-500">
            Earth observation · EUDR-aligned risk · Human validation
          </p>
        </div>

        <div className="flex flex-1 flex-wrap items-center justify-end gap-2 md:min-w-0">
          <div className="relative hidden min-w-[200px] max-w-md flex-1 md:block">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              value={search}
              onChange={(e) => onSearch(e.target.value)}
              placeholder="Search tile ID, region, plot…"
              className="input pl-9 text-xs"
            />
          </div>

          <select
            value={tileValue}
            onChange={(e) => onTileChange(e.target.value)}
            className={cn(
              "input max-w-[220px] font-mono text-xs",
              "hidden sm:block",
            )}
          >
            {LAND_PLOTS.map((p) => (
              <option key={p.id} value={p.tileId}>
                {p.tileId}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() => onToggleMonitoring?.()}
            className="rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-sky-500/50"
            title="Toggle monitoring pipeline"
          >
            <StatusBadge
              tone={monitoringActive ? "sky" : "slate"}
              icon={
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    monitoringActive ? "bg-sky-400 animate-pulse" : "bg-slate-500",
                  )}
                />
              }
            >
              {monitoringActive ? "Monitoring Active" : "Monitoring Paused"}
            </StatusBadge>
          </button>

          <button
            type="button"
            className="grid h-9 w-9 place-items-center rounded-lg border border-slate-800 bg-obsidian-900 text-slate-400 hover:text-white"
            aria-label="Notifications"
          >
            <Bell className="h-4 w-4" />
          </button>
          <div className="flex items-center gap-2 rounded-lg border border-slate-800 bg-obsidian-900 px-2 py-1">
            <div className="grid h-7 w-7 place-items-center rounded-md bg-slate-800 text-slate-400">
              <User className="h-4 w-4" />
            </div>
            <div className="hidden text-left sm:block">
              <p className="text-[11px] font-semibold text-slate-200">Reviewer</p>
              <p className="text-[10px] text-slate-500">Compliance</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
