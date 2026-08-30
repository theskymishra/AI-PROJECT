/**
 * Bayesian Network structure and posterior.
 *
 * Draws the two pathways explicitly, because the whole point of the design is
 * that live evidence reaches each road by two routes -- one through the
 * temporally-filtered FloodSeverity node, one straight through SurfaceWater --
 * and a diagram is the fastest way to make that legible.
 */

import type { BayesianResponse, FloodState } from "@/types";

const SEVERITY_COLOUR: Record<FloodState, string> = {
  NORMAL: "var(--color-safe)",
  RISING: "var(--color-info)",
  HIGH: "var(--color-warn)",
  CRITICAL: "var(--color-crit)",
};

export function BayesianNetwork({ bayes }: { bayes: BayesianResponse | null }) {
  if (!bayes) {
    return (
      <section className="rounded-panel border border-border bg-panel p-4">
        <p className="text-[13px] text-fg-muted">Running inference&hellip;</p>
      </section>
    );
  }

  return (
    <section className="rounded-panel border border-border bg-panel">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <h2 className="text-2xs font-medium tracking-wide text-fg-muted uppercase">
          Bayesian Network
        </h2>
        <span className="font-mono text-2xs text-fg-muted">
          {bayes.execution_ms.toFixed(2)} ms &middot; exact enumeration
        </span>
      </div>

      <div className="p-4">
        <svg viewBox="0 0 460 190" className="h-auto w-full" role="img"
             aria-label="Bayesian network structure: two pathways from evidence to road failure.">
          <defs>
            <marker id="bn-arrow" viewBox="0 0 10 10" refX="9" refY="5"
                    markerWidth="5" markerHeight="5" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--color-fg-muted)" />
            </marker>
          </defs>

          <Node x={20} y={20} label="Rainfall" evidence={bayes.evidence.Rainfall} />
          <Node x={20} y={80} label="WaterLevel" evidence={bayes.evidence.WaterLevel} />
          <Node x={165} y={20} label="FloodSeverity" />
          <Node x={165} y={110} label="SurfaceWater(r)" />
          <Node x={20} y={140} label="Elevation(r)" muted />
          <Node x={320} y={65} label="RoadFailure(r)" highlight />
          <Node x={320} y={140} label="RoadDamage(r)" muted />

          <Edge x1={70} y1={38} x2={165} y2={34} />
          <Edge x1={70} y1={44} x2={70} y2={80} />
          <Edge x1={100} y1={92} x2={165} y2={44} />
          <Edge x1={100} y1={98} x2={165} y2={120} />
          <Edge x1={92} y1={150} x2={165} y2={128} />
          <Edge x1={255} y1={38} x2={320} y2={72} />
          <Edge x1={255} y1={120} x2={320} y2={84} />
          <Edge x1={330} y1={135} x2={335} y2={95} />

          {/* Virtual evidence, dashed to mark it as a likelihood not a value. */}
          <line x1={205} y1={0} x2={205} y2={18} stroke="var(--color-info)"
                strokeWidth={1.5} strokeDasharray="3 3" />
          <text x={210} y={10} fill="var(--color-info)" fontSize={9}
                fontFamily="var(--font-mono)">
            {bayes.used_hmm_virtual_evidence ? "HMM \u03bb(s)" : "HMM detached"}
          </text>
        </svg>

        <div className="mt-4">
          <div className="mb-2 text-2xs tracking-wide text-fg-muted uppercase">
            P(FloodSeverity | evidence)
          </div>
          <ul data-testid="bn-severity" className="flex flex-col gap-1.5">
            {(Object.keys(bayes.flood_severity) as FloodState[]).map((state) => (
              <li key={state} className="flex items-center gap-3">
                <span className="w-16 shrink-0 font-mono text-2xs text-fg-muted">
                  {state}
                </span>
                <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-panel-2">
                  <span
                    className="block h-full"
                    style={{
                      width: `${Math.round(bayes.flood_severity[state] * 100)}%`,
                      background: SEVERITY_COLOUR[state],
                    }}
                  />
                </span>
                <span className="w-12 shrink-0 text-right font-mono text-2xs text-fg">
                  {(bayes.flood_severity[state] * 100).toFixed(1)}%
                </span>
              </li>
            ))}
          </ul>
        </div>

        <p className="mt-3 border-t border-border pt-3 text-2xs leading-relaxed text-fg-muted">
          Two live pathways reach every road. Rainfall and water level shape
          FloodSeverity, which the HMM belief then sharpens as virtual evidence.
          Separately the current gauge reading reaches each road through
          SurfaceWater, weighted by terrain, without passing through
          FloodSeverity at all. P(RoadFailure) uses a noisy-OR over its three
          parents: 11 parameters instead of 36 table rows.
        </p>
      </div>
    </section>
  );
}

function Node({
  x, y, label, evidence, highlight = false, muted = false,
}: {
  x: number; y: number; label: string;
  evidence?: string; highlight?: boolean; muted?: boolean;
}) {
  const stroke = highlight
    ? "var(--color-crit)"
    : evidence
      ? "var(--color-info)"
      : "var(--color-border)";
  return (
    <g>
      <rect x={x} y={y} width={evidence ? 88 : 92} height={evidence ? 34 : 26}
            rx={3} fill="var(--color-panel-2)" stroke={stroke} strokeWidth={1.5} />
      <text x={x + 8} y={y + 16} fontSize={10}
            fill={muted ? "var(--color-fg-muted)" : "var(--color-fg)"}
            fontFamily="var(--font-mono)">
        {label}
      </text>
      {evidence && (
        <text x={x + 8} y={y + 28} fontSize={9} fill="var(--color-info)"
              fontFamily="var(--font-mono)">
          = {evidence}
        </text>
      )}
    </g>
  );
}

function Edge({ x1, y1, x2, y2 }: { x1: number; y1: number; x2: number; y2: number }) {
  return (
    <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--color-fg-muted)"
          strokeWidth={1} markerEnd="url(#bn-arrow)" opacity={0.7} />
  );
}
