/**
 * Sensor readings and the environment's hidden flood state.
 *
 * IMPORTANT LABELLING
 * -------------------
 * `true_flood_state` is ENVIRONMENT GROUND TRUTH, not an AI output. The agent
 * never observes it. Sensors emit noisy symbols drawn from
 * P(observation | true_flood_state), and the Phase 5 HMM will estimate this
 * value from those symbols alone.
 *
 * It is labelled "ground truth" on screen for exactly that reason: in Phase 5
 * the estimate appears beside it, and the gap between the two -- the filtering
 * lag -- is the thing worth demonstrating. Presenting this as an inference now
 * would make the Phase 5 HMM look like it is reading the answer off the
 * environment.
 */

import type { FloodState, SensorReading } from "@/types";

import type { BadgeTone } from "@/components/layout/StatusBadge";
import { StatusBadge } from "@/components/layout/StatusBadge";

const FLOOD_TONE: Record<FloodState, BadgeTone> = {
  NORMAL: "safe",
  RISING: "info",
  HIGH: "warn",
  CRITICAL: "crit",
};

interface EnvironmentPanelProps {
  rainfallMm: number;
  waterLevelM: number;
  riverLevelM: number;
  trueFloodState: FloodState;
  environmentVersion: number;
  sensors: SensorReading[];
}

export function EnvironmentPanel({
  rainfallMm,
  waterLevelM,
  riverLevelM,
  trueFloodState,
  environmentVersion,
  sensors,
}: EnvironmentPanelProps) {
  return (
    <section className="rounded-panel border border-border bg-panel">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <h2 className="text-2xs font-medium tracking-wide text-fg-muted uppercase">
          Environment
        </h2>
        <span className="font-mono text-2xs text-fg-muted">
          env v{environmentVersion}
        </span>
      </div>

      <div className="p-4">
        <div className="grid grid-cols-3 gap-3">
          <Reading label="Rainfall" value={rainfallMm.toFixed(1)} unit="mm/h" />
          <Reading label="Water level" value={waterLevelM.toFixed(2)} unit="m" />
          <Reading label="River level" value={riverLevelM.toFixed(2)} unit="m" />
        </div>

        <div className="mt-4 flex items-center justify-between gap-3 rounded-panel border border-border bg-panel-2 px-3 py-2">
          <div>
            <div className="text-2xs tracking-wide text-fg-muted uppercase">
              Flood state
            </div>
            <div className="text-2xs text-fg-muted">
              Ground truth &mdash; hidden from the agent
            </div>
          </div>
          <StatusBadge tone={FLOOD_TONE[trueFloodState]}>
            {trueFloodState}
          </StatusBadge>
        </div>

        <div className="mt-4">
          <div className="mb-2 text-2xs tracking-wide text-fg-muted uppercase">
            Sensors &mdash; emitted observations
          </div>
          {sensors.length === 0 ? (
            <p className="text-[13px] text-fg-muted">
              No readings yet. Sensors emit once the simulation is running.
            </p>
          ) : (
            <ul className="flex flex-col gap-0.5">
              {sensors.map((sensor) => (
                <li
                  key={sensor.sensor_id}
                  className="flex items-baseline justify-between gap-3 border-b border-border/60 py-1 last:border-b-0"
                >
                  <span className="font-mono text-2xs text-fg-muted">
                    {sensor.sensor_id}
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
          )}
        </div>
      </div>
    </section>
  );
}

function Reading({
  label,
  value,
  unit,
}: {
  label: string;
  value: string;
  unit: string;
}) {
  return (
    <div>
      <div className="text-2xs tracking-wide text-fg-muted uppercase">{label}</div>
      <div className="mt-1 flex items-baseline gap-1">
        <span className="font-mono text-[15px] text-fg">{value}</span>
        <span className="font-mono text-2xs text-fg-muted">{unit}</span>
      </div>
    </div>
  );
}
