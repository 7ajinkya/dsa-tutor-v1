import { toRaw } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

vi.mock("../api/endpoints", () => ({
  startSession: vi.fn(),
  resumeSession: vi.fn(),
  getSessionSnapshot: vi.fn(),
  stopSession: vi.fn(),
  theorySeen: vi.fn(),
  answer: vi.fn(),
  hint: vi.fn(),
  revealSolution: vi.fn(),
  explain: vi.fn(),
  confidence: vi.fn(),
  progress: vi.fn(),
  home: vi.fn(),
  makeIdempotencyKey: vi.fn(),
}));

import { ApiClientError } from "../api/client";
import * as endpoints from "../api/endpoints";
import type { SessionInfo, TurnEnvelope } from "../api/types";

const mockEndpoints = vi.mocked(endpoints);

const sessionInfo: SessionInfo = {
  id: 1, status: "active", pace: "normal", budget_minutes: 25,
  remaining_minutes: 24.99, started_at: "2026-09-03T00:00:00+00:00", ended_at: null,
  end_reason_code: null, end_reason_detail: null,
  daily: { target_units: 4, completed_units: 0, status: "active" },
};

function makeTurn(overrides: Partial<TurnEnvelope> = {}): TurnEnvelope {
  return {
    type: "activity",
    session: sessionInfo,
    step: { action: "advance", why: ["skill 'graph_definition' not yet mastered"], sequence: "planned" },
    notice: null,
    activity: {
      id: "e001_graph_definition", type: "mcq", mode: "teach",
      purpose: "Study on 'What is a graph?'", prompt: "Which statement best describes a graph?",
      answer_format: "letter", position: { index: 1, of: 2 },
      unit: { id: "u001_graph_definition", title: "What is a graph?", goal: "Understand what is a graph?" },
      skill: { id: "graph_definition", title: "What is a graph?" },
      choices: [{ id: "a", text: "A set of vertices connected by edges" }], code: null,
      starter: null, function_name: null, nodes: null, kind: null, generated: false,
      hints: { allowed: true, max_level: 4 },
      available_actions: ["answer", "hint", "explain", "progress", "solution", "stop"],
    },
    theory: null, result: null, hint: null, ...overrides,
  };
}

const theoryTurn = makeTurn({
  type: "theory", activity: null,
  theory: {
    unit: { id: "u001_graph_definition", title: "What is a graph?", goal: "Understand what is a graph?" },
    text: "A graph is vertices connected by edges...", checks_upcoming: 2,
  },
});

const advancedTurn = makeTurn({
  activity: { ...makeTurn().activity!, id: "e002_vertices_edges", skill: { id: "vertices_edges", title: "Vertices and edges" } },
  result: {
    correct: true, score: 1.0, feedback: "Correct.", confidence_signal: "calibrated",
    misconception: null, answered_by: "engine-deterministic", assisted: false, duplicate: false,
  },
});

beforeEach(() => {
  vi.clearAllMocks();
  setActivePinia(createPinia());
  mockEndpoints.makeIdempotencyKey.mockReturnValue("key-1");
});

/** Pinia wraps state in reactive proxies: compare against the raw target. */
function rawTurn(store: { turn: TurnEnvelope | null }): TurnEnvelope | null {
  return store.turn === null ? null : toRaw(store.turn);
}

function rawSession(store: { session: SessionInfo | null }): SessionInfo | null {
  return store.session === null ? null : toRaw(store.session);
}

import { useSessionStore } from "./session";
import { useUiStore } from "./ui";

describe("useSessionStore - initial state", () => {
  it("starts empty and idle with no pedagogical state", () => {
    const store = useSessionStore();
    expect(store.session).toBeNull();
    expect(store.turn).toBeNull();
    expect(store.plan).toBeNull();
    expect(store.status).toBe("idle");
    expect(store.inFlight).toBe(false);
    expect(store.pendingKey).toBeNull();
    expect(store.lastResult).toBeNull();
    expect(store.confidenceReported).toEqual([]);
  });
});

