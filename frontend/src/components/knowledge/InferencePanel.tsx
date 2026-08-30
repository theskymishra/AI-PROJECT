import { useState } from "react";

import type { InferenceResult } from "@/types";

interface Props {
  result: InferenceResult | null;
  onRefresh: () => void;
  pending: boolean;
}

export function InferencePanel({ result, onRefresh, pending }: Props) {
  const [showAll, setShowAll] = useState(false);
  const steps = result?.steps ?? [];
  const visible = showAll ? steps : steps.slice(0, 12);

  return (
    <section className="rounded-panel border border-border bg-panel">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div>
          <h2 className="text-2xs font-medium tracking-wide text-fg-muted uppercase">Forward chaining</h2>
          <p className="mt-1 text-[12px] text-fg-muted">Facts → rules → derived facts until a fixed point.</p>
        </div>
        <button type="button" onClick={onRefresh} disabled={pending}
          className="rounded-panel border border-border bg-panel-2 px-2.5 py-1.5 text-2xs uppercase tracking-wide text-fg-muted hover:text-fg disabled:opacity-40">
          {pending ? "Running…" : "Re-run"}
        </button>
      </div>
      <div className="grid gap-4 p-4 lg:grid-cols-2">
        <div>
          <h3 className="text-2xs uppercase tracking-wide text-fg-muted">Initial facts</h3>
          <div className="mt-2 max-h-64 overflow-auto rounded-panel border border-border bg-bg p-3 font-mono text-[11px] text-fg-muted">
            {(result?.initial_facts ?? []).map((fact) => <div key={fact}>{fact}</div>)}
          </div>
        </div>
        <div>
          <h3 className="text-2xs uppercase tracking-wide text-fg-muted">Derived facts</h3>
          <div className="mt-2 max-h-64 overflow-auto rounded-panel border border-border bg-bg p-3 font-mono text-[11px] text-fg">
            {(result?.derived_facts ?? []).map((fact) => <div key={fact}>{fact}</div>)}
          </div>
        </div>
      </div>
      <div className="border-t border-border px-4 py-3">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-2xs uppercase tracking-wide text-fg-muted">Inference trace</h3>
          <span className="font-mono text-2xs text-fg-muted">{result?.iterations ?? 0} iterations · {result?.execution_ms ?? 0} ms</span>
        </div>
        <div className="flex flex-col gap-2">
          {visible.map((step, index) => (
            <div key={`${step.rule_name}-${index}`} className="rounded-panel border border-border bg-bg px-3 py-2">
              <div className="font-mono text-[11px] text-fg">{step.rule_name}</div>
              <div className="mt-1 text-[11px] text-fg-muted">{step.premises.join(" ∧ ")} → {step.conclusion}</div>
            </div>
          ))}
        </div>
        {steps.length > 12 && (
          <button type="button" onClick={() => setShowAll((value) => !value)} className="mt-3 text-2xs uppercase tracking-wide text-info">
            {showAll ? "Show less" : `Show all ${steps.length} steps`}
          </button>
        )}
      </div>
    </section>
  );
}
