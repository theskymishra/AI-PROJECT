/**
 * Risk Analysis page.
 *
 * The whole Phase 5 chain on one screen:
 *
 *   noisy sensors -> HMM filter -> virtual evidence -> Bayesian Network
 *                -> per-road P(failure) -> A* cost
 *
 * WHAT-IF MODE detaches the HMM's virtual evidence and lets you clamp the
 * rainfall and water-level evidence. Without it the Rainfall -> WaterLevel
 * edges would be present but uninspectable, and an examiner asking "what do
 * those nodes do?" would have nothing to point at.
 *
 * Inference is re-run on demand, not on every tick: the numbers must hold
 * still long enough to read.
 */

import { CircleAlert, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { BayesianNetwork } from "@/components/probability/BayesianNetwork";
import { BeliefChart } from "@/components/probability/BeliefChart";
import { HMMPanel } from "@/components/probability/HMMPanel";
import { SensorCharts } from "@/components/probability/SensorCharts";
import { StatusBadge } from "@/components/layout/StatusBadge";
import { requestBayesian, requestHMM, toApiError } from "@/services/api";
import { useSimulation } from "@/store/SimulationProvider";
import type { BayesianResponse, EvidenceBand, HMMResponse } from "@/types";

const BANDS: EvidenceBand[] = ["LOW", "MED", "HIGH"];

export function RiskPage() {
  const { snapshot, error: streamError } = useSimulation();

  const [hmm, setHmm] = useState<HMMResponse | null>(null);
  const [bayes, setBayes] = useState<BayesianResponse | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [whatIf, setWhatIf] = useState(false);
  const [rainfall, setRainfall] = useState<EvidenceBand>("MED");
  const [waterLevel, setWaterLevel] = useState<EvidenceBand>("MED");

  const refresh = useCallback(async () => {
    setPending(true);
    setError(null);
    try {
      const [hmmResult, bayesResult] = await Promise.all([
        requestHMM(),
        requestBayesian(
          whatIf
            ? { rainfall, water_level: waterLevel, use_hmm: false }
            : {},
        ),
      ]);
      setHmm(hmmResult);
      setBayes(bayesResult);
    } catch (caught) {
      const apiError = toApiError(caught);
      setError(`${apiError.message} ${apiError.hint}`);
    } finally {
      setPending(false);
    }
  }, [whatIf, rainfall, waterLevel]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (!snapshot) {
    return (
      <div className="mx-auto max-w-3xl">
        {streamError ? (
          <div role="alert"
               className="flex items-start gap-3 rounded-panel border border-crit/40 bg-crit/10 p-4">
            <CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-crit" />
            <p className="text-[13px] text-fg-muted">{streamError.hint}</p>
          </div>
        ) : (
          <p className="py-10 text-center text-[13px] text-fg-muted">
            Loading&hellip;
          </p>
        )}
      </div>
    );
  }

  const riskiest = bayes?.riskiest_roads ?? [];

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-fg">Risk Analysis</h2>
          <p className="mt-0.5 text-[13px] text-fg-muted">
            Noisy sensors &rarr; HMM filter &rarr; Bayesian Network &rarr;
            per-road failure probability &rarr; A* route cost.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge tone={whatIf ? "warn" : "info"}>
            {whatIf ? "What-if" : "Live"}
          </StatusBadge>
          <button
            type="button"
            onClick={() => void refresh()}
            disabled={pending}
            className="inline-flex items-center gap-1.5 rounded-panel border border-border bg-panel-2 px-2.5 py-1.5 text-2xs tracking-wide text-fg-muted uppercase transition-colors duration-150 hover:border-info/50 hover:text-fg disabled:opacity-40"
          >
            <RefreshCw aria-hidden="true"
                       className={`size-3.5 ${pending ? "animate-spin" : ""}`} />
            Re-run
          </button>
        </div>
      </div>

      {error && (
        <div role="alert"
             className="rounded-panel border border-crit/40 bg-crit/10 px-4 py-2.5 text-[13px] text-fg">
          {error}
        </div>
      )}

      {/* what-if controls */}
      <section className="rounded-panel border border-border bg-panel px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
          <label className="flex items-center gap-2 text-2xs tracking-wide text-fg-muted uppercase">
            <input
              type="checkbox"
              checked={whatIf}
              onChange={(event) => setWhatIf(event.target.checked)}
              className="size-3.5 accent-[var(--color-info)]"
            />
            What-if mode
          </label>

          <BandSelect id="rain-band" label="Rainfall" value={rainfall}
                      disabled={!whatIf} onChange={setRainfall} />
          <BandSelect id="water-band" label="Water level" value={waterLevel}
                      disabled={!whatIf} onChange={setWaterLevel} />

          <p className="w-full text-2xs leading-relaxed text-fg-muted">
            {whatIf
              ? "The HMM's virtual evidence is detached and the evidence above is clamped, so the Rainfall \u2192 WaterLevel \u2192 FloodSeverity chain is running on its own. Road probabilities shown are hypothetical and are NOT written to the world."
              : `Live sensor evidence: Rainfall = ${bayes?.evidence.Rainfall ?? "\u2014"}, WaterLevel = ${bayes?.evidence.WaterLevel ?? "\u2014"}. The HMM belief enters as virtual evidence on FloodSeverity.`}
          </p>
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="flex flex-col gap-4">
          <HMMPanel hmm={hmm} trueFloodState={snapshot.environment.true_flood_state} />
          <BeliefChart hmm={hmm} />
        </div>
        <div className="flex flex-col gap-4">
          <BayesianNetwork bayes={bayes} />
          <SensorCharts history={snapshot.sensor_history} current={snapshot.sensors} />
        </div>
      </div>

      <section className="rounded-panel border border-border bg-panel">
        <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
          <h2 className="text-2xs font-medium tracking-wide text-fg-muted uppercase">
            Highest inferred failure probability
          </h2>
          <span className="font-mono text-2xs text-fg-muted">
            feeds the A* cost term &gamma; = 3
          </span>
        </div>
        <div className="p-4">
          {riskiest.length === 0 ? (
            <p className="text-[13px] text-fg-muted">No inference yet.</p>
          ) : (
            <ul data-testid="riskiest-roads" className="flex flex-col gap-1.5">
              {riskiest.map((road) => (
                <li key={road.road_id} className="flex items-center gap-3">
                  <span className="w-12 shrink-0 font-mono text-2xs text-fg">
                    {road.road_id}
                  </span>
                  <span className="w-12 shrink-0 font-mono text-2xs text-fg-muted">
                    {road.elevation_band}
                  </span>
                  <span className="h-2 flex-1 overflow-hidden rounded-full bg-panel-2">
                    <span className="block h-full bg-crit"
                          style={{ width: `${Math.round(road.probability * 100)}%` }} />
                  </span>
                  <span className="w-14 shrink-0 text-right font-mono text-[13px] text-fg">
                    {road.probability.toFixed(3)}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-3 border-t border-border pt-3 text-2xs leading-relaxed text-fg-muted">
            This probability is the <em>only</em> risk input to A*. Raw flood and
            damage levels are deliberately excluded from the cost function: they
            are environment ground truth and already inputs to this network, so
            reading them directly would bypass the inference chain and
            double-count the evidence.
          </p>
        </div>
      </section>
    </div>
  );
}

function BandSelect({
  id, label, value, disabled, onChange,
}: {
  id: string; label: string; value: EvidenceBand;
  disabled: boolean; onChange: (band: EvidenceBand) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <label htmlFor={id} className="text-2xs tracking-wide text-fg-muted uppercase">
        {label}
      </label>
      <select
        id={id}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value as EvidenceBand)}
        className="rounded-panel border border-border bg-panel-2 px-2.5 py-1.5 text-[13px] text-fg transition-colors duration-150 hover:border-info/50 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {BANDS.map((band) => (
          <option key={band} value={band}>{band}</option>
        ))}
      </select>
    </div>
  );
}
