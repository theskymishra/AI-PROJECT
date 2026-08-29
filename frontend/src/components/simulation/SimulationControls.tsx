/**
 * Simulation transport controls.
 *
 * Every button issues a real API call. The response carries the full snapshot,
 * which is applied immediately -- so the UI reflects the backend's actual
 * state, not an optimistic guess about what it is about to become.
 *
 * Which buttons are enabled follows the backend's SimStatus:
 *   IDLE       -> Start
 *   RUNNING    -> Pause
 *   PAUSED     -> Resume
 *   COMPLETED  -> Start (the engine resets itself first)
 * Reset is always available.
 */

import { Pause, Play, RotateCcw } from "lucide-react";

import { ALLOWED_SPEEDS } from "@/config";
import { useSimulation } from "@/store/SimulationProvider";
import type { SimStatus } from "@/types";

const BUTTON =
  "inline-flex items-center gap-1.5 rounded-panel border border-border bg-panel-2 px-3 py-1.5 " +
  "text-2xs font-medium tracking-wide uppercase transition-colors duration-150 " +
  "disabled:cursor-not-allowed disabled:opacity-40";

export function SimulationControls() {
  const {
    snapshot,
    commandPending,
    start,
    pause,
    resume,
    reset,
    changeSpeed,
    changeScenario,
  } = useSimulation();

  if (!snapshot) return null;

  const status: SimStatus = snapshot.clock.status;
  const busy = commandPending;
  const canStart = status === "IDLE" || status === "COMPLETED";

  return (
    <section className="flex flex-wrap items-center gap-x-5 gap-y-3 rounded-panel border border-border bg-panel px-4 py-3">
      {/* transport */}
      <div className="flex items-center gap-2">
        {status === "RUNNING" ? (
          <button
            type="button"
            onClick={() => void pause()}
            disabled={busy}
            className={`${BUTTON} text-warn hover:border-warn/50`}
          >
            <Pause aria-hidden="true" className="size-3.5" />
            Pause
          </button>
        ) : (
          <button
            type="button"
            onClick={() => void (canStart ? start() : resume())}
            disabled={busy}
            className={`${BUTTON} text-safe hover:border-safe/50`}
          >
            <Play aria-hidden="true" className="size-3.5" />
            {canStart ? "Start" : "Resume"}
          </button>
        )}

        <button
          type="button"
          onClick={() => void reset()}
          disabled={busy}
          className={`${BUTTON} text-fg-muted hover:border-info/50 hover:text-fg`}
        >
          <RotateCcw aria-hidden="true" className="size-3.5" />
          Reset
        </button>
      </div>

      <div aria-hidden="true" className="h-6 w-px bg-border" />

      {/* speed */}
      <div className="flex items-center gap-2">
        <span className="text-2xs tracking-wide text-fg-muted uppercase">Speed</span>
        <div
          role="group"
          aria-label="Simulation speed"
          className="flex overflow-hidden rounded-panel border border-border"
        >
          {ALLOWED_SPEEDS.map((speed) => {
            const active = snapshot.clock.speed === speed;
            return (
              <button
                key={speed}
                type="button"
                onClick={() => void changeSpeed(speed)}
                disabled={busy}
                aria-pressed={active}
                className={[
                  "px-2.5 py-1.5 font-mono text-2xs transition-colors duration-150",
                  "disabled:cursor-not-allowed disabled:opacity-40",
                  active
                    ? "bg-info/15 text-info"
                    : "bg-panel-2 text-fg-muted hover:text-fg",
                ].join(" ")}
              >
                {speed}x
              </button>
            );
          })}
        </div>
      </div>

      <div aria-hidden="true" className="h-6 w-px bg-border" />

      {/* scenario */}
      <div className="flex items-center gap-2">
        <label
          htmlFor="scenario-select"
          className="text-2xs tracking-wide text-fg-muted uppercase"
        >
          Scenario
        </label>
        <select
          id="scenario-select"
          value={snapshot.scenario.name}
          disabled={busy}
          onChange={(event) => void changeScenario(event.target.value)}
          className="rounded-panel border border-border bg-panel-2 px-2.5 py-1.5 text-[13px] text-fg transition-colors duration-150 hover:border-info/50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {snapshot.available_scenarios.map((scenario) => (
            <option key={scenario.name} value={scenario.name}>
              {scenario.label}
            </option>
          ))}
        </select>
      </div>

      <p className="w-full text-2xs leading-snug text-fg-muted">
        {snapshot.scenario.description}
      </p>
    </section>
  );
}
