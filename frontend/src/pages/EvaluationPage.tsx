import { BarChart3, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { StatusBadge } from "@/components/layout/StatusBadge";
import { getEvaluationReport, toApiError } from "@/services/api";
import type { EvaluationResult } from "@/types";

export function EvaluationPage() {
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setPending(true);
    setError(null);
    try { setResult(await getEvaluationReport()); }
    catch (caught) { const e = toApiError(caught); setError(`${e.message} ${e.hint}`); }
    finally { setPending(false); }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const tone = result?.readiness === "READY" ? "safe" : result?.readiness === "ATTENTION" ? "warn" : "info";

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-fg">Response Evaluation</h2>
          <p className="mt-0.5 text-[13px] text-fg-muted">Phase 13 evaluates response readiness and AI performance indicators from the current simulation state.</p>
        </div>
        <StatusBadge tone={tone}>{result?.readiness ?? "LOADING"}</StatusBadge>
      </div>

      {error && <div role="alert" className="rounded-panel border border-crit/40 bg-crit/10 p-4 text-[12px] text-fg">{error}</div>}

      <section className="rounded-panel border border-border bg-panel p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Active emergencies" value={result?.active_emergencies ?? "—"} />
          <Metric label="Assignment coverage" value={metric(result, "Assignment coverage")} />
          <Metric label="Ambulances" value={result ? `${result.ambulances_total - result.ambulances_available}/${result.ambulances_total} busy` : "—"} />
          <Metric label="Hospital beds" value={result ? `${result.beds_available}/${result.beds_total}` : "—"} />
        </div>
        <div className="mt-4 flex items-center justify-between gap-3">
          <div className="text-[12px] text-fg-muted">{result?.summary ?? "Loading response evaluation…"}</div>
          <button type="button" disabled={pending} onClick={() => void refresh()} className="inline-flex shrink-0 items-center gap-1.5 rounded-panel border border-border bg-panel-2 px-3 py-2 text-2xs uppercase tracking-wide text-fg-muted hover:text-fg disabled:opacity-40"><RefreshCw className="size-3.5" /> Refresh</button>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-panel border border-border bg-panel p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-medium"><BarChart3 className="size-4" /> Performance indicators</div>
          <div className="space-y-2">{result?.metrics.map((item) => <div key={item.name} className="rounded-panel border border-border bg-panel-2 p-3"><div className="flex items-center justify-between gap-3"><span className="text-[12px] font-medium">{item.name}</span><span className="font-mono text-[11px]">{item.value.toFixed(item.unit === "%" ? 1 : 0)} {item.unit}</span></div><p className="mt-1 text-[11px] text-fg-muted">{item.interpretation}</p></div>)}</div>
        </div>
        <div className="rounded-panel border border-border bg-panel p-4">
          <div className="mb-3 text-sm font-medium">Evaluation summary</div>
          <div className="grid grid-cols-2 gap-2 text-[11px]"> <Metric label="Resolved" value={result?.resolved_emergencies ?? "—"} /><Metric label="Unresolvable" value={result?.unresolvable_emergencies ?? "—"} /><Metric label="Assigned" value={result?.assigned_emergencies ?? "—"} /><Metric label="Unassigned" value={result?.unassigned_emergencies ?? "—"} /><Metric label="Audit events" value={result?.audit_events ?? "—"} /><Metric label="HTN actions" value={result?.plan_length ?? "—"} /></div>
        </div>
      </section>

      <section className="rounded-panel border border-border bg-panel p-4">
        <div className="mb-2 text-sm font-medium">Recommendations</div>
        <div className="space-y-2">{result?.recommendations.map((item) => <div key={item} className="rounded-panel border border-border bg-panel-2 p-3 text-[12px] text-fg-muted">• {item}</div>)}</div>
      </section>
    </div>
  );
}

function metric(result: EvaluationResult | null, name: string): string {
  const item = result?.metrics.find((candidate) => candidate.name === name);
  return item ? `${item.value.toFixed(1)}${item.unit}` : "—";
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded-panel border border-border bg-panel-2 p-3"><div className="text-2xs uppercase tracking-wide text-fg-muted">{label}</div><div className="mt-1 text-lg font-semibold text-fg">{value}</div></div>;
}
