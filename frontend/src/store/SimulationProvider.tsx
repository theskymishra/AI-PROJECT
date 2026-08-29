/**
 * The single source of simulation state for the whole application.
 *
 * ARCHITECTURE
 * ------------
 * One SSE connection, one reducer, many readers. Every page and panel reads
 * from this context via useSimulation(); nothing else opens an EventSource and
 * nothing else polls simulation state.
 *
 * There is deliberately NO client-side clock. The tick shown on screen is the
 * tick the backend last sent. A frontend interval that incremented a local
 * counter between frames would look smoother and would be lying -- and the
 * moment it drifted from the backend, every screenshot in the report would be
 * unreproducible.
 *
 * RESYNC
 * ------
 * Deltas are cheap but lossy: a slow client has its oldest frames dropped
 * server-side. Any sequence gap triggers a full refetch rather than leaving
 * the console showing a world with holes in it.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useRef,
} from "react";
import type { ReactNode } from "react";

import {
  fetchState,
  pauseSimulation,
  resetSimulation,
  resumeSimulation,
  setScenario as setScenarioRequest,
  setSpeed as setSpeedRequest,
  startSimulation,
  toApiError,
} from "@/services/api";
import type { ApiError } from "@/services/api";
import { connectStream } from "@/services/stream";
import type { StreamStatus } from "@/services/stream";
import type {
  SimulationSnapshot,
  TickPayload,
} from "@/types";

/* -------------------------------------------------------------------------- */
/* State                                                                      */
/* -------------------------------------------------------------------------- */

interface SimulationState {
  snapshot: SimulationSnapshot | null;
  streamStatus: StreamStatus;
  /** Last envelope sequence applied. Surfaced for diagnostics. */
  seq: number | null;
  /** Times a gap forced a full resync. A non-zero value is worth noticing. */
  resyncCount: number;
  error: ApiError | null;
  /** True while a command is in flight, so controls can disable themselves. */
  commandPending: boolean;
}

type Action =
  | { kind: "snapshot"; payload: SimulationSnapshot; seq: number | null }
  | { kind: "tick"; payload: TickPayload; seq: number }
  | { kind: "streamStatus"; status: StreamStatus }
  | { kind: "resync" }
  | { kind: "error"; error: ApiError | null }
  | { kind: "commandPending"; pending: boolean };

const INITIAL: SimulationState = {
  snapshot: null,
  streamStatus: "connecting",
  seq: null,
  resyncCount: 0,
  error: null,
  commandPending: false,
};

function reducer(state: SimulationState, action: Action): SimulationState {
  switch (action.kind) {
    case "snapshot":
      return {
        ...state,
        snapshot: action.payload,
        seq: action.seq ?? state.seq,
        error: null,
      };

    case "tick": {
      if (!state.snapshot) return state;
      const p = action.payload;
      // See TickPayload in types/index.ts. roads and emergencies are PARTIAL
      // deltas carrying only what changed -- often 1 of 38 roads -- so they
      // are merged by id. Assigning them directly would delete every entity
      // the delta did not mention, which empties the map the first time a
      // single road changes.
      return {
        ...state,
        seq: action.seq,
        snapshot: {
          ...state.snapshot,
          clock: p.clock,
          environment: p.environment,
          stats: p.stats,
          sensors: p.sensors,
          hospitals: p.hospitals,
          roads: mergeById(state.snapshot.roads, p.roads),
          emergencies: mergeById(state.snapshot.emergencies, p.emergencies),
          timeline: appendTail(state.snapshot.timeline, p.timeline_tail),
          alerts: appendTail(state.snapshot.alerts, p.alerts_tail),
        },
      };
    }

    case "streamStatus":
      return { ...state, streamStatus: action.status };

    case "resync":
      return { ...state, resyncCount: state.resyncCount + 1 };

    case "error":
      return { ...state, error: action.error };

    case "commandPending":
      return { ...state, commandPending: action.pending };
  }
}

/**
 * Apply a partial delta, preserving order and every entity the delta omits.
 *
 * The backend sends only changed entities. Existing items are updated in
 * place; anything genuinely new is appended.
 */
