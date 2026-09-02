/**
 * Endpoint tests for the C2 typed API layer (design doc §7, capture-backed
 * fixtures from plans/V1_SLICE_1C_API_CAPTURE.json). Deterministic: fetch stubbed.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import * as endpoints from "./endpoints";
import {
  answerResponse, homeResponse, hintTurn, progressResponse, replayResponse,
  snapshotResponse, startResponse, staleError409, stopResponse, resumeResponse,
} from "./fixtures";

const ok = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const err = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

afterEach(() => {
  vi.unstubAllGlobals();
});

/** Last recorded fetch call as (url, init). */
function lastCall(): { url: string; init: { method: string; body?: string; headers: Record<string, string> } } {
  const fetchMock = vi.mocked(globalThis.fetch);
  const [url, init] = fetchMock.mock.calls[fetchMock.mock.calls.length - 1] as
    [string, { method: string; body?: string; headers: Record<string, string> }];
  return { url, init };
}

describe("endpoint surface", () => {
  it("exports exactly the 12 endpoint functions plus the key generator", () => {
    const fns = Object.keys(endpoints).filter(
      (k) => typeof (endpoints as Record<string, unknown>)[k] === "function");
    expect(fns.sort()).toEqual([
      "answer", "confidence", "explain", "getSessionSnapshot", "hint", "home",
      "makeIdempotencyKey", "progress", "revealSolution", "resumeSession",
      "startSession", "stopSession", "theorySeen",
    ].sort());
  });
});

describe("endpoint request shapes (all 12 routes)", () => {
  it("startSession: POST /api/v1/sessions with pace", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(ok(startResponse))));
    const body = await endpoints.startSession();
    expect(body.turn.type).toBe("theory");
    expect(body.turn.theory?.unit.id).toBe("u001_graph_definition");
    expect(body.session.id).toBe(1);
    const { url, init } = lastCall();
    expect(url).toBe("http://127.0.0.1:8000/api/v1/sessions");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ pace: "normal" });
  });

  it("getSessionSnapshot: GET /api/v1/sessions/{id}", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(ok(snapshotResponse))));
    const body = await endpoints.getSessionSnapshot(1);
    expect(body.plan.total_skills).toBe(38);
    const { url, init } = lastCall();
    expect(url).toBe("http://127.0.0.1:8000/api/v1/sessions/1");
    expect(init.method).toBe("GET");
  });

  it("resumeSession: POST …/resume", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(ok(resumeResponse))));
    const body = await endpoints.resumeSession(1);
    expect(body.resumed).toBe(true);
    const { url, init } = lastCall();
    expect(url).toBe("http://127.0.0.1:8000/api/v1/sessions/1/resume");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({});
  });

  it("stopSession: POST …/stop with and without reason", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(ok(stopResponse))));
    await endpoints.stopSession(1);
    let { url, init } = lastCall();
    expect(url).toBe("http://127.0.0.1:8000/api/v1/sessions/1/stop");
    expect(JSON.parse(init.body as string)).toEqual({});
    await endpoints.stopSession(1, "break");
    ({ url, init } = lastCall());
    expect(JSON.parse(init.body as string)).toEqual({ reason: "break" });
  });

  it("theorySeen: POST …/theory-seen", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(ok({ turn: startResponse.turn }))));
    await endpoints.theorySeen(1);
    const { url, init } = lastCall();
    expect(url).toBe("http://127.0.0.1:8000/api/v1/sessions/1/theory-seen");
    expect(init.method).toBe("POST");
  });

  it("answer: POST …/answer with answer body and Idempotency-Key", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(ok(answerResponse))));
    await endpoints.answer(1, "e001_graph_definition", "a", "K1");
    const { url, init } = lastCall();
    expect(url).toBe("http://127.0.0.1:8000/api/v1/sessions/1/activities/e001_graph_definition/answer");
    expect(init.method).toBe("POST");
    expect(init.headers["Idempotency-Key"]).toBe("K1");
    expect(JSON.parse(init.body as string)).toEqual({ answer: "a" });
  });

  it("hint / revealSolution / explain: POST …/activities/{id}/*", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(ok({ turn: hintTurn }))));
    await endpoints.hint(1, "e001_graph_definition");
    let { url, init } = lastCall();
    expect(url).toBe("http://127.0.0.1:8000/api/v1/sessions/1/activities/e001_graph_definition/hint");
    expect(JSON.parse(init.body as string)).toEqual({});
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(ok({ solution: "s", turn: hintTurn }))));
    await endpoints.revealSolution(1, "e001_graph_definition");
    ({ url, init } = lastCall());
    expect(url).toBe("http://127.0.0.1:8000/api/v1/sessions/1/activities/e001_graph_definition/reveal-solution");
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(ok({ explanation: "e" }))));
    await endpoints.explain(1, "e001_graph_definition");
    ({ url, init } = lastCall());
    expect(url).toBe("http://127.0.0.1:8000/api/v1/sessions/1/activities/e001_graph_definition/explain");
  });

  it("confidence: POST …/confidence with skill_id and rating", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(ok({ recorded: true, skill_id: "graph_definition" }))));
    await endpoints.confidence(1, "graph_definition", 3);
    const { url, init } = lastCall();
    expect(url).toBe("http://127.0.0.1:8000/api/v1/sessions/1/confidence");
    expect(JSON.parse(init.body as string)).toEqual({ skill_id: "graph_definition", rating: 3 });
  });

  it("progress / home: GET endpoints", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(ok(progressResponse))));
    await endpoints.progress();
    let { url, init } = lastCall();
    expect(url).toBe("http://127.0.0.1:8000/api/v1/learner/progress");
    expect(init.method).toBe("GET");
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(ok(homeResponse))));
    await endpoints.home();
    ({ url, init } = lastCall());
    expect(url).toBe("http://127.0.0.1:8000/api/v1/home");
    expect(init.method).toBe("GET");
  });
});

