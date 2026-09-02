/**
 * Transport wrapper (design §7): JSON in/out over the 1B API, frozen error
 * envelope parsing, retryable semantics. Projection-only — no pedagogical
 * logic lives here. Server truth is passed through untouched.
 *
 * Transport failure modes handled here (client-side; no server envelope exists
 * for these, so their codes are client-only and marked as such):
 * - network failure      -> ApiClientError("NETWORK_ERROR", retryable: true)
 * - non-JSON error body  -> ApiClientError("UNPARSEABLE_RESPONSE", retryable: false)
 */
import type { ErrorEnvelope } from "./types";

/** Base URL of the 1B API (VITE_API_BASE; default per frontend/.env.example). */
export const API_BASE: string = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

/** Client-side transport/server error carrying the frozen envelope semantics. */
export class ApiClientError extends Error {
  readonly status: number;
  readonly code: string;
  readonly retryable: boolean;
  /** Non-standard extra envelope keys served by specific errors
   *  (turn / activity / resume / session_id — design §4.0). */
  readonly details: Record<string, unknown>;

  constructor(status: number, code: string, message: string,
              retryable: boolean, details: Record<string, unknown> = {}) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.retryable = retryable;
    this.details = details;
  }
}

export interface RequestOptions {
  body?: unknown;
  headers?: Record<string, string>;
  idempotencyKey?: string;
  signal?: AbortSignal;
}

function buildUrl(path: string): string {
  // path always starts with /api/v1 — API_BASE must not end with a slash.
  return `${API_BASE}${path}`;
}

/**
 * Single fetch call site. Parses JSON on success and the frozen error envelope
 * on failure. Never inspects or transforms payloads beyond envelope handling.
 */
export async function request<T>(method: "GET" | "POST", path: string,
                                 options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { ...options.headers };
  let body: string | undefined;
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }
  if (options.idempotencyKey) {
    headers["Idempotency-Key"] = options.idempotencyKey;
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path), {
      method,
      headers,
      body,
      signal: options.signal,
    });
  } catch (cause) {
    if (cause instanceof Error && cause.name === "AbortError") {
      throw cause; // caller-requested cancellation is not a transport error
    }
    throw new ApiClientError(0, "NETWORK_ERROR",
      "Could not reach the API server.", true, { cause: String(cause) });
  }

  const raw = await response.text().catch(() => "");
  let parsed: unknown = undefined;
  if (raw) {
    try {
      parsed = JSON.parse(raw);
    } catch {
      parsed = undefined;
    }
  }

  if (response.ok) {
    if (parsed === undefined) {
      throw new ApiClientError(response.status, "UNPARSEABLE_RESPONSE",
        "Server returned an unexpected non-JSON body.", false, { raw: raw.slice(0, 500) });
    }
    return parsed as T;
  }

  const envelope = (parsed !== null && typeof parsed === "object" && "error" in parsed)
    ? (parsed as ErrorEnvelope).error
    : undefined;
  if (envelope === undefined || typeof envelope.code !== "string") {
    throw new ApiClientError(response.status, "UNPARSEABLE_RESPONSE",
      `Server returned HTTP ${response.status} without a valid error envelope.`,
      false, { raw: raw.slice(0, 500) });
  }
  const { code, message, retryable, ...details } = envelope;
  throw new ApiClientError(response.status, code,
    typeof message === "string" ? message : "", retryable === true, details);
}
