import { Globe2 } from "lucide-react";
import { REGIONS } from "../data/mock";

export function RegionFilter({
  value,
  onChange,
}: {
  value: string;
  onChange: (region: string) => void;
}) {
  return (
    <div className="relative">
      <Globe2 className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="input appearance-none pl-9 pr-8 font-mono text-xs"
      >
        <option value="all">All regions</option>
        {REGIONS.map((r) => (
          <option key={r} value={r}>
            {r}
          </option>
        ))}
      </select>
    </div>
  );
}

export function regionMatches(plotRegion: string, filter: string): boolean {
  if (filter === "all") return true;
  return plotRegion === filter;
}
