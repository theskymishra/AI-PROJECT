import { CheckCircle2, CircleAlert, Play, RotateCcw, SkipForward } from "lucide-react";
import { useCallback, useState } from "react";

import { StatusBadge } from "@/components/layout/StatusBadge";
import {
  prepareExecution,
  executeAll,
  executeNextAction,
  resetExecution,
  toApiError,
} from "@/services/api";
import type { ExecutionResult } from "@/types";

export function ExecutionPage() {
  const [result, setResult] = useState<ExecutionResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (operation: () => Promise<ExecutionResult>) => {
    setPending(true);
    setError(null);
    try {
      setResult(await operation());
    } catch (caught) {
      const apiError = toApiError(caught);
      setError(`${apiError.message} ${apiError.hint}`);
    } finally {
      setPending(false);
    }
  }, []);

  const currentIndex = result?.next_action_index ?? result?.total_actions ?? 0;

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-fg">Plan Execution</h2>
          <p className="mt-0.5 text-[13px] text-fg-muted">
            Phase 10 executes the Phase 8 HTN response plan against the live simulation state.
          </p>
        </div>
        <StatusBadge tone={result?.status === "COMPLETED" ? "safe" : "info"}>
          {result?.status ?? "IDLE"}
        </StatusBadge>
      </div>

      {error && (
        <div role="alert" className="flex items-start gap-3 rounded-panel border border-crit/40 bg-crit/10 p-4 text-[12px] text-fg">
          <CircleAlert aria-hidden="true" className="mt-0.5 size-4 text-crit" />
          {error}
        </div>
      )}

      <section className="rounded-panel border border-border bg-panel p-4">
        <div className="grid gap-3 sm:grid-cols-4">
          <Metric label="Executed" value={`${result?.executed_count ?? 0}/${result?.total_actions ?? 0}`} />
          <Metric label="Next action" value={result?.next_action_index != null ? result.next_action_index + 1 : "—"} />
          <Metric label="Simulation tick" value={result?.tick ?? 0} />
          <Metric label="Active emergencies" value={result?.snapshot.stats.active_emergencies ?? "—"} />
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={pending}
            onClick={() => void run(prepareExecution)}
            className="inline-flex items-center gap-1.5 rounded-panel border border-border bg-panel-2 px-3 py-2 text-2xs uppercase tracking-wide text-fg-muted hover:text-fg disabled:opacity-40"
          >
            <RotateCcw aria-hidden="true" className="size-3.5" />
            Prepare execution plan
          </button>
          <button
            type="button"
            disabled={pending}
            onClick={() => void run(executeNextAction)}
            className="inline-flex items-center gap-1.5 rounded-panel border border-border bg-panel-2 px-3 py-2 text-2xs uppercase tracking-wide text-fg-muted hover:text-fg disabled:opacity-40"
          >
            <SkipForward aria-hidden="true" className="size-3.5" />
            Execute next action
          </button>
          <button
            type="button"
            disabled={pending}
            onClick={() => void run(executeAll)}
            className="inline-flex items-center gap-1.5 rounded-panel border border-border bg-panel-2 px-3 py-2 text-2xs uppercase tracking-wide text-fg-muted hover:text-fg disabled:opacity-40"
          >
            <Play aria-hidden="true" className="size-3.5" />
            Execute all remaining
          </button>
          <button
            type="button"
            disabled={pending}
            onClick={() => void run(resetExecution)}
            className="inline-flex items-center gap-1.5 rounded-panel border border-border bg-panel-2 px-3 py-2 text-2xs uppercase tracking-wide text-fg-muted hover:text-fg disabled:opacity-40"
          >
            <RotateCcw aria-hidden="true" className="size-3.5" />
            Clear session
          </button>
        </div>

        <p className="mt-3 text-[11px] text-fg-muted">
          Execution changes the simulation state. Clearing this execution session does not reset the simulation.
        </p>
      </section>

      {result && result.plan.length > 0 && (
        <section className="rounded-panel border border-border bg-panel p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-fg">HTN action sequence</h3>
              <p className="mt-1 text-[11px] text-fg-muted">Actions execute in the exact order produced by the Phase 8 planner.</p>
            </div>
            <span className="font-mono text-[11px] text-fg-muted">{currentIndex}/{result.total_actions}</span>
          </div>
          <div className="space-y-2">
            {result.plan.map((action, index) => {
              const executed = index < result.executed_count;
              const active = index === result.next_action_index;
              return (
                <div
                  key={`${index}-${action.name}-${action.args.join("-")}`}
                  className={`flex items-center gap-3 rounded-panel border p-3 ${active ? "border-fg/40 bg-panel-2" : "border-border bg-bg"}`}
                >
                  {executed ? (
                    <CheckCircle2 aria-hidden="true" className="size-4 text-safe" />
                  ) : (
                    <span className="flex size-4 items-center justify-center rounded-full border border-border font-mono text-[9px] text-fg-muted">
                      {index + 1}
                    </span>
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="font-mono text-[11px] text-fg">{action.name}</div>
                    <div className="mt-0.5 font-mono text-[10px] text-fg-muted">({action.args.join(", ")})</div>
                  </div>
                  <StatusBadge tone={executed ? "safe" : active ? "info" : "idle"}>
                    {executed ? "DONE" : active ? "NEXT" : "QUEUED"}
                  </StatusBadge>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {result && (
        <section className="grid gap-4 lg:grid-cols-3">
          <StateCard title="Emergencies" rows={result.snapshot.emergencies.map((item) => [item.id, item.status])} />
          <StateCard title="Ambulances" rows={result.snapshot.ambulances.map((item) => [item.id, `${item.status}${item.assigned_emergency ? ` → ${item.assigned_emergency}` : ""}`])} />
          <StateCard title="Hospitals" rows={result.snapshot.hospitals.map((item) => [item.id, `${item.available_beds}/${item.total_beds} beds`])} />
        </section>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-panel border border-border bg-bg p-3">
      <div className="text-2xs uppercase tracking-wide text-fg-muted">{label}</div>
      <div className="mt-1 font-mono text-xl text-fg">{value}</div>
    </div>
  );
}

function StateCard({ title, rows }: { title: string; rows: string[][] }) {
  return (
    <section className="rounded-panel border border-border bg-panel p-4">
      <h3 className="mb-3 text-sm font-semibold text-fg">{title}</h3>
      <div className="space-y-1.5">
        {rows.length === 0 ? (
          <div className="text-[11px] text-fg-muted">No entries.</div>
        ) : (
          rows.map(([id, value]) => (
            <div key={id} className="flex items-center justify-between gap-3 border-b border-border/60 py-2 text-[11px]">
              <span className="font-mono text-fg">{id}</span>
              <span className="font-mono text-fg-muted">{value}</span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
