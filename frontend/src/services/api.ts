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
