/**
 * Route query form and A* metrics readout.
 *
 * Every number shown is produced by the backend search on this request.
 * Nothing is estimated, and the request sends use_cache:false so the metrics
 * belong to this search rather than to whichever earlier call filled the
 * cache entry.
 */

import { Search } from "lucide-react";

import { StatusBadge } from "@/components/layout/StatusBadge";
import type { RouteCostWeights, RouteResult, WorldNode } from "@/types";

interface RoutePanelProps {
  nodes: WorldNode[];
  start: string;
  goal: string;
  onStartChange: (id: string) => void;
  onGoalChange: (id: string) => void;
  onSubmit: () => void;
  pending: boolean;
  route: RouteResult | null;
  weights: RouteCostWeights | null;
  error: string | null;
}

export function RoutePanel({
  nodes,
  start,
  goal,
  onStartChange,
  onGoalChange,
  onSubmit,
  pending,
  route,
  weights,
  error,
}: RoutePanelProps) {
  const sorted = [...nodes].sort((a, b) =>
    a.id.localeCompare(b.id, undefined, { numeric: true }),
  );

  return (
    <section className="rounded-panel border border-border bg-panel">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <h2 className="text-2xs font-medium tracking-wide text-fg-muted uppercase">
          A* Route Query
        </h2>
        {route && (
          <StatusBadge tone={route.found ? "safe" : "crit"}>
            {route.found ? "Route found" : "No route"}
          </StatusBadge>
        )}
      </div>

      <div className="flex flex-col gap-3 p-4">
        <div className="flex flex-wrap items-end gap-3">
          <NodeSelect
            id="route-start"
            label="Start"
            value={start}
            nodes={sorted}
            onChange={onStartChange}
          />
          <NodeSelect
            id="route-goal"
            label="Destination"
            value={goal}
            nodes={sorted}
            onChange={onGoalChange}
          />
          <button
            type="button"
            onClick={onSubmit}
            disabled={pending}
            className="inline-flex items-center gap-1.5 rounded-panel border border-border bg-panel-2 px-3 py-1.5 text-2xs font-medium tracking-wide text-info uppercase transition-colors duration-150 hover:border-info/50 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Search aria-hidden="true" className="size-3.5" />
            {pending ? "Searching" : "Find route"}
          </button>
        </div>

        {error && (
          <p role="alert" className="text-[13px] text-crit">
            {error}
          </p>
        )}

        {route && !route.found && route.failure_reason && (
          <p role="alert" className="text-[13px] text-warn">
            {route.failure_reason}
          </p>
        )}

        {route?.found && (
          <>
            <dl
              data-testid="route-metrics"
              className="grid grid-cols-2 gap-x-4 sm:grid-cols-3"
            >
              <Metric
                label="Path cost"
                value={route.total_cost.toFixed(2)}
                unit="risk-km"
              />
              <Metric
                label="Distance"
                value={route.total_distance.toFixed(2)}
                unit="km"
              />
              <Metric label="Hops" value={String(route.edges.length)} unit="roads" />
              <Metric
                label="Nodes expanded"
                value={String(route.nodes_expanded)}
                unit="of 24"
              />
              <Metric
                label="Nodes generated"
                value={String(route.nodes_generated)}
              />
              <Metric
                label="Execution"
                value={route.execution_ms.toFixed(3)}
                unit="ms"
              />
            </dl>

            <div>
              <div className="text-2xs tracking-wide text-fg-muted uppercase">
                Path
              </div>
              <p className="mt-1 font-mono text-[13px] break-words text-fg">
                {route.path.join(" \u2192 ")}
              </p>
            </div>

            {weights && (
              <p className="border-t border-border pt-2 text-2xs leading-relaxed text-fg-muted">
                Cost = distance &times; (1 + {weights.flood}&middot;flood +{" "}
                {weights.damage}&middot;damage + {weights.failure}&middot;P(fail)).
                P(fail) is 0 on every road until the Bayesian Network arrives in
                Phase 5, so routing today avoids flooded and damaged roads only.
              </p>
            )}
          </>
        )}
      </div>
    </section>
  );
}

function NodeSelect({
  id,
  label,
  value,
  nodes,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  nodes: WorldNode[];
  onChange: (id: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label
        htmlFor={id}
        className="text-2xs tracking-wide text-fg-muted uppercase"
      >
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="rounded-panel border border-border bg-panel-2 px-2.5 py-1.5 text-[13px] text-fg transition-colors duration-150 hover:border-info/50"
      >
        {nodes.map((node) => (
          <option key={node.id} value={node.id}>
            {node.id} &mdash; {node.name}
          </option>
        ))}
      </select>
    </div>
  );
}

function Metric({
  label,
  value,
  unit,
}: {
  label: string;
  value: string;
  unit?: string;
}) {
  return (
    <div className="border-b border-border/60 py-1.5">
      <dt className="text-2xs tracking-wide text-fg-muted uppercase">{label}</dt>
      <dd className="flex items-baseline gap-1">
        <span className="font-mono text-[15px] text-fg">{value}</span>
        {unit && <span className="font-mono text-2xs text-fg-muted">{unit}</span>}
      </dd>
    </div>
  );
}
