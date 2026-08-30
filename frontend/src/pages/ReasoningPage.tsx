import { CircleAlert, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { FOLPanel } from "@/components/knowledge/FOLPanel";
import { InferencePanel } from "@/components/knowledge/InferencePanel";
import { StatusBadge } from "@/components/layout/StatusBadge";
import { requestFOL, requestInference, toApiError } from "@/services/api";
import { useSimulation } from "@/store/SimulationProvider";
import type { FOLResult, InferenceResult } from "@/types";

export function ReasoningPage() {
  const { snapshot, error: streamError } = useSimulation();
  const [inference, setInference] = useState<InferenceResult | null>(null);
  const [fol, setFol] = useState<FOLResult | null>(null);
  const [pending, setPending] = useState(false);
  const [queryPending, setQueryPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setPending(true);
    setError(null);
    try {
      setInference(await requestInference());
    } catch (caught) {
      const apiError = toApiError(caught);
      setError(`${apiError.message} ${apiError.hint}`);
    } finally {
      setPending(false);
    }
  }, []);

  const query = useCallback(async (value: string) => {
    setQueryPending(true);
    setError(null);
    try {
      setFol(await requestFOL(value));
    } catch (caught) {
      const apiError = toApiError(caught);
      setError(`${apiError.message} ${apiError.hint}`);
    } finally {
      setQueryPending(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => { void query("Unsafe(R) & Road(R)"); }, [query]);

  if (!snapshot) {
    return <div className="py-10 text-center text-[13px] text-fg-muted">{streamError?.hint ?? "Loading…"}</div>;
  }

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-fg">AI Reasoning</h2>
          <p className="mt-0.5 text-[13px] text-fg-muted">Facts → forward chaining → FOL queries → explainable symbolic conclusions.</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge tone="info">Live</StatusBadge>
          <button type="button" onClick={() => void refresh()} disabled={pending}
            className="inline-flex items-center gap-1.5 rounded-panel border border-border bg-panel-2 px-2.5 py-1.5 text-2xs uppercase tracking-wide text-fg-muted hover:text-fg disabled:opacity-40">
            <RefreshCw aria-hidden="true" className={`size-3.5 ${pending ? "animate-spin" : ""}`} /> Re-run
          </button>
        </div>
      </div>
      {error && <div role="alert" className="flex items-start gap-3 rounded-panel border border-crit/40 bg-crit/10 p-4 text-[12px] text-fg"><CircleAlert aria-hidden="true" className="mt-0.5 size-4 text-crit" />{error}</div>}
      <section className="rounded-panel border border-border bg-panel p-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <Metric label="Symbolic facts" value={inference?.initial_facts.length ?? 0} />
          <Metric label="Derived facts" value={inference?.derived_facts.length ?? 0} />
          <Metric label="Rules fired" value={inference?.steps.length ?? 0} />
        </div>
        <p className="mt-4 text-[12px] leading-relaxed text-fg-muted">
          Phase 5 supplies the numeric evidence. Phase 6 turns that evidence into explicit propositions such as <code className="font-mono text-fg">HighFailureProb(R17)</code>, derives <code className="font-mono text-fg">Unsafe(R17)</code> and <code className="font-mono text-fg">Avoid(R17)</code>, and exposes the derivation instead of hiding it inside the router.
        </p>
      </section>
      <InferencePanel result={inference} onRefresh={() => void refresh()} pending={pending} />
      <FOLPanel result={fol} onQuery={(value) => void query(value)} pending={queryPending} />
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-panel border border-border bg-bg p-3"><div className="text-2xs uppercase tracking-wide text-fg-muted">{label}</div><div className="mt-1 font-mono text-xl text-fg">{value}</div></div>;
}
