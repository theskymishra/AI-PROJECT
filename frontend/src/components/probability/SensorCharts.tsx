/**
 * Sensor readings over time.
 *
 * Raw gauge values from the simulation's sensor history. The observation
 * SYMBOL each reading produced is emitted with noise from the true hidden
 * state, which is why the symbol column and the metre reading do not always
 * agree -- that disagreement is what gives the HMM work to do.
 */

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { SensorReading } from "@/types";

const MAX_POINTS = 180;

export function SensorCharts({
  history,
  current,
}: {
  history: SensorReading[];
  current: SensorReading[];
}) {
  const gauge = history.filter((r) => r.sensor_id === "SEN6").slice(-MAX_POINTS);

  return (
    <section className="rounded-panel border border-border bg-panel">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <h2 className="text-2xs font-medium tracking-wide text-fg-muted uppercase">
          Sensors
        </h2>
        <span className="font-mono text-2xs text-fg-muted">
          SEN6 river gauge feeds the HMM
        </span>
      </div>

      <div className="h-44 p-3" data-testid="sensor-chart">
        {gauge.length < 2 ? (
          <p className="p-4 text-[13px] text-fg-muted">
            Readings appear once the simulation is running.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={gauge.map((r) => ({
                tick: r.tick,
                water: r.water_level_m,
                rain: r.rainfall_mm,
              }))}
              margin={{ top: 4, right: 8, bottom: 4, left: 0 }}
            >
              <CartesianGrid stroke="var(--color-border)" strokeDasharray="2 4" />
              <XAxis dataKey="tick" stroke="var(--color-fg-muted)"
                     tick={{ fontSize: 11, fontFamily: "var(--font-mono)" }}
                     tickLine={false} />
              <YAxis stroke="var(--color-fg-muted)"
                     tick={{ fontSize: 11, fontFamily: "var(--font-mono)" }}
                     tickLine={false} width={34} />
              <Tooltip
                contentStyle={{
                  background: "var(--color-panel-2)",
                  border: "1px solid var(--color-border)",
                  borderRadius: 4,
                  fontSize: 12,
                }}
              />
              <Line type="monotone" dataKey="water" stroke="var(--color-info)"
                    strokeWidth={2} dot={false} isAnimationActive={false}
                    name="water (m)" />
              <Line type="monotone" dataKey="rain" stroke="var(--color-warn)"
                    strokeWidth={1.5} dot={false} isAnimationActive={false}
                    name="rain (mm/h)" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="border-t border-border px-4 py-3">
        <div className="mb-2 text-2xs tracking-wide text-fg-muted uppercase">
          Latest emitted observations
        </div>
        <ul className="flex flex-col gap-0.5">
          {current.map((sensor) => (
            <li key={sensor.sensor_id}
                className="flex items-baseline justify-between gap-3 border-b border-border/60 py-1 last:border-b-0">
              <span className="font-mono text-2xs text-fg-muted">
                {sensor.sensor_id}
                {sensor.sensor_id === "SEN6" && (
                  <span className="ml-1.5 text-info">gauge</span>
                )}
              </span>
              <span className="font-mono text-2xs text-fg-muted">
                {sensor.water_level_m.toFixed(2)} m
              </span>
              <span className="font-mono text-2xs text-fg">
                {sensor.observation}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
