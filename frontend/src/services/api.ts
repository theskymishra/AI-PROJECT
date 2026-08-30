/**
 * HTTP client and typed backend calls.
 *
 * Errors are normalised into ApiError so the UI can render a specific,
 * actionable message. "Failed to fetch" tells the user nothing; "backend not
 * reachable at http://localhost:8000 -- is uvicorn running?" tells them exactly
 * what to do.
 */

import axios from "axios";
import type { AxiosInstance } from "axios";

import { API_URL, REQUEST_TIMEOUT_MS } from "@/config";
import type { HealthResponse } from "@/types";

export const api: AxiosInstance = axios.create({
  baseURL: API_URL,
  timeout: REQUEST_TIMEOUT_MS,
  headers: { Accept: "application/json" },
});

export type ApiErrorKind = "network" | "timeout" | "http" | "unknown";

export interface ApiError {
  kind: ApiErrorKind;
  status?: number;
  message: string;
  /** What the user should actually check. */
  hint: string;
}

export function toApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    if (error.code === "ECONNABORTED") {
      return {
        kind: "timeout",
        message: `Request to ${API_URL} timed out after ${REQUEST_TIMEOUT_MS} ms.`,
        hint: "The backend is reachable but not responding. Check the uvicorn log.",
      };
    }
    if (error.response) {
      return {
        kind: "http",
        status: error.response.status,
        message: `Backend returned ${error.response.status} ${error.response.statusText}.`,
        hint: "The backend is running but rejected this request. Check the route exists.",
      };
    }
    return {
      kind: "network",
      message: `No response from ${API_URL}.`,
      hint:
        "Check that uvicorn is running, that VITE_API_URL matches its host and " +
        "port, and that this origin is listed in AIDERS_CORS_ORIGINS.",
    };
  }
  return {
    kind: "unknown",
    message: error instanceof Error ? error.message : String(error),
    hint: "Unexpected failure. Check the browser console.",
  };
}

export interface TimedHealth {
  health: HealthResponse;
  /** Client-measured round trip in milliseconds. */
  latencyMs: number;
}

export async function fetchHealth(): Promise<TimedHealth> {
  const startedAt = performance.now();
  const response = await api.get<HealthResponse>("/api/health");
  return {
    health: response.data,
    latencyMs: Math.round(performance.now() - startedAt),
  };
}

/* ==========================================================================
   Phase 2 -- simulation commands
   ==========================================================================
   Every command returns the FULL snapshot, so the caller applies the response
   directly instead of issuing a command and then waiting for the stream to
   catch up. That removes a whole class of "I clicked pause and nothing
   happened for a second" bugs, and it means the controls still work if the
   SSE connection is down.
   ========================================================================== */

import type {
  BayesianRequest,
  BayesianResponse,
  HMMRequest,
  HMMResponse,
  RouteRequest,
  RouteResponse,
  ScenarioDetail,
  SimulationSnapshot,
} from "@/types";

export async function fetchState(): Promise<SimulationSnapshot> {
  const { data } = await api.get<SimulationSnapshot>("/api/simulation/state");
  return data;
}

export async function fetchScenarios(): Promise<ScenarioDetail[]> {
  const { data } = await api.get<ScenarioDetail[]>("/api/simulation/scenarios");
  return data;
}

export async function startSimulation(): Promise<SimulationSnapshot> {
  const { data } = await api.post<SimulationSnapshot>("/api/simulation/start");
  return data;
}

export async function pauseSimulation(): Promise<SimulationSnapshot> {
  const { data } = await api.post<SimulationSnapshot>("/api/simulation/pause");
  return data;
}

export async function resumeSimulation(): Promise<SimulationSnapshot> {
  const { data } = await api.post<SimulationSnapshot>("/api/simulation/resume");
  return data;
}

export async function resetSimulation(): Promise<SimulationSnapshot> {
  const { data } = await api.post<SimulationSnapshot>("/api/simulation/reset");
  return data;
}

export async function setSpeed(speed: number): Promise<SimulationSnapshot> {
  const { data } = await api.post<SimulationSnapshot>("/api/simulation/speed", {
    speed,
  });
  return data;
}

export async function setScenario(name: string): Promise<SimulationSnapshot> {
  const { data } = await api.post<SimulationSnapshot>("/api/simulation/scenario", {
    name,
  });
  return data;
}

export interface StreamHealth {
  status: string;
  subscribers: number;
  dropped_frames: number;
  seq: number;
}

export async function fetchStreamHealth(): Promise<StreamHealth> {
  const { data } = await api.get<StreamHealth>("/api/simulation/stream-health");
  return data;
}

/**
 * Run A* between two nodes against current simulation state.
 *
 * `use_cache: false` by default here: the UI shows nodes-expanded and
 * execution time, and a cache hit would report the metrics of whichever
 * earlier call populated the entry. Showing borrowed metrics as if they were
 * this search's would be exactly the kind of faked AI output the brief bans.
 */
export async function requestRoute(
  request: RouteRequest,
): Promise<RouteResponse> {
  const { data } = await api.post<RouteResponse>("/api/ai/route", {
    use_cache: false,
    ...request,
  });
  return data;
}

/** Read the live HMM filter, or filter a supplied sequence from the prior. */
export async function requestHMM(request: HMMRequest = {}): Promise<HMMResponse> {
  const { data } = await api.post<HMMResponse>("/api/ai/hmm", request);
  return data;
}

/** Run Bayesian inference. Omit evidence for live sensor readings. */
export async function requestBayesian(
  request: BayesianRequest = {},
): Promise<BayesianResponse> {
  const { data } = await api.post<BayesianResponse>("/api/ai/bayesian", request);
  return data;
}

/* ==========================================================================
   Phase 6 -- symbolic knowledge engine
   ========================================================================== */

import type { FOLResult, InferenceRequest, InferenceResult } from "@/types";

export async function requestInference(
  request: InferenceRequest = {},
): Promise<InferenceResult> {
  const { data } = await api.post<InferenceResult>("/api/ai/infer", request);
  return data;
}

export async function requestFOL(query: string): Promise<FOLResult> {
  const { data } = await api.post<FOLResult>("/api/ai/fol", { query });
  return data;
}
