/**
 * Semantic status pill.
 *
 * Colour is never the only signal: every badge also carries a label, so the
 * meaning survives a monochrome projector and a colour-blind viewer.
 */

import type { ReactNode } from "react";

export type BadgeTone = "info" | "safe" | "warn" | "crit" | "idle";

const TONE_CLASSES: Record<BadgeTone, string> = {
  info: "border-info/40 bg-info/10 text-info",
  safe: "border-safe/40 bg-safe/10 text-safe",
  warn: "border-warn/40 bg-warn/10 text-warn",
  crit: "border-crit/40 bg-crit/10 text-crit",
  idle: "border-idle/40 bg-idle/10 text-idle",
};

const DOT_CLASSES: Record<BadgeTone, string> = {
  info: "bg-info",
  safe: "bg-safe",
  warn: "bg-warn",
  crit: "bg-crit",
  idle: "bg-idle",
};

interface StatusBadgeProps {
  tone: BadgeTone;
  children: ReactNode;
  /** Slowly pulses the dot. Used for transient states such as "checking". */
  pulse?: boolean;
}

export function StatusBadge({ tone, children, pulse = false }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-panel border px-2 py-0.5 text-2xs font-medium tracking-wide uppercase ${TONE_CLASSES[tone]}`}
    >
      <span
        aria-hidden="true"
        className={`size-1.5 rounded-full ${DOT_CLASSES[tone]} ${pulse ? "animate-pulse" : ""}`}
      />
      {children}
    </span>
  );
}
