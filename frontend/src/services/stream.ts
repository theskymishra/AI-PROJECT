/**
 * Server-Sent Events client.
 *
 * ONE connection for the whole application, owned by SimulationProvider.
 * There is no client-side simulation loop anywhere in this codebase: the
 * browser renders what the backend sends and nothing else. If the clock
 * appears to move while the backend is stopped, that is a bug, not a feature.
 *
 * Three things this handles that a bare `new EventSource(url)` does not:
 *
 *   1. NAMED EVENTS. The backend sends `event: snapshot`, `event: tick` and
 *      `event: sim_control`. EventSource.onmessage only fires for unnamed
 *      events, so every frame would be silently dropped. Named listeners are
 *      required.
 *   2. SEQUENCE GAPS. Every envelope carries a monotonic `seq`. A gap means
 *      frames were dropped (the backend sheds the oldest frames for a slow
 *      client rather than growing its queue without bound). On a gap we
 *      refetch full state instead of rendering a world with holes in it.
 *   3. RECONNECT REPORTING. EventSource retries on its own, but silently.
 *      Surfacing the state is what stops a frozen console being mistaken for
 *      a paused simulation.
 */

import type { SimControlPayload, SimulationSnapshot, TickPayload } from "@/types";

import { API_URL } from "@/config";

export type StreamStatus = "connecting" | "open" | "reconnecting" | "closed";

export interface StreamHandlers {
  onSnapshot: (payload: SimulationSnapshot, seq: number) => void;
  onTick: (payload: TickPayload, seq: number) => void;
  onSimControl: (payload: SimControlPayload, seq: number) => void;
  onStatus: (status: StreamStatus) => void;
  /** Fired when `seq` jumps. The provider responds by refetching full state. */
  onSequenceGap: (expected: number, received: number) => void;
}

interface Envelope<T> {
  seq: number;
  tick: number;
  type: string;
  payload: T;
}

export interface StreamConnection {
  close: () => void;
}

/**
 * Open the stream. Returns a handle whose `close()` must be called on unmount,
 * or React StrictMode's double-invoked effects leave an orphaned connection
 * holding a subscriber slot on the server.
 */
export function connectStream(handlers: StreamHandlers): StreamConnection {
  const source = new EventSource(`${API_URL}/api/stream`);
  let lastSeq: number | null = null;
  let closed = false;

  handlers.onStatus("connecting");

  const parse = <T,>(raw: MessageEvent): Envelope<T> | null => {
    try {
      return JSON.parse(raw.data) as Envelope<T>;
    } catch {
      // A frame we cannot parse is a contract violation, not a user error.
      console.error("[AI-DERS] unparseable SSE frame", raw.data);
      return null;
    }
  };

  /** Returns false when a gap was detected and the frame should be ignored. */
  const checkSeq = (seq: number): boolean => {
    if (lastSeq !== null && seq > lastSeq + 1) {
      handlers.onSequenceGap(lastSeq + 1, seq);
      lastSeq = seq;
      return false;
    }
    lastSeq = seq;
    return true;
  };

  source.addEventListener("snapshot", (event) => {
    const envelope = parse<SimulationSnapshot>(event as MessageEvent);
    if (!envelope) return;
    // A snapshot is a full resync, so it re-bases the sequence rather than
    // being checked against it.
    lastSeq = envelope.seq;
    handlers.onSnapshot(envelope.payload, envelope.seq);
  });

  source.addEventListener("tick", (event) => {
    const envelope = parse<TickPayload>(event as MessageEvent);
    if (!envelope || !checkSeq(envelope.seq)) return;
    handlers.onTick(envelope.payload, envelope.seq);
  });

  source.addEventListener("sim_control", (event) => {
    const envelope = parse<SimControlPayload>(event as MessageEvent);
    if (!envelope) return;
    lastSeq = envelope.seq;
    handlers.onSimControl(envelope.payload, envelope.seq);
  });

  source.onopen = () => {
    if (!closed) handlers.onStatus("open");
  };

  source.onerror = () => {
    if (closed) return;
    // readyState CLOSED means EventSource gave up; CONNECTING means it is
    // retrying on its own and we should not open a competing connection.
    handlers.onStatus(
      source.readyState === EventSource.CLOSED ? "closed" : "reconnecting",
    );
  };

  return {
    close: () => {
      closed = true;
      source.close();
      handlers.onStatus("closed");
    },
  };
}
