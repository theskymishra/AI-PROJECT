/**
 * Full-page disaster map.
 *
 * The map itself is the same component the dashboard embeds; only the
 * `interactive` flag differs. One implementation means the dashboard view can
 * never drift from the real one.
 */

import { CircleAlert } from "lucide-react";

import { DisasterMap } from "@/components/map/DisasterMap";
import { StatusBadge } from "@/components/layout/StatusBadge";
import { useSimulation } from "@/store/SimulationProvider";

export function DisasterMapPage() {
  const { snapshot, error, streamStatus } = useSimulation();

  if (!snapshot) {
    return (
      <div className="mx-auto max-w-3xl">
        {error ? (
          <div
            role="alert"
            className="flex items-start gap-3 rounded-panel border border-crit/40 bg-crit/10 p-4"
          >
            <CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-crit" />
            <div>
              <div className="text-[13px] font-medium text-fg">
                Cannot reach the backend
              </div>
              <p className="mt-1 text-[13px] text-fg-muted">{error.hint}</p>
            </div>
          </div>
        ) : (
          <p className="py-10 text-center text-[13px] text-fg-muted">
            Loading world&hellip;
          </p>
        )}
      </div>
    );
  }

  const { stats, environment, clock, scenario } = snapshot;

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-fg">Disaster Map</h2>
          <p className="mt-0.5 text-[13px] text-fg-muted">
            {scenario.label} &middot; tick {clock.tick} &middot; scroll to zoom,
            drag to pan, click any road, node or zone for detail.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge tone={stats.blocked_roads > 0 ? "crit" : "safe"}>
            {stats.blocked_roads} blocked
          </StatusBadge>
          <StatusBadge tone={stats.risky_roads > 0 ? "warn" : "safe"}>
            {stats.risky_roads} at risk
          </StatusBadge>
          <StatusBadge tone={stats.active_emergencies > 0 ? "crit" : "idle"}>
            {stats.active_emergencies} emergencies
          </StatusBadge>
        </div>
      </div>

      {streamStatus !== "open" && (
        <div
          role="status"
          className="rounded-panel border border-warn/40 bg-warn/10 px-4 py-2.5 text-[13px] text-fg"
        >
          Live stream is {streamStatus}. The map shows the last state received.
        </div>
      )}

      <DisasterMap
        nodes={snapshot.nodes}
        zones={snapshot.zones}
        roads={snapshot.roads}
        hospitals={snapshot.hospitals}
        shelters={snapshot.shelters}
        ambulances={snapshot.ambulances}
        emergencies={snapshot.emergencies}
        interactive
      />

      <p className="text-2xs leading-relaxed text-fg-muted">
        Flood shading is each zone&rsquo;s <code>flood_level</code> from the
        simulation, not an estimate. Road colour and dash pattern follow the
        backend&rsquo;s derived road status. Water level{" "}
        {environment.water_level_m.toFixed(2)} m; environment version{" "}
        {environment.environment_version}.
      </p>
    </div>
  );
}
