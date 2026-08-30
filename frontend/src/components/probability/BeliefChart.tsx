/**
 * Belief over time, as a stacked area chart.
 *
 * Rows come from the backend's belief_history: one row per tick, in the state
 * order the backend declares. Nothing is interpolated in the browser.
 */

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { FloodState, HMMResponse } from "@/types";

const SERIES: Array<{ state: FloodState; colour: string }> = [
  { state: "NORMAL", colour: "var(--color-safe)" },
  { state: "RISING", colour: "var(--color-info)" },
  { state: "HIGH", colour: "var(--color-warn)" },
  { state: "CRITICAL", colour: "var(--color-crit)" },
];

/** Cap on plotted points. A 500-tick run does not need 500 SVG nodes per band. */
const MAX_POINTS = 180;

export function BeliefChart({ hmm }: { hmm: HMMResponse | null }) {
  if (!hmm || hmm.belief_history.length < 2) {
    return (
      <section className="rounded-panel border border-border bg-panel p-4">
        <p className="text-[13px] text-fg-muted">
          Belief history appears once the simulation has run.
        </p>
      </section>
    );
  }

  const history = hmm.belief_history.slice(-MAX_POINTS);
  const offset = hmm.belief_history.length - history.length;

  const data = history.map((row, index) => ({
    tick: offset + index,
    NORMAL: row[0] ?? 0,
    RISING: row[1] ?? 0,
    HIGH: row[2] ?? 0,
    CRITICAL: row[3] ?? 0,
  }));

  return (
    <section className="rounded-panel border border-border bg-panel">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <h2 className="text-2xs font-medium tracking-wide text-fg-muted uppercase">
          Belief Over Time
        </h2>
        <span className="font-mono text-2xs text-fg-muted">
          last {history.length} ticks
        </span>
      </div>
      <div className="h-56 p-3" data-testid="belief-chart">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
            <CartesianGrid stroke="var(--color-border)" strokeDasharray="2 4" />
            <XAxis
              dataKey="tick"
              stroke="var(--color-fg-muted)"
              tick={{ fontSize: 11, fontFamily: "var(--font-mono)" }}
              tickLine={false}
            />
            <YAxis
              domain={[0, 1]}
              stroke="var(--color-fg-muted)"
              tick={{ fontSize: 11, fontFamily: "var(--font-mono)" }}
              tickLine={false}
              width={34}
            />
            <Tooltip
              contentStyle={{
                background: "var(--color-panel-2)",
                border: "1px solid var(--color-border)",
                borderRadius: 4,
                fontSize: 12,
              }}
              // Recharts 3 types the value as ValueType | undefined, so it
              // is narrowed here rather than cast away.
              formatter={(value) =>
                typeof value === "number" ? value.toFixed(3) : String(value ?? "")
              }
            />
            {SERIES.map(({ state, colour }) => (
              <Area
                key={state}
                type="monotone"
                dataKey={state}
                stackId="belief"
                stroke={colour}
                fill={colour}
                fillOpacity={0.5}
                isAnimationActive={false}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