describe("useSessionStore - lifecycle (start/resume/snapshot/stop)", () => {
  it("start replaces session and turn with the server response (server truth)", async () => {
    mockEndpoints.startSession.mockResolvedValue({ turn: theoryTurn, session: sessionInfo });
    const store = useSessionStore();
    await store.start();
    expect(rawSession(store)).toBe(sessionInfo);
    expect(rawTurn(store)).toBe(theoryTurn);      // object identity: server truth, not rebuilt
    expect(store.status).toBe("ready");
    expect(mockEndpoints.startSession).toHaveBeenCalledWith("normal");  // pace passthrough; endpoint wraps it in the body
  });

  it("start propagates errors into store state and rethrows", async () => {
    mockEndpoints.startSession.mockRejectedValue(
      new ApiClientError(500, "INTERNAL_ERROR", "boom", false));
    const store = useSessionStore();
    await expect(store.start()).rejects.toThrow("boom");
    expect(store.status).toBe("error");
    expect(store.error?.code).toBe("INTERNAL_ERROR");
    expect(store.inFlight).toBe(false);
  });

  it("resume replaces the turn and session", async () => {
    mockEndpoints.resumeSession.mockResolvedValue({
      turn: advancedTurn, session: sessionInfo, resumed: true });
    const store = useSessionStore();
    await store.resume(1);
    expect(rawTurn(store)).toBe(advancedTurn);
    expect(rawSession(store)).toBe(sessionInfo);
  });

  it("loadSnapshot sets turn and plan and performs zero mutations", async () => {
    mockEndpoints.getSessionSnapshot.mockResolvedValue({
      session: sessionInfo, turn: advancedTurn,
      plan: { items: [], mastered: 1, pace_budget: "normal", questions: 2,
              remaining_minutes: 24, theory_blocks: 1, total_skills: 38, units: 4 },
    });
    const store = useSessionStore();
    await store.loadSnapshot(1);
    expect(rawTurn(store)).toBe(advancedTurn);
    expect(store.plan?.total_skills).toBe(38);
    expect(mockEndpoints.answer).not.toHaveBeenCalled();
    expect(mockEndpoints.stopSession).not.toHaveBeenCalled();
  });

  it("stop applies the ended turn and session", async () => {
    const pausedSession = { ...sessionInfo, status: "paused",
                            end_reason_code: "learner_stop",
                            end_reason_detail: "learner requested stop" };
    const ended = makeTurn({ type: "ended", activity: null,
      session: pausedSession,
      notice: { kind: "ended", text: "Session paused" } });
    mockEndpoints.stopSession.mockResolvedValue({ session: pausedSession, turn: ended,
      notice: { kind: "stopped", text: "Session paused - state persisted (learner requested "
              + "stop)." } });
    const store = useSessionStore();
    store.session = sessionInfo;
    await store.stop();
    expect(rawTurn(store)).toBe(ended);
    expect(store.session?.status).toBe("paused");
  });
});

describe("useSessionStore - theory-seen", () => {
  it("theorySeen replaces the turn with the authoritative activity turn", async () => {
    mockEndpoints.theorySeen.mockResolvedValue({ turn: advancedTurn });
    const store = useSessionStore();
    store.session = sessionInfo;                      // mutation precondition: active session
    await store.theorySeen();
    expect(rawTurn(store)).toBe(advancedTurn);
  });

  it("suppresses a duplicate theory acknowledgement while the first is in flight", async () => {
    mockEndpoints.theorySeen.mockReturnValueOnce(new Promise(() => {}));
    const store = useSessionStore();
    store.session = sessionInfo;
    store.turn = theoryTurn;
    void store.theorySeen();
    await store.theorySeen();
    expect(mockEndpoints.theorySeen).toHaveBeenCalledTimes(1);
  });
});

