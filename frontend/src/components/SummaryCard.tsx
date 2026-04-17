import type { LucideIcon } from "lucide-react";
import { cn } from "../lib/cn";

export function SummaryCard({
  label,
  value,
  sub,
  icon: Icon,
  accent = "text-sky-400",
  highlight,
}: {
  label: string;
  value: string;
  sub?: string;
  icon: LucideIcon;
  accent?: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={cn(
        "panel p-4 transition",
        highlight && "ring-1 ring-sky-500/40 shadow-glow",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="label-upper">{label}</p>
          <p className="mt-2 font-mono text-2xl font-semibold tracking-tight text-white">
            {value}
          </p>
          {sub && (
            <p className="mt-1 text-xs text-slate-500">{sub}</p>
          )}
        </div>
        <div
          className={cn(
            "rounded-lg border border-slate-800 bg-obsidian-950 p-2.5",
            accent,
          )}
        >
          <Icon className="h-5 w-5" strokeWidth={1.75} />
        </div>
      </div>
    </div>
  );
}
