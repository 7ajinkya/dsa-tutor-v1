/**
 * useSessionStore (design §6): owns the current session/turn and orchestrates
 * the typed C2 API calls. Orchestration only — NO pedagogical logic, no
 * progression decisions, no mastery calculations, no sequencing, no
 * diagnostic/instructional inference (invariant, plan v0.2.0 review).
 *
 * Rules implemented here (approved plan + design doc):
 * - server truth wins: every successful mutation replaces the stored turn with
 *   the authoritative server turn (object passthrough, never reconstructed);
 * - single in-flight mutation: submitAnswer suppresses concurrent submissions;
 * - idempotency (design §4.5): one key per intentional submission, kept across
 *   retryable failures, cleared on success / stale adoption / non-retryable errors;
 * - stale adoption (design §16): 409 STALE_ACTIVITY adopts `error.details.turn`
 *   and never re-submits the stale action.
 */
import { ref } from "vue";
import { defineStore } from "pinia";
import { ApiClientError } from "../api/client";
import * as api from "../api/endpoints";
import type {
  AnswerResponse, PlanPreview, Result, SessionInfo, TurnEnvelope,
} from "../api/types";
import { useUiStore } from "./ui";

type SessionStatus = "idle" | "loading" | "ready" | "error";

export interface StoreError {
  code: string;
  message: string;
  retryable: boolean;
}