describe("useSessionStore - answer (server truth + idempotency + stale adoption)", () => {
  it("answer success replaces the turn with the server object and clears the pending key", async () => {
    mockEndpoints.answer.mockResolvedValue({ turn: advancedTurn, result: advancedTurn.result! });
    const store = useSessionStore();
    store.session = sessionInfo;
    const res = await store.submitAnswer("e001_graph_definition", "a");
    expect(res).not.toBeNull();
    expect(rawTurn(store)).toBe(advancedTurn);        // identity: server turn, not rebuilt
    expect(toRaw(store.lastResult!)).toBe(advancedTurn.result);
    expect(store.pendingKey).toBeNull();
    expect(mockEndpoints.answer).toHaveBeenCalledWith(1, "e001_graph_definition", "a", "key-1");
  });

  it("keeps the pending key across retryable failures and reuses it on retry", async () => {
    mockEndpoints.answer
      .mockRejectedValueOnce(new ApiClientError(503, "STORAGE_UNAVAILABLE",
        "Storage is temporarily unavailable.", true))
      .mockResolvedValueOnce({ turn: advancedTurn, result: advancedTurn.result! });
    const store = useSessionStore();
    store.session = sessionInfo;
    await expect(store.submitAnswer("e001_graph_definition", "a")).rejects.toThrow();
    expect(store.pendingKey).toBe("key-1");          // kept for the retry
    expect(store.status).toBe("error");
    await store.submitAnswer("e001_graph_definition", "a");  // retry with the SAME key
    expect(mockEndpoints.answer).toHaveBeenLastCalledWith(1, "e001_graph_definition", "a", "key-1");
    expect(store.pendingKey).toBeNull();             // cleared after success
  });

  it("clears the pending key on non-retryable errors", async () => {
    mockEndpoints.answer.mockRejectedValue(
      new ApiClientError(400, "VALIDATION_ERROR", "bad request", false));
    const store = useSessionStore();
    store.session = sessionInfo;
    await expect(store.submitAnswer("e001_graph_definition", "a")).rejects.toThrow();
    expect(store.pendingKey).toBeNull();
  });

  it("stale activity adopts the authoritative error.turn without resubmitting", async () => {
    const stale = new ApiClientError(409, "STALE_ACTIVITY",
      "This activity is no longer current.", false, { turn: advancedTurn });
    mockEndpoints.answer.mockRejectedValue(stale);
    const store = useSessionStore();
    store.session = sessionInfo;
    const ui = useUiStore();
    const res = await store.submitAnswer("e001_graph_definition", "a");
    expect(res).toBeNull();
    expect(rawTurn(store)).toBe(advancedTurn);       // adopted authoritative turn
    expect(store.pendingKey).toBeNull();
    expect(store.status).toBe("ready");
    expect(mockEndpoints.answer).toHaveBeenCalledTimes(1);  // no auto-resubmission
    expect(ui.staleAdopted).toBe(true);
    expect(ui.toasts.some((t) => t.text.includes("Skipped ahead"))).toBe(true);
  });

  it("enforces the single in-flight mutation rule", async () => {
    mockEndpoints.answer.mockReturnValueOnce(new Promise(() => {}));  // never resolves
    const store = useSessionStore();
    store.session = sessionInfo;
    void store.submitAnswer("e001_graph_definition", "a");
    const second = await store.submitAnswer("e001_graph_definition", "a");
    expect(second).toBeNull();                       // suppressed while in flight
    expect(mockEndpoints.answer).toHaveBeenCalledTimes(1);
  });

  it("C8 cleanup (F8): a keyed replay (result.duplicate=true) informs the learner the answer was already recorded", async () => {
    const ui = useUiStore();
    const replayResult = { ...advancedTurn.result!, duplicate: true };
    mockEndpoints.answer.mockResolvedValue({ turn: advancedTurn, result: replayResult });
    const store = useSessionStore();
    store.session = sessionInfo;
    await store.submitAnswer("e001_graph_definition", "a");
    expect(ui.toasts.some((t) => t.text === "Your answer was already recorded.")).toBe(true);
  });

  it("C8 cleanup (F8): a fresh submission (duplicate=false) raises no duplicate toast", async () => {
    const ui = useUiStore();
    mockEndpoints.answer.mockResolvedValue({ turn: advancedTurn, result: advancedTurn.result! });
    const store = useSessionStore();
    store.session = sessionInfo;
    await store.submitAnswer("e001_graph_definition", "a");
    expect(ui.toasts.some((t) => t.text === "Your answer was already recorded.")).toBe(false);
  });

  it("C8 retains the last submission for the retry affordance after a retryable failure", async () => {
    mockEndpoints.answer
      .mockRejectedValueOnce(new ApiClientError(503, "STORAGE_UNAVAILABLE",
        "Storage is temporarily unavailable.", true))
      .mockResolvedValueOnce({ turn: advancedTurn, result: advancedTurn.result! });
    const store = useSessionStore();
    store.session = sessionInfo;
    await expect(store.submitAnswer("e001_graph_definition", "a")).rejects.toThrow();
    expect(store.lastSubmission).toEqual({ activityId: "e001_graph_definition", answer: "a" });
    await store.submitAnswer("e001_graph_definition", "a");  // retry: same key, same answer
    expect(mockEndpoints.answer).toHaveBeenLastCalledWith(1, "e001_graph_definition", "a", "key-1");
    expect(store.lastSubmission).toBeNull();
  });

  it("C8 clears the retained submission on stale adoption (never resubmits)", async () => {
    const stale = new ApiClientError(409, "STALE_ACTIVITY",
      "This activity is no longer current.", false, { turn: advancedTurn });
    mockEndpoints.answer.mockRejectedValue(stale);
    const store = useSessionStore();
    store.session = sessionInfo;
    await store.submitAnswer("e001_graph_definition", "a");
    expect(store.lastSubmission).toBeNull();
    expect(mockEndpoints.answer).toHaveBeenCalledTimes(1);
  });

  it("C8 clears the retained submission on non-retryable errors", async () => {
    mockEndpoints.answer.mockRejectedValue(
      new ApiClientError(400, "VALIDATION_ERROR", "bad request", false));
    const store = useSessionStore();
    store.session = sessionInfo;
    await expect(store.submitAnswer("e001_graph_definition", "a")).rejects.toThrow();
    expect(store.lastSubmission).toBeNull();
  });

  it("C8 a successful authoritative load clears the stale-adopted recovery state", async () => {
    const ui = useUiStore();
    ui.markStaleAdopted();
    expect(ui.staleAdopted).toBe(true);
    mockEndpoints.getSessionSnapshot.mockResolvedValue({
      session: sessionInfo, turn: advancedTurn,
      plan: { items: [], mastered: 1, pace_budget: "normal", questions: 2,
              remaining_minutes: 24, theory_blocks: 1, total_skills: 38, units: 4 },
    });
    const store = useSessionStore();
    await store.loadSnapshot(1);
    expect(ui.staleAdopted).toBe(false);
  });

  it("C8 a successful resume clears the stale-adopted recovery state", async () => {
    const ui = useUiStore();
    ui.markStaleAdopted();
    mockEndpoints.resumeSession.mockResolvedValue({
      turn: advancedTurn, session: sessionInfo, resumed: true });
    const store = useSessionStore();
    await store.resume(1);
    expect(ui.staleAdopted).toBe(false);
  });

  it("C8 cleanup (F11): a later authoritative action clears an obsolete retryable answer error", async () => {
    mockEndpoints.answer.mockRejectedValue(new ApiClientError(503, "STORAGE_UNAVAILABLE",
      "Storage is temporarily unavailable.", true));
    const store = useSessionStore();
    store.session = sessionInfo;
    store.turn = makeTurn();                       // the learner is looking at the current activity
    await expect(store.submitAnswer("e001_graph_definition", "a")).rejects.toThrow();
    expect(store.error?.retryable).toBe(true);
    expect(store.lastSubmission).toEqual({ activityId: "e001_graph_definition", answer: "a" });
    expect(store.pendingKey).toBe("key-1");
    // the learner uses a different authoritative action instead of retrying
    const hinted = makeTurn({ hint: { level: 1, kind: "socratic", text: "Think about dots and lines." } });
    mockEndpoints.hint.mockResolvedValue({ turn: hinted });
    await store.requestHint();
    expect(store.error).toBeNull();                 // obsolete answer error must not linger
    expect(store.lastSubmission).toBeNull();        // nothing left to retry
    expect(store.pendingKey).toBeNull();            // the voided key is never reused
  });

  it("never locally invents pedagogical state (raw target is the server object)", async () => {
    mockEndpoints.answer.mockResolvedValue({ turn: advancedTurn, result: advancedTurn.result! });
    const store = useSessionStore();
    store.session = sessionInfo;
    await store.submitAnswer("e001_graph_definition", "a");
    expect(toRaw(store.turn!)).toBe(advancedTurn);
    expect(JSON.stringify(toRaw(store.turn!))).toBe(JSON.stringify(advancedTurn));
  });
});

