/**
 * Frontend configuration.
 *
 * The API base URL is read here and ONLY here. Everything else imports API_URL
 * from this module, so there is exactly one place to change it and no hard-coded
 * URLs scattered through the codebase.
 */

const rawApiUrl = import.meta.env.VITE_API_URL;

/** Backend base URL, trailing slashes stripped so path joins stay predictable. */
export const API_URL = (rawApiUrl ?? "http://localhost:8000").replace(/\/+$/, "");

if (!rawApiUrl && import.meta.env.DEV) {
  console.warn(
    `[AI-DERS] VITE_API_URL is not set. Falling back to ${API_URL}. ` +
      `Copy frontend/.env.example to frontend/.env to configure it.`,
  );
}

/** Whether VITE_API_URL was explicitly configured, surfaced in the UI. */
export const API_URL_IS_EXPLICIT = Boolean(rawApiUrl);

/**
 * Health re-check interval.
 *
 * This is the only polling in the application and it exists solely to keep the
 * connection badge honest. Simulation state arrives over Server-Sent Events
 * from Phase 2 onward; nothing else polls.
 */
export const HEALTH_POLL_INTERVAL_MS = 15_000;

/** Request timeout. Short: a local backend either answers fast or is down. */
export const REQUEST_TIMEOUT_MS = 5_000;