export const useSessionStore = defineStore("session", () => {
  const session = ref<SessionInfo | null>(null);
  const turn = ref<TurnEnvelope | null>(null);
  const plan = ref<PlanPreview | null>(null);
  const status = ref<SessionStatus>("idle");
  const error = ref<StoreError | null>(null);
  /** True while a mutation is in flight — views disable mutation buttons. */
  const inFlight = ref(false);
  /** Idempotency key of the in-flight (or retryable-failed) answer submission. */
  const pendingKey = ref<string | null>(null);
  const lastResult = ref<Result | null>(null);
  const lastExplanation = ref<string | null>(null);
  const lastSolution = ref<string | null>(null);
  const confidenceReported = ref<string[]>([]);

  function toStoreError(err: unknown): StoreError {
    if (err instanceof ApiClientError) {
      return { code: err.code, message: err.message, retryable: err.retryable };
    }
    return { code: "INTERNAL_ERROR", message: "Unexpected client error.", retryable: false };
  }

  /** Server truth wins: passthrough the server turn object, never rebuild it. */
  function applyTurn(incoming: TurnEnvelope): void {
    turn.value = incoming;
    if (incoming.session) session.value = incoming.session;
    // transient per-activity panels reset with the turn
    lastExplanation.value = null;
    lastSolution.value = null;
  }

  // -------------------------------------------------------------- lifecycle
  async function start(pace: "slow" | "normal" | "fast" = "normal"): Promise<void> {
    if (inFlight.value) return;
    inFlight.value = true;
    status.value = "loading";
    error.value = null;
    try {
      const res = await api.startSession(pace);
      session.value = res.session;
      applyTurn(res.turn);
      plan.value = null;
      status.value = "ready";
      confidenceReported.value = [];
    } catch (err) {
      status.value = "error";
      error.value = toStoreError(err);
      throw err;
    } finally {
      inFlight.value = false;
    }
  }

  async function resume(sessionId: number): Promise<void> {
    if (inFlight.value) return;
    inFlight.value = true;
    status.value = "loading";
    error.value = null;
    try {
      const res = await api.resumeSession(sessionId);
      session.value = res.session;
      applyTurn(res.turn);
      status.value = "ready";
    } catch (err) {
      status.value = "error";
      error.value = toStoreError(err);
      throw err;
    } finally {
      inFlight.value = false;
    }
  }

  /** Read-only snapshot (design §4.2): zero server writes; used by the
   *  /session/:id route guard on reload. */
  async function loadSnapshot(sessionId: number): Promise<void> {
    if (inFlight.value) return;
    inFlight.value = true;
    status.value = "loading";
    error.value = null;
    try {
      const res = await api.getSessionSnapshot(sessionId);
      session.value = res.session;
      applyTurn(res.turn);
      plan.value = res.plan;
      status.value = "ready";
    } catch (err) {
      status.value = "error";
      error.value = toStoreError(err);
      throw err;
    } finally {
      inFlight.value = false;
    }
  }

  async function stop(reason?: string): Promise<void> {
    if (inFlight.value || session.value === null) return;
    inFlight.value = true;
    status.value = "loading";
    error.value = null;
    try {
      const res = await api.stopSession(session.value.id, reason);
      if (res.session) session.value = res.session;
      if (res.turn) applyTurn(res.turn);
      status.value = "ready";
    } catch (err) {
      status.value = "error";
      error.value = toStoreError(err);
      throw err;
    } finally {
      inFlight.value = false;
    }
  }

  // -------------------------------------------------------------- theory
  async function theorySeen(): Promise<void> {
    if (inFlight.value || session.value === null) return;
    inFlight.value = true;
    status.value = "loading";
    error.value = null;
    try {
      const res = await api.theorySeen(session.value.id);
      applyTurn(res.turn);
      status.value = "ready";
    } catch (err) {
      status.value = "error";
      error.value = toStoreError(err);
      throw err;
    } finally {
      inFlight.value = false;
    }
  }

  // -------------------------------------------------------------- answer
  async function submitAnswer(activityId: string, answer: string): Promise<AnswerResponse | null> {
    if (inFlight.value || session.value === null) return null;
    const ui = useUiStore();
    const key = pendingKey.value ?? api.makeIdempotencyKey();
    pendingKey.value = key; // kept across retryable failures; one key per submission
    inFlight.value = true;
    status.value = "loading";
    error.value = null;
    try {
      const res = await api.answer(session.value.id, activityId, answer, key);
      applyTurn(res.turn);
      lastResult.value = res.result;
      pendingKey.value = null; // success: the next submission is intentionally new
      ui.clearStaleAdopted();
      status.value = "ready";
      return res;
    } catch (err) {
      if (err instanceof ApiClientError && err.code === "STALE_ACTIVITY"
          && err.details.turn !== undefined) {
        // stale adoption (design §16): authoritative turn replaces the local one;
        // the stale submission is void — no automatic re-submission.
        applyTurn(err.details.turn as TurnEnvelope);
        pendingKey.value = null;
        status.value = "ready";
        ui.markStaleAdopted();
        ui.pushToast("info", "Skipped ahead — showing the current task.");
        return null;
      }
      status.value = "error";
      error.value = toStoreError(err);
      if (!(err instanceof ApiClientError && err.retryable)) {
        pendingKey.value = null; // non-retryable: the submission is void
      }
      throw err;
    } finally {
      inFlight.value = false;
    }
  }

  // -------------------------------------------------------------- hint / reveal / explain
  async function requestHint(): Promise<void> {
    if (inFlight.value || session.value === null || turn.value === null
        || turn.value.activity === null) return;
    inFlight.value = true;
    status.value = "loading";
    error.value = null;
    try {
      const res = await api.hint(session.value.id, turn.value.activity.id);
      applyTurn(res.turn);
      status.value = "ready";
    } catch (err) {
      status.value = "error";
      error.value = toStoreError(err);
      throw err;
    } finally {
      inFlight.value = false;
    }
  }

  async function revealSolution(): Promise<void> {
    if (inFlight.value || session.value === null || turn.value === null
        || turn.value.activity === null) return;
    inFlight.value = true;
    status.value = "loading";
    error.value = null;
    try {
      const res = await api.revealSolution(session.value.id, turn.value.activity.id);
      applyTurn(res.turn);
      lastSolution.value = res.solution;
      status.value = "ready";
    } catch (err) {
      status.value = "error";
      error.value = toStoreError(err);
      throw err;
    } finally {
      inFlight.value = false;
    }
  }

  async function explainCurrent(): Promise<void> {
    if (inFlight.value || session.value === null || turn.value === null
        || turn.value.activity === null) return;
    inFlight.value = true;
    status.value = "loading";
    error.value = null;
    try {
      const res = await api.explain(session.value.id, turn.value.activity.id);
      lastExplanation.value = res.explanation;
      status.value = "ready";
    } catch (err) {
      status.value = "error";
      error.value = toStoreError(err);
      throw err;
    } finally {
      inFlight.value = false;
    }
  }

  // -------------------------------------------------------------- confidence
  async function reportConfidence(skillId: string, rating: number): Promise<void> {
    if (inFlight.value || session.value === null) return;
    inFlight.value = true;
    status.value = "loading";
    error.value = null;
    try {
      await api.confidence(session.value.id, skillId, rating);
      // in-memory UI bookkeeping only: the turn is NOT locally mutated
      if (!confidenceReported.value.includes(skillId)) {
        confidenceReported.value = [...confidenceReported.value, skillId];
      }
      status.value = "ready";
    } catch (err) {
      status.value = "error";
      error.value = toStoreError(err);
      throw err;
    } finally {
      inFlight.value = false;
    }
  }

  function hasReportedConfidence(skillId: string): boolean {
    return confidenceReported.value.includes(skillId);
  }

  return {
    // state
    session, turn, plan, status, error, inFlight, pendingKey,
    lastResult, lastExplanation, lastSolution, confidenceReported,
    // actions
    start, resume, loadSnapshot, stop, theorySeen, submitAnswer,
    requestHint, revealSolution, explainCurrent, reportConfidence,
    hasReportedConfidence,
  };
});
