import { Globe2 } from "lucide-react";

export function RegionFilter({
  value,
  onChange,
  regions,
}: {
  value: string;
  onChange: (region: string) => void;
  /** When set (e.g. API-driven plots), filter options match plot regions. */
  regions?: string[];
}) {
  const options = regions?.length ? regions : [];
  return (
    <div className="relative">
      <Globe2 className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="input appearance-none pl-9 pr-8 font-mono text-xs"
      >
        <option value="all">All regions</option>
        {options.map((r) => (
          <option key={r} value={r}>
            {r.length > 48 ? `${r.slice(0, 45)}…` : r}
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
