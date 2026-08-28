/**
 * Dashboard.
 *
 * In later phases this becomes the operations overview: statistics, map, AI
 * decision panel, event timeline. In Phase 1 there is no simulation, so it
 * shows the thing that IS real and IS useful right now -- whether the
 * browser can actually reach the backend, how fast, and what that backend is.
 *
 * No stat cards reading "0" or "--". A number with nothing behind it is a
 * placeholder, and it teaches the reader to distrust the numbers that will be
 * real later.
 */

import { Activity, CircleAlert, Server } from "lucide-react";
import type { ReactNode } from "react";
import { useOutletContext } from "react-router";

import { StatusBadge } from "@/components/layout/StatusBadge";
import { API_URL, API_URL_IS_EXPLICIT, HEALTH_POLL_INTERVAL_MS } from "@/config";
import type { BackendHealth } from "@/hooks/useBackendHealth";

/* -------------------------------------------------------------------------- */

interface PanelProps {
  title: string;
  icon: ReactNode;
  action?: ReactNode;
  children: ReactNode;
}

function Panel({ title, icon, action, children }: PanelProps) {
  return (
    <section className="rounded-panel border border-border bg-panel">
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-2 text-fg-muted">
          {icon}
          <h2 className="text-2xs font-medium tracking-wide text-fg-muted uppercase">
            {title}
          </h2>
        </div>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

interface FieldProps {
  label: string;
  children: ReactNode;
  mono?: boolean;
}

function Field({ label, children, mono = true }: FieldProps) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-border/60 py-1.5 last:border-b-0">
      <dt className="text-2xs tracking-wide text-fg-muted uppercase">{label}</dt>
      <dd
        className={`min-w-0 truncate text-right text-[13px] text-fg ${mono ? "font-mono" : ""}`}
      >
        {children}
      </dd>
    </div>
  );
}

function formatUptime(seconds: number): string {
  const total = Math.floor(seconds);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(hours)}:${pad(minutes)}:${pad(secs)}`;
}

/* -------------------------------------------------------------------------- */

export function Dashboard() {
  const backend = useOutletContext<BackendHealth>();
  const { state, health, error, latencyMs, lastCheckedAt, refresh } = backend;

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4">
      <div>
        <h2 className="text-xl font-semibold text-fg">System Status</h2>
        <p className="mt-0.5 text-[13px] text-fg-muted">
          Phase 1 foundation. The simulation, map and AI subsystems arrive in
          later phases; this view reports the connection they will run over.
        </p>
      </div>

      {state === "offline" && error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-panel border border-crit/40 bg-crit/10 p-4"
        >
          <CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-crit" />
          <div className="min-w-0">
            <div className="text-[13px] font-medium text-fg">
              Cannot reach the backend
            </div>
            <p className="mt-1 font-mono text-2xs break-words text-fg-muted">
              {error.message}
            </p>
            <p className="mt-2 text-[13px] text-fg-muted">{error.hint}</p>
            <button
              type="button"
              onClick={refresh}
              className="mt-3 rounded-panel border border-border bg-panel-2 px-2.5 py-1.5 text-2xs tracking-wide text-fg uppercase transition-colors duration-150 hover:border-info/50"
            >
              Try again
            </button>
          </div>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Panel
          title="Connection"
          icon={<Activity aria-hidden="true" className="size-3.5" />}
          action={
            state === "online" ? (
              <StatusBadge tone="safe">Online</StatusBadge>
            ) : state === "checking" ? (
              <StatusBadge tone="info" pulse>
                Checking
              </StatusBadge>
            ) : (
              <StatusBadge tone="crit">Offline</StatusBadge>
            )
          }
        >
          <dl>
            <Field label="Endpoint">{API_URL}</Field>
            <Field label="Source">
              {API_URL_IS_EXPLICIT ? "VITE_API_URL" : "built-in fallback"}
            </Field>
            <Field label="Round trip">
              {latencyMs !== null ? `${latencyMs} ms` : "—"}
            </Field>
            <Field label="Last checked">
              {lastCheckedAt ? lastCheckedAt.toLocaleTimeString() : "—"}
            </Field>
            <Field label="Re-check every">
              {Math.round(HEALTH_POLL_INTERVAL_MS / 1000)} s
            </Field>
          </dl>
        </Panel>

        <Panel
          title="Backend"
          icon={<Server aria-hidden="true" className="size-3.5" />}
          action={
            health ? (
              <StatusBadge tone="info">
                Phase {health.phase}/{health.total_phases}
              </StatusBadge>
            ) : undefined
          }
        >
          {health ? (
            <dl>
              <Field label="Application" mono={false}>
                {health.app}
              </Field>
              <Field label="Version">v{health.version}</Field>
              <Field label="Uptime">{formatUptime(health.uptime_seconds)}</Field>
              <Field label="Status">{health.status.toUpperCase()}</Field>
            </dl>
          ) : (
            <p className="text-[13px] text-fg-muted">
              Build information becomes available once the backend responds.
            </p>
          )}
        </Panel>
      </div>

      <p className="text-2xs leading-relaxed text-fg-muted">
        AI-DERS is an academic AI simulation. It is not an operational
        emergency-management system, and no output it produces should be used to
        make real emergency decisions.
      </p>
    </div>
  );
}
