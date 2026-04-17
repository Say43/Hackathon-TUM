import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TimeSeriesPoint } from "../types";
import { cn } from "../lib/cn";

export type TimeSeriesMode = "ndvi" | "radar" | "both" | "embedding";

const MODE_LABEL: Record<TimeSeriesMode, string> = {
  ndvi: "Sentinel-2 NDVI (vegetation)",
  radar: "Sentinel-1 VV backscatter (dB)",
  both: "NDVI + radar overlay",
  embedding: "AEF embedding norm",
};

export function TimeSeriesChart({
  data,
  mode,
  changeStart,
  changeEnd,
  compact,
}: {
  data: TimeSeriesPoint[];
  mode: TimeSeriesMode;
  changeStart: string;
  changeEnd: string;
  compact?: boolean;
}) {
  const events = data.filter((d) => d.eventFlag).map((d) => d.month);
  const height = compact ? 200 : 320;

  return (
    <div className="w-full">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-xs font-medium text-slate-400">{MODE_LABEL[mode]}</p>
        {events[0] && (
          <span className="font-mono text-[10px] text-amber-400/90">
            Event marker: {events[0]}
          </span>
        )}
      </div>
      <div style={{ width: "100%", height }} className="min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis
              dataKey="month"
              tick={{ fill: "#64748b", fontSize: 9 }}
              tickLine={false}
              axisLine={{ stroke: "#334155" }}
              interval={compact ? 5 : 3}
            />
            <YAxis
              yAxisId="left"
              tick={{ fill: "#64748b", fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: "#334155" }}
              domain={mode === "radar" ? ["auto", "auto"] : [0, 1]}
              width={36}
            />
            {(mode === "both" || mode === "radar") && (
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fill: "#94a3b8", fontSize: 10 }}
                tickLine={false}
                axisLine={{ stroke: "#334155" }}
                width={36}
              />
            )}
            <Tooltip
              contentStyle={{
                backgroundColor: "#0f172a",
                border: "1px solid #334155",
                borderRadius: 8,
                fontSize: 12,
              }}
              labelStyle={{ color: "#e2e8f0" }}
            />
            <ReferenceLine
              yAxisId="left"
              x={changeStart}
              stroke="#38bdf8"
              strokeDasharray="4 4"
              label={{ value: "window", fill: "#64748b", fontSize: 10 }}
            />
            <ReferenceLine
              yAxisId="left"
              x={changeEnd}
              stroke="#38bdf8"
              strokeDasharray="4 4"
            />
            {(mode === "ndvi" || mode === "both") && (
              <Area
                yAxisId="left"
                type="monotone"
                dataKey="sentinel2Ndvi"
                stroke="#22c55e"
                fill="url(#ndviFill)"
                strokeWidth={2}
                name="NDVI"
              />
            )}
            {(mode === "radar" || mode === "both") && (
              <Line
                yAxisId={mode === "both" ? "right" : "left"}
                type="monotone"
                dataKey="sentinel1Vvdb"
                stroke="#f97316"
                dot={false}
                strokeWidth={2}
                name="S1 VV (dB)"
              />
            )}
            {mode === "embedding" && (
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="embeddingNorm"
                stroke="#a78bfa"
                dot={false}
                strokeWidth={2}
                name="AEF norm"
              />
            )}
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="weakLabelAggregate"
              stroke="#94a3b8"
              strokeDasharray="5 5"
              dot={false}
              strokeWidth={1}
              name="Weak label agg."
            />
            {data
              .filter((d) => d.eventFlag)
              .map((d) => (
                <ReferenceLine
                  key={d.month}
                  yAxisId="left"
                  x={d.month}
                  stroke="#fbbf24"
                  strokeWidth={2}
                  label={{ value: "Δ", fill: "#fbbf24", fontSize: 11 }}
                />
              ))}
            <defs>
              <linearGradient id="ndviFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#22c55e" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
              </linearGradient>
            </defs>
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className={cn("mt-2 text-[10px] text-slate-600", compact && "hidden sm:block")}>
        Shaded window: detected change interval {changeStart} → {changeEnd}. Weak label
        aggregate shown as dashed reference.
      </p>
    </div>
  );
}
