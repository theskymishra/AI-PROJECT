import { CheckCircle2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { StatusBadge } from "@/components/layout/StatusBadge";
import { getFinalReport, toApiError } from "@/services/api";
import type { FinalReportResult } from "@/types";

export function FinalReportPage() {
  const [result, setResult] = useState<FinalReportResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setPending(true);
    setError(null);
    try {
      setResult(await getFinalReport());
    } catch (caught) {
      const e = toApiError(caught);
      setError(`${e.message} ${e.hint}`);
    } finally {
      setPending(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const tone = result?.readiness === "READY"
    ? "safe"
    : result?.readiness === "ATTENTION"
      ? "warn"
      : "info";

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-fg">Final Project Report</h2>
          <p className="mt-0.5 text-[13px] text-fg-muted">
            Phase 14 final integration view for the complete AI-DERS academic simulation.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge tone={tone}>{result?.readiness ?? "LOADING"}</StatusBadge>
          <button
            type="button"
            disabled={pending}
            onClick={() => void refresh()}
            className="inline-flex items-center gap-1.5 rounded-panel border border-border bg-panel-2 px-3 py-2 text-2xs uppercase tracking-wide text-fg-muted hover:text-fg disabled:opacity-40"
          >
            <RefreshCw className="size-3.5" /> Refresh
          </button>
        </div>
      </div>

      {error && <div role="alert" className="rounded-panel border border-crit/40 bg-crit/10 p-4 text-[12px] text-fg">{error}</div>}

      {result && (
        <>
          <section className="rounded-panel border border-border bg-panel p-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Metric label="Build" value={`Phase ${result.phase}/${result.total_phases}`} />
              <Metric label="Scenario" value={result.scenario} />
              <Metric label="Simulation" value={`${result.simulation_status} · tick ${result.tick}`} />
              <Metric label="Replanning" value={result.replanning_required ? "REQUIRED" : "NOT REQUIRED"} />
            </div>
            <p className="mt-4 text-[12px] leading-5 text-fg-muted">{result.summary}</p>
          </section>

          <section className="rounded-panel border border-border bg-panel p-4">
            <div className="mb-3 text-sm font-medium">Simulation inventory</div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Metric label="Zones" value={result.zones} />
              <Metric label="Roads" value={result.roads} />
              <Metric label="Hospitals" value={result.hospitals} />
              <Metric label="Shelters" value={result.shelters} />
              <Metric label="Ambulances" value={result.ambulances} />
              <Metric label="Emergencies" value={result.emergencies} />
              <Metric label="Sensor history" value={result.sensor_readings} />
              <Metric label="Timeline events" value={result.timeline_events} />
            </div>
          </section>

          <section className="rounded-panel border border-border bg-panel p-4">
            <div className="mb-3 text-sm font-medium">Phase integration status</div>
            <div className="space-y-2">
              {result.subsystems.map((item) => (
                <div key={item.phase} className="grid gap-2 rounded-panel border border-border bg-panel-2 p-3 md:grid-cols-[55px_190px_1fr_auto] md:items-center">
                  <span className="font-mono text-[11px] text-fg-muted">P{item.phase}</span>
                  <span className="text-[12px] font-medium">{item.name}</span>
                  <span className="text-[11px] text-fg-muted">{item.evidence}</span>
                  <span className="font-mono text-[10px] uppercase">{item.status}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-panel border border-border bg-panel p-4">
            <div className="mb-3 text-sm font-medium">Final verification checks</div>
            <div className="space-y-2">
              {result.final_checks.map((check) => (
                <div key={check} className="flex gap-2 rounded-panel border border-border bg-panel-2 p-3 text-[12px] text-fg-muted">
                  <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
                  <span>{check}</span>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-panel border border-border bg-panel-2 p-3">
      <div className="text-2xs uppercase tracking-wide text-fg-muted">{label}</div>
      <div className="mt-1 text-lg font-semibold text-fg">{value}</div>
    </div>
  );
}
