/**
 * A single live figure.
 *
 * Every value shown here comes from the backend's `stats` block. Nothing is
 * computed in the browser and nothing is simulated: if the backend is stopped,
 * these numbers stop.
 */

import type { BadgeTone } from "@/components/layout/StatusBadge";

interface StatCardProps {
  label: string;
  value: number | string;
  /** Denominator for "3 / 4" style readings. */
  outOf?: number;
  /** Colour is meaning, never decoration. Omit for neutral figures. */
  tone?: BadgeTone;
  hint?: string;
}

const VALUE_TONE: Record<BadgeTone, string> = {
  info: "text-info",
  safe: "text-safe",
  warn: "text-warn",
  crit: "text-crit",
  idle: "text-idle",
};

export function StatCard({ label, value, outOf, tone, hint }: StatCardProps) {
  return (
    <div className="rounded-panel border border-border bg-panel px-3.5 py-3">
      <div className="text-2xs tracking-wide text-fg-muted uppercase">{label}</div>
      <div className="mt-1.5 flex items-baseline gap-1">
        <span
          className={`font-mono text-[20px] leading-none font-medium ${tone ? VALUE_TONE[tone] : "text-fg"}`}
        >
          {value}
        </span>
        {outOf !== undefined && (
          <span className="font-mono text-[13px] text-fg-muted">/ {outOf}</span>
        )}
      </div>
      {hint && <div className="mt-1 text-2xs text-fg-muted">{hint}</div>}
    </div>
  );
}
