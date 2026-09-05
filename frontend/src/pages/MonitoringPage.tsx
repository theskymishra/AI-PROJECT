import { Activity, RefreshCw, ShieldAlert, Stethoscope } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { StatusBadge } from "@/components/layout/StatusBadge";
import { getMonitoringStatus, getReplanCheck, toApiError } from "@/services/api";
import type { MonitoringResult } from "@/types";

export function MonitoringPage() {
  const [result, setResult] = useState<MonitoringResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (withPlan = false) => {
    setPending(true);
    setError(null);
    try {
      setResult(await (withPlan ? getReplanCheck() : getMonitoringStatus()));
    } catch (caught) {
      const apiError = toApiError(caught);
      setError(`${apiError.message} ${apiError.hint}`);
    } finally {
      setPending(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const health = result?.health;
  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-fg">Response Monitoring</h2>
          <p className="mt-0.5 text-[13px] text-fg-muted">Phase 11 continuously assesses live response health and detects conditions that may require replanning.</p>
        </div>
        <StatusBadge tone={result?.overall === "CLEAR" || result?.overall === "STABLE" ? "safe" : "warn"}>
          {result?.overall ?? "CHECKING"}
        </StatusBadge>
      </div>

      {error && <div role="alert" className="rounded-panel border border-crit/40 bg-crit/10 p-4 text-[12px] text-fg">{error}</div>}

      <section className="rounded-panel border border-border bg-panel p-4">
        <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <Metric label="Active emergencies" value={health?.active_emergencies ?? "—"} />
          <Metric label="Assigned" value={health?.assigned_emergencies ?? "—"} />
          <Metric label="Ambulances" value={health ? `${health.ambulances_available}/${health.ambulances_total}` : "—"} />
          <Metric label="Beds" value={health ? `${health.beds_available}/${health.beds_total}` : "—"} />
          <Metric label="Tick" value={result?.tick ?? "—"} />
          <Metric label="Replan" value={result?.replanning_required ? "REQUIRED" : "NO"} />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" disabled={pending} onClick={() => void refresh()} className="inline-flex items-center gap-1.5 rounded-panel border border-border bg-panel-2 px-3 py-2 text-2xs uppercase tracking-wide text-fg-muted hover:text-fg disabled:opacity-40"><RefreshCw className="size-3.5" /> Refresh assessment</button>
          <button type="button" disabled={pending} onClick={() => void refresh(true)} className="inline-flex items-center gap-1.5 rounded-panel border border-border bg-panel-2 px-3 py-2 text-2xs uppercase tracking-wide text-fg-muted hover:text-fg disabled:opacity-40"><Activity className="size-3.5" /> Check replanning</button>
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-panel border border-border bg-panel p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-medium"><ShieldAlert className="size-4" /> Attention</div>
          {result?.alerts.length ? <ul className="space-y-2 text-[12px] text-fg-muted">{result.alerts.map((item) => <li key={item}>• {item}</li>)}</ul> : <p className="text-[12px] text-fg-muted">No attention items detected.</p>}
        </section>
        <section className="rounded-panel border border-border bg-panel p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-medium"><Stethoscope className="size-4" /> Recommendations</div>
          {result?.recommendations.length ? <ul className="space-y-2 text-[12px] text-fg-muted">{result.recommendations.map((item) => <li key={item}>• {item}</li>)}</ul> : <p className="text-[12px] text-fg-muted">No recommendations.</p>}
        </section>
      </div>

      <section className="rounded-panel border border-border bg-panel p-4">
        <h3 className="mb-3 text-sm font-medium">Emergency monitoring</h3>
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {result?.items.map((item) => (
            <div key={item.emergency_id} className="rounded-panel border border-border bg-panel-2 p-3">
              <div className="flex items-center justify-between gap-2"><span className="font-mono text-xs">{item.emergency_id}</span><StatusBadge tone={item.attention === "STABLE" || item.attention === "READY" ? "safe" : item.attention === "ACTIVE" ? "info" : "warn"}>{item.attention}</StatusBadge></div>
              <div className="mt-2 text-[11px] text-fg-muted">Status: {item.status} · Ambulance: {item.ambulance_id ?? "—"} · Hospital: {item.hospital_id ?? "—"}</div>
              <p className="mt-2 text-[11px] text-fg-muted">{item.recommendation}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded-panel border border-border bg-panel-2 p-3"><div className="text-2xs uppercase tracking-wide text-fg-muted">{label}</div><div className="mt-1 text-lg font-semibold text-fg">{value}</div></div>;
}
