/**
 * Active alerts, newest first.
 *
 * Levels are the backend's AlertLevel enum: INFO, WARNING, CRITICAL.
 */

import { StatusBadge } from "@/components/layout/StatusBadge";
import type { BadgeTone } from "@/components/layout/StatusBadge";
import type { Alert, AlertLevel } from "@/types";

const LEVEL_TONE: Record<AlertLevel, BadgeTone> = {
  INFO: "info",
  WARNING: "warn",
  CRITICAL: "crit",
};

export function AlertPanel({ alerts }: { alerts: Alert[] }) {
  const newestFirst = [...alerts].reverse();

  return (
    <section className="flex min-h-0 flex-col rounded-panel border border-border bg-panel">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <h2 className="text-2xs font-medium tracking-wide text-fg-muted uppercase">
          Alerts
        </h2>
        <span className="font-mono text-2xs text-fg-muted">{alerts.length}</span>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {newestFirst.length === 0 ? (
          <p className="px-2 py-6 text-center text-[13px] text-fg-muted">
            No active alerts.
          </p>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {newestFirst.map((alert) => (
              <li
                key={alert.id}
                className="rounded-panel border border-border bg-panel-2 px-3 py-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="text-[13px] leading-snug text-fg">
                    {alert.title}
                  </span>
                  <StatusBadge tone={LEVEL_TONE[alert.level]}>
                    {alert.level}
                  </StatusBadge>
                </div>
                <p className="mt-1 text-2xs leading-snug text-fg-muted">
                  {alert.message}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