function mergeById<T extends { id: string }>(
  existing: T[],
  delta: T[] | undefined,
): T[] {
  if (!delta || delta.length === 0) return existing;
  const updates = new Map(delta.map((item) => [item.id, item]));
  const merged = existing.map((item) => updates.get(item.id) ?? item);
  for (const item of delta) {
    if (!existing.some((e) => e.id === item.id)) merged.push(item);
  }
  return merged;
}

/**
 * Append newly arrived entries, skipping any already held.
 *
 * The backend sends a tail rather than the full list each tick. Deduplicating
 * by id keeps the feed correct across a reconnect, where the same entries can
 * legitimately arrive twice.
 */
function appendTail<T extends { id: string }>(
  existing: T[],
  tail: T[] | undefined,
): T[] {
  if (!tail || tail.length === 0) return existing;
  const seen = new Set(existing.map((item) => item.id));
  const fresh = tail.filter((item) => !seen.has(item.id));
  return fresh.length === 0 ? existing : [...existing, ...fresh];
}

/* -------------------------------------------------------------------------- */
/* Context                                                                    */
/* -------------------------------------------------------------------------- */

export interface SimulationContextValue extends SimulationState {
  start: () => Promise<void>;
  pause: () => Promise<void>;
  resume: () => Promise<void>;
  reset: () => Promise<void>;
  changeSpeed: (speed: number) => Promise<void>;
  changeScenario: (name: string) => Promise<void>;
  refresh: () => Promise<void>;
}

const SimulationContext = createContext<SimulationContextValue | null>(null);

export function SimulationProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, INITIAL);
  const mounted = useRef(true);

  const loadState = useCallback(async () => {
    try {
      const snapshot = await fetchState();
      if (!mounted.current) return;
      dispatch({ kind: "snapshot", payload: snapshot, seq: null });
    } catch (caught) {
      if (!mounted.current) return;
      dispatch({ kind: "error", error: toApiError(caught) });
    }
  }, []);

  // Initial load, then the stream. The REST fetch means the dashboard renders
  // immediately rather than waiting on the stream's opening snapshot.
  useEffect(() => {
    mounted.current = true;
    void loadState();

    const connection = connectStream({
      onSnapshot: (payload, seq) => {
        if (mounted.current) dispatch({ kind: "snapshot", payload, seq });
      },
      onTick: (payload, seq) => {
        if (mounted.current) dispatch({ kind: "tick", payload, seq });
      },
      onSimControl: (payload, seq) => {
        // start/pause/reset/scenario changes carry the full snapshot.
        if (mounted.current) {
          dispatch({ kind: "snapshot", payload: payload.snapshot, seq });
        }
      },
      onStatus: (status) => {
        if (mounted.current) dispatch({ kind: "streamStatus", status });
      },
      onSequenceGap: (expected, received) => {
        console.warn(
          `[AI-DERS] SSE sequence gap: expected ${expected}, received ${received}. Resyncing.`,
        );
        if (!mounted.current) return;
        dispatch({ kind: "resync" });
        void loadState();
      },
    });

    return () => {
      mounted.current = false;
      connection.close();
    };
  }, [loadState]);

  /** Run a command, apply the snapshot it returns, surface any failure. */
  const run = useCallback(
    async (command: () => Promise<SimulationSnapshot>) => {
      dispatch({ kind: "commandPending", pending: true });
      try {
        const snapshot = await command();
        if (!mounted.current) return;
        dispatch({ kind: "snapshot", payload: snapshot, seq: null });
      } catch (caught) {
        if (!mounted.current) return;
        dispatch({ kind: "error", error: toApiError(caught) });
      } finally {
        if (mounted.current) {
          dispatch({ kind: "commandPending", pending: false });
        }
      }
    },
    [],
  );

  const value = useMemo<SimulationContextValue>(
    () => ({
      ...state,
      start: () => run(startSimulation),
      pause: () => run(pauseSimulation),
      resume: () => run(resumeSimulation),
      reset: () => run(resetSimulation),
      changeSpeed: (speed: number) => run(() => setSpeedRequest(speed)),
      changeScenario: (name: string) => run(() => setScenarioRequest(name)),
      refresh: loadState,
    }),
    [state, run, loadState],
  );

  return (
    <SimulationContext value={value}>{children}</SimulationContext>
  );
}

export function useSimulation(): SimulationContextValue {
  const context = useContext(SimulationContext);
  if (!context) {
    throw new Error("useSimulation must be used inside a SimulationProvider");
  }
  return context;
}
