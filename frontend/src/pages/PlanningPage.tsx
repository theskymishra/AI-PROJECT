import { CircleAlert, GitBranch, RefreshCw } from "lucide-react";
import { useCallback, useState } from "react";

import { StatusBadge } from "@/components/layout/StatusBadge";
import { requestPlanning, toApiError } from "@/services/api";
import { useSimulation } from "@/store/SimulationProvider";
import type { PlanNode, PlanResult } from "@/types";

export function PlanningPage() {
  const { snapshot, error: streamError } = useSimulation();
  const [result, setResult] = useState<PlanResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async () => {
    setPending(true);
    setError(null);
    try {
      setResult(await requestPlanning());
    } catch (caught) {
      const apiError = toApiError(caught);
      setError(`${apiError.message} ${apiError.hint}`);
    } finally {
      setPending(false);
    }
  }, []);

  if (!snapshot) {
    return <div className="py-10 text-center text-[13px] text-fg-muted">{streamError?.hint ?? "Loading…"}</div>;
  }

  // The simulation stream can briefly lag behind a successful planning/allocation
  // API call. Once a plan exists, derive the displayed assignment count from the
  // actual plan actions so the metric reflects the state the planner used.
  const plannedEmergencyIds = result
  ? new Set(
      result.actions
        .flatMap((action) => action.args)
        .filter((arg) => /^E\d+$/.test(arg)),
    )
  : null;

  const assignedCount = plannedEmergencyIds
    ? plannedEmergencyIds.size
    : snapshot.emergencies.filter(
        (e) =>
          e.assigned_ambulance &&
          e.assigned_hospital &&
          e.status !== "RESOLVED" &&
          e.status !== "UNRESOLVABLE",
      ).length;

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-fg">AI Response Planning</h2>
          <p className="mt-0.5 text-[13px] text-fg-muted">
            Phase 8 HTN planning: convert Phase 7 resource assignments into an ordered emergency-response plan.
          </p>
        </div>
        <StatusBadge tone="info">HTN</StatusBadge>
      </div>

      {error && (
        <div role="alert" className="flex items-start gap-3 rounded-panel border border-crit/40 bg-crit/10 p-4 text-[12px] text-fg">
          <CircleAlert aria-hidden="true" className="mt-0.5 size-4 text-crit" />{error}
        </div>
      )}

      <section className="rounded-panel border border-border bg-panel p-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <Metric label="Assigned emergencies" value={assignedCount} />
          <Metric label="Planned actions" value={result?.plan_length ?? 0} />
          <Metric label="Planner nodes expanded" value={result?.nodes_expanded ?? 0} />
        </div>
        <button
          type="button"
          onClick={() => void run()}
          disabled={pending}
          className="mt-4 inline-flex items-center gap-1.5 rounded-panel border border-border bg-panel-2 px-3 py-2 text-2xs uppercase tracking-wide text-fg-muted hover:text-fg disabled:opacity-40"
        >
          <RefreshCw aria-hidden="true" className={`size-3.5 ${pending ? "animate-spin" : ""}`} />
          Build response plan
        </button>
        <p className="mt-3 text-[11px] text-fg-muted">
          Planning is read-only. It does not dispatch ambulances, move patients, or modify the simulation.
        </p>
      </section>

      {result && (
        <>
          <section className="rounded-panel border border-border bg-panel p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-fg">Plan result</h3>
                <p className="mt-1 text-[11px] text-fg-muted">Goal: <span className="font-mono">{result.goal}</span></p>
              </div>
              <StatusBadge tone={result.status === "FOUND" ? "safe" : "crit"}>{result.status}</StatusBadge>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <Metric label="Plan length" value={result.plan_length} />
              <Metric label="Nodes expanded" value={result.nodes_expanded} />
              <Metric label="Execution ms" value={result.execution_ms} />
            </div>
          </section>

          {result.actions.length > 0 && (
            <section className="rounded-panel border border-border bg-panel p-4">
              <h3 className="mb-3 text-sm font-semibold text-fg">Ordered action sequence</h3>
              <div className="space-y-2">
                {result.actions.map((action, index) => (
                  <div key={`${index}-${action.name}`} className="rounded-panel border border-border bg-bg p-3">
                    <div className="flex gap-3">
                      <span className="font-mono text-[11px] text-fg-muted">{String(index + 1).padStart(2, "0")}</span>
                      <div className="min-w-0">
                        <div className="font-mono text-[12px] text-fg">{action.name}({action.args.join(", ")})</div>
                        <div className="mt-1 text-[11px] text-fg-muted">Pre: {action.preconditions.join(" ∧ ")}</div>
                        <div className="text-[11px] text-fg-muted">Add: {action.add_effects.join(", ") || "—"}</div>
                        <div className="text-[11px] text-fg-muted">Delete: {action.delete_effects.join(", ") || "—"}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {result.hierarchy && (
            <section className="rounded-panel border border-border bg-panel p-4">
              <div className="mb-3 flex items-center gap-2">
                <GitBranch aria-hidden="true" className="size-4 text-fg-muted" />
                <h3 className="text-sm font-semibold text-fg">Hierarchical task network</h3>
              </div>
              <PlanTree node={result.hierarchy} depth={0} />
            </section>
          )}
        </>
      )}
    </div>
  );
}

function PlanTree({ node, depth }: { node: PlanNode; depth: number }) {
  return (
    <div className="text-[11px]">
      <div className="flex items-center gap-2 border-b border-border/60 py-1.5" style={{ paddingLeft: `${depth * 18}px` }}>
        <span className="font-mono text-fg">{node.task}</span>
        <span className="text-fg-muted">{node.primitive ? "primitive" : `→ ${node.method}`}</span>
      </div>
      {node.children.map((child, index) => <PlanTree key={`${child.task}-${index}`} node={child} depth={depth + 1} />)}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-panel border border-border bg-bg p-3"><div className="text-2xs uppercase tracking-wide text-fg-muted">{label}</div><div className="mt-1 font-mono text-xl text-fg">{value}</div></div>;
}
