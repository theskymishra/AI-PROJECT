import { CircleAlert, RefreshCw, ShieldCheck } from "lucide-react";
import { useCallback, useState } from "react";

import { StatusBadge } from "@/components/layout/StatusBadge";
import { requestAllocation, toApiError } from "@/services/api";
import { useSimulation } from "@/store/SimulationProvider";
import type { CSPResult } from "@/types";

export function ResourcesPage() {
  const { snapshot, error: streamError } = useSimulation();
  const [result, setResult] = useState<CSPResult | null>(null);
  const [pending, setPending] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (apply: boolean) => {
    if (apply) setApplying(true);
    else setPending(true);
    setError(null);
    try {
      setResult(await requestAllocation({ apply }));
    } catch (caught) {
      const apiError = toApiError(caught);
      setError(`${apiError.message} ${apiError.hint}`);
    } finally {
      setPending(false);
      setApplying(false);
    }
  }, []);

  if (!snapshot) {
    return <div className="py-10 text-center text-[13px] text-fg-muted">{streamError?.hint ?? "Loading…"}</div>;
  }

  const active = snapshot.emergencies.filter(
    (e) => e.status !== "RESOLVED" && e.status !== "UNRESOLVABLE",
  );

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-fg">Resource Allocation</h2>
          <p className="mt-0.5 text-[13px] text-fg-muted">
            Phase 7 CSP: emergencies → ambulances → hospitals, subject to capacity, availability and safe A* routes.
          </p>
        </div>
        <StatusBadge tone="info">CSP</StatusBadge>
      </div>

      {error && (
        <div role="alert" className="flex items-start gap-3 rounded-panel border border-crit/40 bg-crit/10 p-4 text-[12px] text-fg">
          <CircleAlert aria-hidden="true" className="mt-0.5 size-4 text-crit" />{error}
        </div>
      )}

      <section className="rounded-panel border border-border bg-panel p-4">
        <div className="grid gap-3 sm:grid-cols-4">
          <Metric label="Active emergencies" value={active.length} />
          <Metric label="Available ambulances" value={snapshot.ambulances.filter((a) => a.status === "AVAILABLE").length} />
          <Metric label="Open hospitals" value={snapshot.hospitals.filter((h) => h.available_beds > 0).length} />
          <Metric label="Patients awaiting transport" value={snapshot.stats.patients_awaiting_transport} />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" onClick={() => void run(false)} disabled={pending || applying}
            className="inline-flex items-center gap-1.5 rounded-panel border border-border bg-panel-2 px-3 py-2 text-2xs uppercase tracking-wide text-fg-muted hover:text-fg disabled:opacity-40">
            <RefreshCw aria-hidden="true" className={`size-3.5 ${pending ? "animate-spin" : ""}`} /> Preview allocation
          </button>
          <button type="button" onClick={() => void run(true)} disabled={pending || applying}
            className="inline-flex items-center gap-1.5 rounded-panel border border-safe/40 bg-safe/10 px-3 py-2 text-2xs uppercase tracking-wide text-fg hover:bg-safe/20 disabled:opacity-40">
            <ShieldCheck aria-hidden="true" className="size-3.5" /> Apply allocation
          </button>
        </div>
        <p className="mt-3 text-[11px] text-fg-muted">
          Preview runs the real solver without changing the simulation. Apply commits the returned ambulance/hospital assignments.
        </p>
      </section>

      <section className="rounded-panel border border-border bg-panel p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-fg">Assignments</h3>
          {result && <StatusBadge tone={result.status === "SOLVED" ? "safe" : result.status === "PARTIAL" ? "warn" : "crit"}>{result.status}</StatusBadge>}
        </div>
        {!result ? (
          <p className="text-[12px] text-fg-muted">Run Preview allocation to inspect the CSP solution and search trace.</p>
        ) : Object.keys(result.assignments).length === 0 ? (
          <p className="text-[12px] text-fg-muted">No assignments were produced. {Object.keys(result.unassigned).length ? "See unassigned emergencies below." : "There are no unassigned active emergencies."}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[12px]">
              <thead className="text-2xs uppercase tracking-wide text-fg-muted"><tr><th className="pb-2">Emergency</th><th className="pb-2">Ambulance</th><th className="pb-2">Hospital</th></tr></thead>
              <tbody>{Object.entries(result.assignments).map(([id, assignment]) => (
                <tr key={id} className="border-t border-border"><td className="py-2 font-mono text-fg">{id}</td><td className="py-2 font-mono text-fg">{assignment.ambulance_id}</td><td className="py-2 font-mono text-fg">{assignment.hospital_id}</td></tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>

      {result && (
        <>
          <section className="rounded-panel border border-border bg-panel p-4">
            <div className="grid gap-3 sm:grid-cols-5">
              <Metric label="Constraints checked" value={result.constraints_checked} />
              <Metric label="Conflicts" value={result.conflicts} />
              <Metric label="Backtracks" value={result.backtracks} />
              <Metric label="Domain reductions" value={result.domain_reductions} />
              <Metric label="Execution ms" value={result.execution_ms} />
            </div>
          </section>

          {Object.keys(result.unassigned).length > 0 && (
            <section className="rounded-panel border border-border bg-panel p-4">
              <h3 className="mb-2 text-sm font-semibold text-fg">Unassigned emergencies</h3>
              <div className="space-y-1 text-[12px]">{Object.entries(result.unassigned).map(([id, reason]) => <div key={id} className="flex justify-between gap-4"><span className="font-mono text-fg">{id}</span><span className="text-fg-muted">{reason}</span></div>)}</div>
            </section>
          )}

          <section className="rounded-panel border border-border bg-panel p-4">
            <h3 className="mb-2 text-sm font-semibold text-fg">CSP decision trace</h3>
            <div className="max-h-80 space-y-1 overflow-auto pr-1">{result.trace.map((step, index) => (
              <div key={`${step.step}-${index}`} className="grid grid-cols-[42px_70px_1fr] gap-2 border-b border-border/60 py-1.5 text-[11px]">
                <span className="font-mono text-fg-muted">#{step.step}</span>
                <span className="font-mono text-fg">{step.outcome}</span>
                <span className="text-fg-muted"><span className="font-mono text-fg">{step.variable}</span> · {step.value} · {step.reason}</span>
              </div>
            ))}</div>
          </section>
        </>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-panel border border-border bg-bg p-3"><div className="text-2xs uppercase tracking-wide text-fg-muted">{label}</div><div className="mt-1 font-mono text-xl text-fg">{value}</div></div>;
}
