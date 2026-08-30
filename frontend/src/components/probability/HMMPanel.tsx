/**
 * Hidden Markov Model belief.
 *
 * Every number here is produced by the forward algorithm on the backend from
 * the noisy observation stream. The true flood state is shown alongside for
 * comparison and is labelled ENVIRONMENT GROUND TRUTH -- the agent never sees
 * it, and the gap between the two is the filtering lag, which is the thing
 * worth demonstrating.
 */

import { StatusBadge } from "@/components/layout/StatusBadge";
import type { BadgeTone } from "@/components/layout/StatusBadge";
import type { FloodState, HMMResponse } from "@/types";

const STATE_TONE: Record<FloodState, BadgeTone> = {
  NORMAL: "safe",
  RISING: "info",
  HIGH: "warn",
  CRITICAL: "crit",
};

const BAR_COLOUR: Record<FloodState, string> = {
  NORMAL: "bg-safe",
  RISING: "bg-info",
  HIGH: "bg-warn",
  CRITICAL: "bg-crit",
};

interface HMMPanelProps {
  hmm: HMMResponse | null;
  trueFloodState: FloodState;
}

export function HMMPanel({ hmm, trueFloodState }: HMMPanelProps) {
  if (!hmm) {
    return (
      <section className="rounded-panel border border-border bg-panel p-4">
        <p className="text-[13px] text-fg-muted">Loading belief&hellip;</p>
      </section>
    );
  }

  const lagging = hmm.most_likely !== trueFloodState;

  return (
    <section className="rounded-panel border border-border bg-panel">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <h2 className="text-2xs font-medium tracking-wide text-fg-muted uppercase">
          HMM &mdash; Estimated Flood State
        </h2>
        <span className="font-mono text-2xs text-fg-muted">
          {hmm.observation_history.length} observations
        </span>
      </div>

      <div className="p-4">
        <ul data-testid="hmm-belief" className="flex flex-col gap-2">
          {hmm.states.map((state) => {
            const probability = hmm.belief[state] ?? 0;
            return (
              <li key={state} className="flex items-center gap-3">
                <span className="w-16 shrink-0 font-mono text-2xs text-fg-muted">
                  {state}
                </span>
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-panel-2">
                  <span
                    data-testid={`hmm-bar-${state}`}
                    className={`block h-full ${BAR_COLOUR[state]} transition-[width] duration-150`}
                    style={{ width: `${Math.round(probability * 100)}%` }}
                  />
                </span>
                <span className="w-12 shrink-0 text-right font-mono text-[13px] text-fg">
                  {(probability * 100).toFixed(1)}%
                </span>
              </li>
            );
          })}
        </ul>

        <dl className="mt-4 grid grid-cols-2 gap-x-4 border-t border-border pt-3">
          <Field label="Estimated">
            <StatusBadge tone={STATE_TONE[hmm.most_likely]}>
              {hmm.most_likely}
            </StatusBadge>
          </Field>
          <Field label="Ground truth">
            <StatusBadge tone={STATE_TONE[trueFloodState]}>
              {trueFloodState}
            </StatusBadge>
          </Field>
          <Field label="Uncertainty">
            <span className="font-mono text-[13px] text-fg">
              {hmm.entropy.toFixed(2)} bits
            </span>
          </Field>
          <Field label="Step likelihood">
            <span className="font-mono text-[13px] text-fg">
              {hmm.step_likelihood.toFixed(3)}
            </span>
          </Field>
        </dl>

        <p
          data-testid="hmm-lag-note"
          className="mt-3 text-2xs leading-relaxed text-fg-muted"
        >
          {lagging
            ? `The filter estimates ${hmm.most_likely} while the environment is actually ${trueFloodState}. That gap is filtering lag: the agent only sees noisy sensor symbols, never the state itself.`
            : `The estimate currently agrees with the environment. It will not always: the sensors are noisy by design, so the belief lags real changes by a few ticks.`}
        </p>
        <p className="mt-2 text-2xs leading-relaxed text-fg-muted">
          Ground truth is shown for comparison only. It is environment state and
          is never an input to any decision the agent makes.
        </p>
      </div>
    </section>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2 border-b border-border/60 py-1.5">
      <dt className="text-2xs tracking-wide text-fg-muted uppercase">{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}
