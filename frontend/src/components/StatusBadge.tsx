import type { ReactNode } from "react";
import { cn } from "../lib/cn";

type Tone = "sky" | "emerald" | "amber" | "rose" | "slate" | "violet";

const TONE: Record<Tone, string> = {
  sky: "border-sky-800/60 bg-sky-950/50 text-sky-300",
  emerald: "border-emerald-800/60 bg-emerald-950/40 text-emerald-300",
  amber: "border-amber-800/60 bg-amber-950/40 text-amber-200",
  rose: "border-rose-800/60 bg-rose-950/40 text-rose-300",
  slate: "border-slate-700 bg-obsidian-800 text-slate-300",
  violet: "border-violet-800/60 bg-violet-950/40 text-violet-200",
};

export function StatusBadge({
  tone = "slate",
  children,
  icon,
  className,
}: {
  tone?: Tone;
  children: ReactNode;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <span className={cn("chip", TONE[tone], className)}>
      {icon}
      {children}
    </span>
  );
}
