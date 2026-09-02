/**
 * Typed endpoint functions — 1:1 with the 12 implemented 1B routes
 * (verified against dsa_tutor/api/app.py; payload shapes from the live capture,
 * plans/V1_SLICE_1C_API_CAPTURE.json). The ONLY fetch call sites live in
 * client.ts; this module adds paths, bodies and the Idempotency-Key semantics:
 *
 *   - one FRESH key per intentional answer submission (makeIdempotencyKey)
 *   - the caller reuses the SAME key when retrying that same submission
 *   (design §4.5; duplicate submissions are replayed server-side, stale ones 409).
 */
import { request } from "./client";
import type {
  AnswerResponse, ConfidenceResponse, ExplainResponse, HomePayload, Pace,
  ProgressReport, RevealResponse, ResumeResponse, SnapshotResponse,
  StartResponse, StopResponse, TurnResponse,
} from "./types";

export function makeIdempotencyKey(): string {
  const c = globalThis.crypto;
  if (c && typeof c.randomUUID === "function") {
    return c.randomUUID();
  }
  return `idem-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/** POST /api/v1/sessions — start a new session (409 if one already exists). */
export function startSession(pace: Pace = "normal"): Promise<StartResponse> {
  return request("POST", "/api/v1/sessions", { body: { pace } });
}

/** GET /api/v1/sessions/{id} — read-only snapshot (zero server writes). */
export function getSessionSnapshot(sessionId: number | string): Promise<SnapshotResponse> {
  return request("GET", `/api/v1/sessions/${sessionId}`);
}

/** POST …/resume — paused→active once; already-active is a 200 no-op. */
export function resumeSession(sessionId: number | string): Promise<ResumeResponse> {
  return request("POST", `/api/v1/sessions/${sessionId}/resume`, { body: {} });
}

/** POST …/stop — active→paused once; already-paused is a 200 no-op. */
export function stopSession(sessionId: number | string, reason?: string): Promise<StopResponse> {
  return request("POST", `/api/v1/sessions/${sessionId}/stop`,
    { body: reason ? { reason } : {} });
}

/** POST …/theory-seen — retry-safe theory completion. */
export function theorySeen(sessionId: number | string): Promise<TurnResponse> {
  return request("POST", `/api/v1/sessions/${sessionId}/theory-seen`, { body: {} });
}

/** POST …/answer — requires Idempotency-Key (fresh per intentional submission). */
export function answer(sessionId: number | string, activityId: string, answer: string,
                       idempotencyKey: string = makeIdempotencyKey()): Promise<AnswerResponse> {
  return request("POST",
    `/api/v1/sessions/${sessionId}/activities/${activityId}/answer`,
    { body: { answer }, idempotencyKey });
}

/** POST …/hint — next rung of the assistance ladder. */
export function hint(sessionId: number | string, activityId: string): Promise<TurnResponse> {
  return request("POST", `/api/v1/sessions/${sessionId}/activities/${activityId}/hint`,
    { body: {} });
}

/** POST …/reveal-solution — complete reveal (attempt counts as assisted). */
export function revealSolution(sessionId: number | string,
                               activityId: string): Promise<RevealResponse> {
  return request("POST",
    `/api/v1/sessions/${sessionId}/activities/${activityId}/reveal-solution`, { body: {} });
}

/** POST …/explain — targeted explanation of the current activity. */
export function explain(sessionId: number | string, activityId: string): Promise<ExplainResponse> {
  return request("POST", `/api/v1/sessions/${sessionId}/activities/${activityId}/explain`,
    { body: {} });
}

/** POST …/confidence — learner confidence rating for a skill. */
export function confidence(sessionId: number | string, skillId: string,
                           rating: number): Promise<ConfidenceResponse> {
  return request("POST", `/api/v1/sessions/${sessionId}/confidence`,
    { body: { skill_id: skillId, rating } });
}

/** GET /api/v1/learner/progress — qualitative mastery report. */
export function progress(): Promise<ProgressReport> {
  return request("GET", "/api/v1/learner/progress");
}

/** GET /api/v1/home — dashboard composition (daily + plan + resume). */
export function home(): Promise<HomePayload> {
  return request("GET", "/api/v1/home");
}
