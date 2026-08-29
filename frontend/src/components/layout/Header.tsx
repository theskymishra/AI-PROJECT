/**
 * Top header bar.
 *
 * Phase 1 rendered only System Health, because nothing else had a real data
 * source. Phase 2 adds Scenario, Simulation status and Simulation Time -- all
 * driven by the backend snapshot, none of them computed in the browser.
 *
 * The clock reads `clock.elapsed_label`, which the backend formats. Formatting
 * it here from the tick count would be a second implementation of the same
 * rule, free to drift; and a browser-side timer ticking between frames would
 * be a client-side simulation, which this project deliberately does not have.
 */

import type { ReactNode } from "react";

import { RefreshCw } from "lucide-react";

import { StatusBadge } from "@/components/layout/StatusBadge";
import type { BadgeTone } from "@/components/layout/StatusBadge";
import type { BackendHealth } from "@/hooks/useBackendHealth";
import type { StreamStatus } from "@/services/stream";
import { useSimulation } from "@/store/SimulationProvider";
import type { SimStatus } from "@/types";

interface HeaderProps {
  backend: BackendHealth;
}

const SIM_TONE: Record<SimStatus, BadgeTone> = {
  IDLE: "idle",
  RUNNING: "safe",
  PAUSED: "warn",
  COMPLETED: "info",
};

const STREAM_TONE: Record<StreamStatus, BadgeTone> = {
  connecting: "info",
  open: "safe",
  reconnecting: "warn",
  closed: "crit",
};

const STREAM_LABEL: Record<StreamStatus, string> = {
  connecting: "Connecting",
  open: "Live",
  reconnecting: "Reconnecting",
  closed: "Disconnected",
};

function Readout({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex shrink-0 flex-col items-end gap-1">
      <span className="text-2xs tracking-wide text-fg-muted uppercase">{label}</span>
      {children}
    </div>
  );
}

export function Header({ backend }: HeaderProps) {
  const { snapshot, streamStatus, refresh } = useSimulation();
  const { health, state, refresh: refreshHealth } = backend;

  const clock = snapshot?.clock;
  const scenario = snapshot?.scenario;

  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-6 border-b border-border bg-panel px-5">
      <div className="min-w-0">
        <h1 className="truncate text-[15px] font-semibold text-fg">
          {health?.full_name ??
            "AI-Driven Disaster Evacuation & Emergency Response System"}
        </h1>
        <p className="truncate text-2xs text-fg-muted">
          {health?.tagline ?? "Intelligent emergency response under uncertainty."}
        </p>
      </div>

      <div className="flex shrink-0 items-center gap-5">
        {scenario && (
          <Readout label="Scenario">
            <span className="font-mono text-[13px] text-fg">{scenario.label}</span>
          </Readout>
        )}

        {clock && (
          <Readout label="Simulation">
            <StatusBadge
              tone={SIM_TONE[clock.status]}
              pulse={clock.status === "RUNNING"}
            >
              {clock.status}
            </StatusBadge>
          </Readout>
        )}

        {clock && (
          <Readout label="Sim Time">
            <span className="font-mono text-[13px] text-fg">
              {clock.elapsed_label}
              <span className="ml-1.5 text-fg-muted">t{clock.tick}</span>
            </span>
          </Readout>
        )}

        <Readout label="Stream">
          <StatusBadge
            tone={STREAM_TONE[streamStatus]}
            pulse={streamStatus === "connecting" || streamStatus === "reconnecting"}
          >
            {STREAM_LABEL[streamStatus]}
          </StatusBadge>
        </Readout>

        <Readout label="System Health">
          {state === "online" ? (
            <StatusBadge tone="safe">Online</StatusBadge>
          ) : state === "checking" ? (
            <StatusBadge tone="info" pulse>
              Checking
            </StatusBadge>
          ) : (
            <StatusBadge tone="crit">Offline</StatusBadge>
          )}
        </Readout>

        <button
          type="button"
          onClick={() => {
            refreshHealth();
            void refresh();
          }}
          className="inline-flex items-center gap-1.5 rounded-panel border border-border bg-panel-2 px-2.5 py-1.5 text-2xs tracking-wide text-fg-muted uppercase transition-colors duration-150 hover:border-info/50 hover:text-fg"
        >
          <RefreshCw
            aria-hidden="true"
            className={`size-3.5 ${state === "checking" ? "animate-spin" : ""}`}
          />
          Refresh
        </button>
      </div>
    </header>
  );
}
