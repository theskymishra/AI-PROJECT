import { Activity, CircleAlert, RefreshCw } from "lucide-react";
import { useCallback, useState } from "react";

import { StatusBadge } from "@/components/layout/StatusBadge";
import { requestEvidence, toApiError } from "@/services/api";
import type { EvidenceResult } from "@/types";

const STATES = ["NORMAL", "RISING", "HIGH", "CRITICAL"] as const;

export function EvidencePage() {
  const [result, setResult] = useState<EvidenceResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async () => {
    setPending(true);
    setError(null);
    try {
      setResult(await requestEvidence());
    } catch (caught) {
      const apiError = toApiError(caught);
      setError(`${apiError.message} ${apiError.hint}`);
    } finally {
      setPending(false);
    }
  }, []);

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-fg">Evidence Fusion</h2>
          <p className="mt-0.5 text-[13px] text-fg-muted">
            Phase 9 Dempster-Shafer reasoning: combine noisy sensor evidence while preserving uncertainty and ignorance.
          </p>
        </div>
        <StatusBadge tone="info">DST</StatusBadge>
      </div>

      {error && <div role="alert" className="flex items-start gap-3 rounded-panel border border-crit/40 bg-crit/10 p-4 text-[12px] text-fg"><CircleAlert aria-hidden="true" className="mt-0.5 size-4 text-crit" />{error}</div>}

      <section className="rounded-panel border border-border bg-panel p-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <Metric label="Evidence sources" value={result?.evidence_count ?? 0} />
          <Metric label="Conflict" value={result ? `${(result.conflict * 100).toFixed(1)}%` : "—"} />
          <Metric label="Execution ms" value={result?.execution_ms ?? 0} />
        </div>
        <button type="button" onClick={() => void run()} disabled={pending} className="mt-4 inline-flex items-center gap-1.5 rounded-panel border border-border bg-panel-2 px-3 py-2 text-2xs uppercase tracking-wide text-fg-muted hover:text-fg disabled:opacity-40">
          <RefreshCw aria-hidden="true" className={`size-3.5 ${pending ? "animate-spin" : ""}`} />
          Fuse current sensor evidence
        </button>
        <p className="mt-3 text-[11px] text-fg-muted">Read-only analysis. No simulation state is modified.</p>
      </section>

      {result && (
        <>
          <section className="rounded-panel border border-border bg-panel p-4">
            <div className="flex items-center justify-between gap-3">
              <div><h3 className="text-sm font-semibold text-fg">Combined evidence</h3><p className="mt-1 text-[11px] text-fg-muted">Belief and plausibility form an interval; pignistic probability provides a decision-oriented distribution.</p></div>
              <StatusBadge tone={result.status === "FUSED" ? "safe" : "info"}>{result.status}</StatusBadge>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-4">
              {STATES.map((state) => {
                  const pignistic = result.pignistic[state] ?? 0;
                  const belief = result.belief[state] ?? 0;
                  const plausibility = result.plausibility[state] ?? 0;

                  return (
                    <div key={state} className="rounded-panel border border-border bg-bg p-3">
                      <div className="text-2xs uppercase tracking-wide text-fg-muted">
                        {state}
                      </div>
                      <div className="mt-2 font-mono text-lg text-fg">
                        {(pignistic * 100).toFixed(1)}%
                      </div>
                      <div className="mt-1 text-[10px] text-fg-muted">
                        Bel {belief.toFixed(3)} · Pl {plausibility.toFixed(3)}
                      </div>
                    </div>
                  );
                })}
            </div>
          </section>

          <section className="rounded-panel border border-border bg-panel p-4">
            <div className="mb-3 flex items-center gap-2"><Activity aria-hidden="true" className="size-4 text-fg-muted" /><h3 className="text-sm font-semibold text-fg">Basic probability assignments</h3></div>
            {Object.entries(result.combined_masses).map(([set, mass]) => <div key={set} className="flex items-center justify-between border-b border-border/60 py-2 text-[11px]"><span className="font-mono text-fg">{set}</span><span className="font-mono text-fg-muted">{(mass * 100).toFixed(2)}%</span></div>)}
          </section>

          <section className="rounded-panel border border-border bg-panel p-4">
            <h3 className="mb-3 text-sm font-semibold text-fg">Sensor evidence</h3>
            <div className="space-y-2">{result.sources.map((source) => <div key={source.source_id} className="rounded-panel border border-border bg-bg p-3"><div className="flex justify-between gap-3 text-[11px]"><span className="font-mono text-fg">{source.source_id}</span><span className="text-fg-muted">t{source.tick} · reliability {(source.reliability * 100).toFixed(0)}%</span></div><div className="mt-1 font-mono text-[11px] text-fg-muted">{source.observation}</div><div className="mt-2 text-[10px] text-fg-muted">{Object.entries(source.masses).map(([key, value]) => `${key}: ${(value * 100).toFixed(1)}%`).join(" · ")}</div></div>)}</div>
          </section>
        </>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return <div className="rounded-panel border border-border bg-bg p-3"><div className="text-2xs uppercase tracking-wide text-fg-muted">{label}</div><div className="mt-1 font-mono text-xl text-fg">{value}</div></div>;
}
