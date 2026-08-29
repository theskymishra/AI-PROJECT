/**
 * A* expansion playback controls.
 *
 * Replays the order the BACKEND search expanded nodes in. The browser does not
 * re-run the search; frame k is the first k entries of expansion_order. That
 * keeps one implementation of A* in the project rather than two that can
 * disagree.
 */

import { Play, Pause, SkipForward, RotateCcw } from "lucide-react";

import type { SearchPlayback } from "@/hooks/useSearchPlayback";

const BUTTON =
  "inline-flex items-center gap-1.5 rounded-panel border border-border bg-panel-2 " +
  "px-2.5 py-1.5 text-2xs font-medium tracking-wide uppercase transition-colors " +
  "duration-150 disabled:cursor-not-allowed disabled:opacity-40";

export function SearchVisualizer({
  playback,
  expansionOrder,
}: {
  playback: SearchPlayback;
  expansionOrder: string[];
}) {
  const { state, step, totalSteps, revealed } = playback;
  const progress = totalSteps === 0 ? 0 : (step / totalSteps) * 100;
  const current = revealed.length > 0 ? revealed[revealed.length - 1] : null;

  return (
    <section className="rounded-panel border border-border bg-panel">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <h2 className="text-2xs font-medium tracking-wide text-fg-muted uppercase">
          Search Visualisation
        </h2>
        <span data-testid="playback-step" className="font-mono text-2xs text-fg-muted">
          {step} / {totalSteps} expanded
        </span>
      </div>

      <div className="flex flex-col gap-3 p-4">
        <div className="flex flex-wrap items-center gap-2">
          {state === "playing" ? (
            <button
              type="button"
              onClick={playback.pause}
              className={`${BUTTON} text-warn hover:border-warn/50`}
            >
              <Pause aria-hidden="true" className="size-3.5" />
              Pause
            </button>
          ) : (
            <button
              type="button"
              onClick={playback.play}
              disabled={totalSteps === 0}
              className={`${BUTTON} text-safe hover:border-safe/50`}
            >
              <Play aria-hidden="true" className="size-3.5" />
              {state === "finished" ? "Replay" : "Play"}
            </button>
          )}

          <button
            type="button"
            onClick={playback.stepForward}
            disabled={totalSteps === 0 || step >= totalSteps}
            className={`${BUTTON} text-fg-muted hover:border-info/50 hover:text-fg`}
          >
            <SkipForward aria-hidden="true" className="size-3.5" />
            Step
          </button>

          <button
            type="button"
            onClick={playback.reset}
            disabled={step === 0}
            className={`${BUTTON} text-fg-muted hover:border-info/50 hover:text-fg`}
          >
            <RotateCcw aria-hidden="true" className="size-3.5" />
            Reset
          </button>

          <button
            type="button"
            onClick={playback.showAll}
            disabled={totalSteps === 0 || step >= totalSteps}
            className={`${BUTTON} text-fg-muted hover:border-info/50 hover:text-fg`}
          >
            Show all
          </button>
        </div>

        <div
          className="h-1 w-full overflow-hidden rounded-full bg-panel-2"
          role="progressbar"
          aria-valuenow={step}
          aria-valuemin={0}
          aria-valuemax={totalSteps}
          aria-label="Search expansion progress"
        >
          <div
            className="h-full bg-info transition-[width] duration-150"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div>
          <div className="text-2xs tracking-wide text-fg-muted uppercase">
            Expansion order
          </div>
          <p
            data-testid="expansion-order"
            className="mt-1 font-mono text-2xs leading-relaxed break-words"
          >
            {expansionOrder.map((nodeId, index) => (
              <span
                key={`${nodeId}-${index}`}
                className={
                  index < step
                    ? nodeId === current
                      ? "text-info"
                      : "text-fg"
                    : "text-idle"
                }
              >
                {nodeId}
                {index < expansionOrder.length - 1 ? " \u00b7 " : ""}
              </span>
            ))}
          </p>
        </div>

        <p className="text-2xs leading-relaxed text-fg-muted">
          Nodes are replayed in the order the backend search expanded them.
          The browser does not re-run A*.
        </p>
      </div>
    </section>
  );
}