describe("useSessionStore - hint / reveal / explain / confidence", () => {
  it("hint replaces the turn (hint lives in the envelope)", async () => {
    const hinted = makeTurn({ hint: { level: 1, kind: "socratic", text: "Think about dots and lines." } });
    mockEndpoints.hint.mockResolvedValue({ turn: hinted });
    const store = useSessionStore();
    store.session = sessionInfo;
    store.turn = advancedTurn;
    await store.requestHint();
    expect(rawTurn(store)).toBe(hinted);
    expect(store.turn.hint?.level).toBe(1);
  });

  it("revealSolution stores the solution text and replaces the turn", async () => {
    const revealed = makeTurn({ notice: { kind: "solution_revealed", text: "Reference explanation..." } });
    mockEndpoints.revealSolution.mockResolvedValue({ solution: "Reference explanation...", turn: revealed });
    const store = useSessionStore();
    store.session = sessionInfo;
    store.turn = advancedTurn;
    await store.revealSolution();
    expect(store.lastSolution).toBe("Reference explanation...");
    expect(rawTurn(store)).toBe(revealed);
  });

  it("explainCurrent stores the explanation without mutating the turn", async () => {
    mockEndpoints.explain.mockResolvedValue({ explanation: "A graph is..." });
    const store = useSessionStore();
    store.session = sessionInfo;
    store.turn = advancedTurn;
    const before = store.turn;
    await store.explainCurrent();
    expect(store.lastExplanation).toBe("A graph is...");
    expect(store.turn).toBe(before);                 // same reactive proxy: untouched
  });

  it("confidence reporting is in-memory bookkeeping only (turn untouched)", async () => {
    mockEndpoints.confidence.mockResolvedValue({ recorded: true, skill_id: "graph_definition" });
    const store = useSessionStore();
    store.session = sessionInfo;
    store.turn = advancedTurn;
    const before = store.turn;
    await store.reportConfidence("graph_definition", 3);
    expect(store.turn).toBe(before);                 // no local turn mutation
    expect(store.hasReportedConfidence("graph_definition")).toBe(true);
    expect(store.hasReportedConfidence("other")).toBe(false);
  });
});
