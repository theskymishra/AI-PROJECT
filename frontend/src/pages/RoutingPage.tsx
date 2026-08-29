/**
 * AI Routing page.
 *
 * Runs the real backend A* and draws its result on the same DisasterMap the
 * rest of the application uses. The route overlay, the explored-node halos and
 * every metric on screen come from one search on the server.
 */

import { CircleAlert } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { DisasterMap } from "@/components/map/DisasterMap";
import { RoutePanel } from "@/components/routing/RoutePanel";
import { SearchVisualizer } from "@/components/routing/SearchVisualizer";
import { useSearchPlayback } from "@/hooks/useSearchPlayback";
import { requestRoute, toApiError } from "@/services/api";
import { useSimulation } from "@/store/SimulationProvider";
import type { RouteCostWeights, RouteResult } from "@/types";

/** Riverside Quay to Highland Hospital: the corridor the demo turns on. */
const DEFAULT_START = "N1";
const DEFAULT_GOAL = "N17";

export function RoutingPage() {
  const { snapshot, error: streamError } = useSimulation();

  const [start, setStart] = useState(DEFAULT_START);
  const [goal, setGoal] = useState(DEFAULT_GOAL);
  const [route, setRoute] = useState<RouteResult | null>(null);
  const [weights, setWeights] = useState<RouteCostWeights | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const playback = useSearchPlayback(route?.expansion_order);

  const search = useCallback(async () => {
    setPending(true);
    setError(null);
    try {
      const response = await requestRoute({ start, goal });
      setRoute(response.route);
      setWeights(response.weights);
    } catch (caught) {
      const apiError = toApiError(caught);
      setError(`${apiError.message} ${apiError.hint}`);
      setRoute(null);
    } finally {
      setPending(false);
    }
  }, [start, goal]);

  // One search on mount so the page is not empty on arrival. Subsequent
  // searches are explicit: A* must not silently re-run on every tick, or the
  // metrics would churn while the user is reading them.
  useEffect(() => {
    void search();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!snapshot) {
    return (
      <div className="mx-auto max-w-3xl">
        {streamError ? (
          <div
            role="alert"
            className="flex items-start gap-3 rounded-panel border border-crit/40 bg-crit/10 p-4"
          >
            <CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-crit" />
            <p className="text-[13px] text-fg-muted">{streamError.hint}</p>
          </div>
        ) : (
          <p className="py-10 text-center text-[13px] text-fg-muted">
            Loading world&hellip;
          </p>
        )}
      </div>
    );
  }

  const showingPartialSearch =
    playback.state !== "idle" && playback.step < playback.totalSteps;

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4">
      <div>
        <h2 className="text-xl font-semibold text-fg">AI Routing</h2>
        <p className="mt-0.5 text-[13px] text-fg-muted">
          A* search over the live road network. Blocked roads are excluded from
          the search; flooded and damaged roads cost more to traverse.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <DisasterMap
          nodes={snapshot.nodes}
          zones={snapshot.zones}
          roads={snapshot.roads}
          hospitals={snapshot.hospitals}
          shelters={snapshot.shelters}
          ambulances={snapshot.ambulances}
          emergencies={snapshot.emergencies}
          interactive
          title="Route"
          routeEdges={showingPartialSearch ? [] : (route?.edges ?? [])}
          routePath={showingPartialSearch ? [] : (route?.path ?? [])}
          exploredNodes={playback.state === "idle" ? [] : playback.revealed}
          startNode={start}
          goalNode={goal}
        />

        <div className="flex flex-col gap-4">
          <RoutePanel
            nodes={snapshot.nodes}
            start={start}
            goal={goal}
            onStartChange={setStart}
            onGoalChange={setGoal}
            onSubmit={() => void search()}
            pending={pending}
            route={route}
            weights={weights}
            error={error}
          />
          {route?.found && (
            <SearchVisualizer
              playback={playback}
              expansionOrder={route.expansion_order}
            />
          )}
        </div>
      </div>

      <p className="text-2xs leading-relaxed text-fg-muted">
        Route recomputed on demand, not on every tick. Block a road from the
        dashboard and search again to see A* choose a different corridor.
        Environment version {snapshot.environment.environment_version}.
      </p>
    </div>
  );
}
