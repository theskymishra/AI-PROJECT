import { BrainCircuit, ChevronDown, FileSearch, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { StatusBadge } from "@/components/layout/StatusBadge";
import { getExplainabilityReport, toApiError } from "@/services/api";
import type { EmergencyExplanation, ExplainabilityResult } from "@/types";

export function ExplainabilityPage() {
  const [result, setResult] = useState<ExplainabilityResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setPending(true);
    setError(null);
    try {
      setResult(await getExplainabilityReport());
    } catch (caught) {
      const apiError = toApiError(caught);
      setError(`${apiError.message} ${apiError.hint}`);
    } finally {
      setPending(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-fg">AI Decision Explainability</h2>
          <p className="mt-0.5 text-[13px] text-fg-muted">Phase 12 exposes the reasoning chain behind allocation, planning, execution and monitoring decisions.</p>
        </div>
        <StatusBadge tone="info">READ ONLY</StatusBadge>
      </div>

      {error && <div role="alert" className="rounded-panel border border-crit/40 bg-crit/10 p-4 text-[12px] text-fg">{error}</div>}

      <section className="rounded-panel border border-border bg-panel p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Active explanations" value={result?.explanations.length ?? "—"} />
          <Metric label="Audit events" value={result?.audit_events ?? "—"} />
          <Metric label="HTN plan" value={result?.plan_status ?? "—"} />
          <Metric label="Plan actions" value={result?.plan_length ?? "—"} />
        </div>
        <div className="mt-4 flex items-center justify-between gap-3">
          <div className="text-[12px] text-fg-muted">{result?.summary ?? "Loading decision explanation…"}</div>
          <button type="button" disabled={pending} onClick={() => void refresh()} className="inline-flex shrink-0 items-center gap-1.5 rounded-panel border border-border bg-panel-2 px-3 py-2 text-2xs uppercase tracking-wide text-fg-muted hover:text-fg disabled:opacity-40"><RefreshCw className="size-3.5" /> Refresh</button>
        </div>
      </section>

      <section className="rounded-panel border border-border bg-panel p-4">
        <div className="mb-3 flex items-center gap-2 text-sm font-medium"><BrainCircuit className="size-4" /> AI decision chain</div>
        <div className="flex flex-wrap items-center gap-2">
          {result?.ai_chain.map((step, index) => <div key={step} className="flex items-center gap-2"><span className="rounded-panel border border-border bg-panel-2 px-3 py-2 text-[11px] font-medium">{step}</span>{index < (result.ai_chain.length - 1) && <ChevronDown className="hidden size-3 rotate-[-90deg] text-fg-muted sm:block" />}</div>)}
        </div>
      </section>

      <section className="flex flex-col gap-3">
        {result?.explanations.map((item) => <ExplanationCard key={item.emergency_id} item={item} />)}
        {result && result.explanations.length === 0 && <div className="rounded-panel border border-border bg-panel p-5 text-[12px] text-fg-muted">No active emergency requires an explanation at the current simulation tick.</div>}
      </section>
    </div>
  );
}

function ExplanationCard({ item }: { item: EmergencyExplanation }) {
  return (
    <article className="rounded-panel border border-border bg-panel p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2"><span className="font-mono text-xs">{item.emergency_id}</span><StatusBadge tone={item.decision === "CONTINUE CURRENT RESPONSE" ? "safe" : "warn"}>{item.decision}</StatusBadge></div>
          <div className="mt-2 text-[11px] text-fg-muted">Status: {item.status} · Severity: {item.severity ?? "—"} · Patients: {item.patients} · Ambulance: {item.ambulance_id ?? "—"} · Hospital: {item.hospital_id ?? "—"}</div>
        </div>
        <FileSearch className="size-4 text-fg-muted" />
      </div>
      <p className="mt-3 text-[12px] text-fg-muted">{item.rationale}</p>
      <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
        {item.steps.map((step) => <div key={step.component} className="rounded-panel border border-border bg-panel-2 p-3"><div className="text-2xs font-semibold uppercase tracking-wide text-fg-muted">{step.component}</div><div className="mt-1 text-[12px] font-medium text-fg">{step.decision}</div><p className="mt-1.5 text-[11px] text-fg-muted">{step.rationale}</p><div className="mt-2 space-y-1">{step.evidence.map((evidence) => <div key={evidence} className="font-mono text-[10px] text-fg-muted">{evidence}</div>)}</div></div>)}
      </div>
    </article>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded-panel border border-border bg-panel-2 p-3"><div className="text-2xs uppercase tracking-wide text-fg-muted">{label}</div><div className="mt-1 text-lg font-semibold text-fg">{value}</div></div>;
}
