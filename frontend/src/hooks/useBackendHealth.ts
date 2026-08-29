/**
 * Live backend connection state.
 *
 * Re-checks on mount, on an interval, when the tab regains focus, and on
 * demand. From Phase 2 the simulation arrives over SSE; this hook keeps doing
 * only what it does now -- answering "is the backend there".
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { HEALTH_POLL_INTERVAL_MS } from "@/config";
import { fetchHealth, toApiError } from "@/services/api";
import type { ApiError } from "@/services/api";
import type { HealthResponse } from "@/types";

export type ConnectionState = "checking" | "online" | "offline";

export interface BackendHealth {
  state: ConnectionState;
  health: HealthResponse | null;
  error: ApiError | null;
  latencyMs: number | null;
  lastCheckedAt: Date | null;
  refresh: () => void;
}

export interface UseBackendHealthOptions {
  /**
   * Suspend interval polling. Set while the SSE stream is open: a live stream
   * already proves the backend is reachable, so polling as well is redundant
   * traffic on a console that is meant to be push-driven.
   */
  paused?: boolean;
}

export function useBackendHealth(
  options: UseBackendHealthOptions = {},
): BackendHealth {
  const { paused = false } = options;
  const [state, setState] = useState<ConnectionState>("checking");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [lastCheckedAt, setLastCheckedAt] = useState<Date | null>(null);

  // Guards against a slow response resolving after the component unmounts.
  const mountedRef = useRef(true);

  const check = useCallback(async () => {
    try {
      const { health: payload, latencyMs: measured } = await fetchHealth();
      if (!mountedRef.current) return;
      setHealth(payload);
      setLatencyMs(measured);
      setError(null);
      setState("online");
    } catch (caught) {
      if (!mountedRef.current) return;
      setError(toApiError(caught));
      setLatencyMs(null);
      setState("offline");
    } finally {
      if (mountedRef.current) setLastCheckedAt(new Date());
    }
  }, []);

  const refresh = useCallback(() => {
    setState("checking");
    void check();
  }, [check]);

  useEffect(() => {
    mountedRef.current = true;
    void check();

    const interval = paused
      ? null
      : window.setInterval(() => void check(), HEALTH_POLL_INTERVAL_MS);
    const onFocus = () => void check();
    window.addEventListener("focus", onFocus);

    return () => {
      mountedRef.current = false;
      if (interval !== null) window.clearInterval(interval);
      window.removeEventListener("focus", onFocus);
    };
  }, [check, paused]);

  return { state, health, error, latencyMs, lastCheckedAt, refresh };
}
