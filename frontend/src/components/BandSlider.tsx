export function BandSlider({
  label,
  value,
  onChange,
  max = 63,
  accent = "sky",
  disabled,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  max?: number;
  accent?: "sky" | "violet" | "emerald" | "rose" | "slate";
  disabled?: boolean;
}) {
  const accentBg: Record<string, string> = {
    sky: "accent-sky-500",
    violet: "accent-violet-500",
    emerald: "accent-emerald-500",
    rose: "accent-rose-500",
    slate: "accent-slate-400",
  };
  const swatch: Record<string, string> = {
    sky: "bg-sky-500/20 text-sky-200 border-sky-700/60",
    violet: "bg-violet-500/20 text-violet-200 border-violet-700/60",
    emerald: "bg-emerald-500/20 text-emerald-200 border-emerald-700/60",
    rose: "bg-rose-500/20 text-rose-200 border-rose-700/60",
    slate: "bg-slate-700/40 text-slate-200 border-slate-700/60",
  };
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-slate-300">{label}</span>
        <span
          className={`rounded-md border px-1.5 py-0.5 font-mono text-[11px] ${swatch[accent]}`}
        >
          band {value}
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className={`w-full ${accentBg[accent]}`}
        disabled={disabled}
      />
    </div>
  );
}
