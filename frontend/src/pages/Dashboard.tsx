/**
 * Operations dashboard.
 *
 * Every figure, event and road colour on this page originates in the backend
 * snapshot delivered over SSE. Nothing is simulated, interpolated or
 * synthesised in the browser: if the backend stops, this page stops.
 */

import { CircleAlert } from "lucide-react";

import { AlertPanel } from "@/components/dashboard/AlertPanel";
import { EnvironmentPanel } from "@/components/dashboard/EnvironmentPanel";
import { EventTimeline } from "@/components/dashboard/EventTimeline";
import { StatCard } from "@/components/dashboard/StatCard";
import { SimulationControls } from "@/components/simulation/SimulationControls";
import { WorldPreview } from "@/components/world/WorldPreview";
import { useSimulation } from "@/store/SimulationProvider";

export function Dashboard() {
  const { snapshot, error, streamStatus, resyncCount, refresh } = useSimulation();

  if (!snapshot) {
    return (
      <div className="mx-auto max-w-5xl">
        {error ? (
          <div
            role="alert"
            className="flex items-start gap-3 rounded-panel border border-crit/40 bg-crit/10 p-4"
          >
            <CircleAlert
              aria-hidden="true"
              className="mt-0.5 size-4 shrink-0 text-crit"
            />
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
                onClick={() => void refresh()}
                className="mt-3 rounded-panel border border-border bg-panel-2 px-2.5 py-1.5 text-2xs tracking-wide text-fg uppercase transition-colors duration-150 hover:border-info/50"
              >
                Try again
              </button>
            </div>
          </div>
        ) : (
          <p className="py-10 text-center text-[13px] text-fg-muted">
            Loading simulation state&hellip;
          </p>
        )}
      </div>
    );
  }

  const { stats, environment, clock } = snapshot;
  const beds = stats.available_beds;
  const bedTone =
    beds === 0 ? "crit" : beds / Math.max(stats.total_beds, 1) <= 0.25 ? "warn" : "safe";

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4">
      <SimulationControls />

      {streamStatus !== "open" && (
        <div
          role="status"
          className="rounded-panel border border-warn/40 bg-warn/10 px-4 py-2.5 text-[13px] text-fg"
        >
          Live stream is {streamStatus}. Figures below are the last values
          received and will not advance until the connection is restored.
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard
          label="Active Emergencies"
          value={stats.active_emergencies}
          tone={stats.active_emergencies > 0 ? "crit" : "idle"}
        />
        <StatCard
          label="People at Risk"
          value={stats.people_at_risk}
          tone={stats.people_at_risk > 0 ? "warn" : "idle"}
          hint={`${stats.patients_awaiting_transport} need transport`}
        />
        <StatCard
          label="Ambulances"
          value={stats.available_ambulances}
          outOf={stats.total_ambulances}
          tone={stats.available_ambulances === 0 ? "crit" : "safe"}
        />
        <StatCard
          label="Hospital Beds"
          value={beds}
          outOf={stats.total_beds}
          tone={bedTone}
          hint={`${stats.available_icu} ICU`}
        />
        <StatCard
          label="Blocked Roads"
          value={stats.blocked_roads}
          outOf={stats.total_roads}
          tone={stats.blocked_roads > 0 ? "crit" : "safe"}
        />
        <StatCard
          label="Roads at Risk"
          value={stats.risky_roads}
          outOf={stats.total_roads}
          tone={stats.risky_roads > 0 ? "warn" : "safe"}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-4">
          <WorldPreview
            nodes={snapshot.nodes}
            zones={snapshot.zones}
            roads={snapshot.roads}
            hospitals={snapshot.hospitals}
            shelters={snapshot.shelters}
          />
          <div className="grid gap-4 md:grid-cols-2">
            <FacilityPanel snapshot={snapshot} />
            <EnvironmentPanel
              rainfallMm={environment.rainfall_mm}
              waterLevelM={environment.water_level_m}
              riverLevelM={environment.river_level_m}
              trueFloodState={environment.true_flood_state}
              environmentVersion={environment.environment_version}
              sensors={snapshot.sensors}
            />
          </div>
        </div>

        <div className="flex min-h-0 flex-col gap-4 xl:max-h-[calc(100vh-13rem)]">
          <div className="min-h-0 flex-1">
            <EventTimeline entries={snapshot.timeline} />
          </div>
          <div className="min-h-0 max-h-72 flex-1">
            <AlertPanel alerts={snapshot.alerts} />
          </div>
        </div>
      </div>

      <p className="text-2xs leading-relaxed text-fg-muted">
        AI-DERS is an academic AI simulation. It is not an operational
        emergency-management system, and no output it produces should be used to
        make real emergency decisions. Scenario {snapshot.scenario.name} runs for{" "}
        {snapshot.scenario.duration_ticks} ticks; currently at tick {clock.tick}.
        {resyncCount > 0 &&
          ` Stream resynchronised ${resyncCount} time(s) after a dropped frame.`}
      </p>
    </div>
  );
}

/** Hospitals and shelters, with their derived server-side status. */
function FacilityPanel({
  snapshot,
}: {
  snapshot: NonNullable<ReturnType<typeof useSimulation>["snapshot"]>;
}) {
  return (
    <section className="rounded-panel border border-border bg-panel">
      <div className="border-b border-border px-4 py-2.5">
        <h2 className="text-2xs font-medium tracking-wide text-fg-muted uppercase">
          Facilities
        </h2>
      </div>
      <div className="p-4">
        <table className="w-full text-left">
          <thead>
            <tr className="text-2xs tracking-wide text-fg-muted uppercase">
              <th className="pb-1.5 font-medium">Hospital</th>
              <th className="pb-1.5 text-right font-medium">Beds</th>
              <th className="pb-1.5 text-right font-medium">ICU</th>
              <th className="pb-1.5 text-right font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {snapshot.hospitals.map((hospital) => (
              <tr key={hospital.id} className="border-t border-border/60">
                <td className="py-1.5 text-[13px] text-fg">{hospital.name}</td>
                <td className="py-1.5 text-right font-mono text-[13px] text-fg">
                  {hospital.available_beds}
                  <span className="text-fg-muted">/{hospital.total_beds}</span>
                </td>
                <td className="py-1.5 text-right font-mono text-[13px] text-fg">
                  {hospital.available_icu}
                  <span className="text-fg-muted">/{hospital.total_icu}</span>
                </td>
                <td className="py-1.5 text-right font-mono text-2xs text-fg-muted">
                  {hospital.status}
                </td>
              </tr>
            ))}
            {snapshot.shelters.map((shelter) => (
              <tr key={shelter.id} className="border-t border-border/60">
                <td className="py-1.5 text-[13px] text-fg">{shelter.name}</td>
                <td className="py-1.5 text-right font-mono text-[13px] text-fg">
                  {shelter.capacity - shelter.occupancy}
                  <span className="text-fg-muted">/{shelter.capacity}</span>
                </td>
                <td className="py-1.5 text-right font-mono text-[13px] text-fg-muted">
                  &mdash;
                </td>
                <td className="py-1.5 text-right font-mono text-2xs text-fg-muted">
                  {shelter.status}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