describe("idempotency-key semantics (design §4.5)", () => {
  it("reuses the SAME key when the caller retries the same submission", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(ok(answerResponse))
      .mockResolvedValueOnce(ok({ turn: answerResponse.turn, result: replayResponse.result })));
    await endpoints.answer(1, "e001_graph_definition", "a", "K1");
    await endpoints.answer(1, "e001_graph_definition", "a", "K1");
    const [, init1] = vi.mocked(globalThis.fetch).mock.calls[0] as [string, { headers: Record<string, string> }];
    const [, init2] = vi.mocked(globalThis.fetch).mock.calls[1] as [string, { headers: Record<string, string> }];
    expect(init1.headers["Idempotency-Key"]).toBe("K1");
    expect(init2.headers["Idempotency-Key"]).toBe("K1");
  });

  it("generates a fresh unique key per call when none is provided", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(ok(answerResponse))));
    await endpoints.answer(1, "e001_graph_definition", "a");
    await endpoints.answer(1, "e001_graph_definition", "a");
    const [, init1] = vi.mocked(globalThis.fetch).mock.calls[0] as [string, { headers: Record<string, string> }];
    const [, init2] = vi.mocked(globalThis.fetch).mock.calls[1] as [string, { headers: Record<string, string> }];
    const k1 = init1.headers["Idempotency-Key"];
    const k2 = init2.headers["Idempotency-Key"];
    expect(k1).toBeTruthy();
    expect(k2).toBeTruthy();
    expect(k1).not.toBe(k2);
  });

  it("makeIdempotencyKey produces unique keys", () => {
    const keys = new Set(Array.from({ length: 100 }, () => endpoints.makeIdempotencyKey()));
    expect(keys.size).toBe(100);
  });
});

describe("real captured response/error shapes", () => {
  it("parses the real stale-activity 409 and exposes the fresh turn detail", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(err(staleError409.status, staleError409.body)));
    const exc = await endpoints.answer(1, "e001_graph_definition", "a", "K2")
      .catch((e: unknown) => e);
    const e = exc as unknown as { code: string; details: { turn: { activity: { id: string } } } };
    expect(e.code).toBe("STALE_ACTIVITY");
    expect(e.details.turn.activity.id).toBe("e002_vertices_edges");
  });

  it("parses the real replay response (duplicate=true) with the authoritative current turn", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(ok(replayResponse))));
    const body = await endpoints.answer(1, "e001_graph_definition", "a", "K1");
    expect(body.result.duplicate).toBe(true);
    expect(body.result.correct).toBe(true);
    expect(body.turn.activity?.id).toBe("e002_vertices_edges");
  });

  it("never exposes grading-secret keys in projected activity payloads", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(ok(answerResponse))));
    const body = await endpoints.answer(1, "e001_graph_definition", "a", "K1");
    const dumped = JSON.stringify(body);
    for (const secret of ["answer_id:", "expected_output:", "\"solution\":", "\"tests\":",
      "acceptable:", "expected_edges:", "reference_points:", "min_points:", "hint_ladder:",
      "difficulty:", "required_capabilities:"]) {
      expect(dumped.includes(secret)).toBe(false);
    }
  });
})
