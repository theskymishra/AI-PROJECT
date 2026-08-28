/**
 * Top header bar.
 *
 * The brief specifies Scenario / Simulation / Simulation Time / System Health /
 * Reset. Only System Health has a real data source in Phase 1, so only System
 * Health renders. The rest arrive in Phase 2 together with the simulation
 * clock that feeds them; a header full of dashes would be decoration.
 */

import { RefreshCw } from "lucide-react";

import { StatusBadge } from "@/components/layout/StatusBadge";
import type { BackendHealth } from "@/hooks/useBackendHealth";

interface HeaderProps {
  backend: BackendHealth;
}

function ConnectionBadge({ state }: { state: BackendHealth["state"] }) {
  if (state === "online") return <StatusBadge tone="safe">Online</StatusBadge>;
  if (state === "checking")
    return (
      <StatusBadge tone="info" pulse>
        Checking
      </StatusBadge>
    );
  return <StatusBadge tone="crit">Offline</StatusBadge>;
}

export function Header({ backend }: HeaderProps) {
  const { health, state, latencyMs, refresh } = backend;

  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-6 border-b border-border bg-panel px-5">
      <div className="min-w-0">
        <h1 className="truncate text-[15px] font-semibold text-fg">
          {health?.full_name ?? "AI-Driven Disaster Evacuation & Emergency Response System"}
        </h1>
        <p className="truncate text-2xs text-fg-muted">
          {health?.tagline ?? "Intelligent emergency response under uncertainty."}
        </p>
      </div>

      <div className="flex shrink-0 items-center gap-5">
        <div className="flex flex-col items-end gap-1">
          <span className="text-2xs tracking-wide text-fg-muted uppercase">
            System Health
          </span>
          <ConnectionBadge state={state} />
        </div>

        {latencyMs !== null && (
          <div className="flex flex-col items-end gap-1">
            <span className="text-2xs tracking-wide text-fg-muted uppercase">
              Latency
            </span>
            <span className="font-mono text-[13px] text-fg">{latencyMs} ms</span>
          </div>
        )}

        {health && (
          <div className="flex flex-col items-end gap-1">
            <span className="text-2xs tracking-wide text-fg-muted uppercase">
              Version
            </span>
            <span className="font-mono text-[13px] text-fg">v{health.version}</span>
          </div>
        )}

        <button
          type="button"
          onClick={refresh}
          className="inline-flex items-center gap-1.5 rounded-panel border border-border bg-panel-2 px-2.5 py-1.5 text-2xs tracking-wide text-fg-muted uppercase transition-colors duration-150 hover:border-info/50 hover:text-fg"
        >
          <RefreshCw
            aria-hidden="true"
            className={`size-3.5 ${state === "checking" ? "animate-spin" : ""}`}
          />
          Re-check
        </button>
      </div>
    </header>
  );
}
