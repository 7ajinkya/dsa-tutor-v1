/**
 * Transport tests for the C2 API client (design doc §7).
 * Deterministic: fetch is stubbed; no live backend.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiClientError, API_BASE, request } from "./client";

const ok = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const raw = (text: string, status = 500) => new Response(text, { status });
const err = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("request transport", () => {
  it("parses successful JSON responses (GET, no body, no content-type)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok({ hello: 1 }));
    vi.stubGlobal("fetch", fetchMock);
    const out = await request<{ hello: number }>("GET", "/api/v1/home");
    expect(out).toEqual({ hello: 1 });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${API_BASE}/api/v1/home`);
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
    expect(init.headers["Content-Type"]).toBeUndefined();
  });

  it("sends POST bodies as JSON with Content-Type", async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok({ recorded: true }));
    vi.stubGlobal("fetch", fetchMock);
    await request("POST", "/api/v1/sessions", { body: { pace: "normal" } });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${API_BASE}/api/v1/sessions`);
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ pace: "normal" });
    expect(init.headers["Content-Type"]).toBe("application/json");
  });

  it("attaches the Idempotency-Key header when provided", async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok({}));
    vi.stubGlobal("fetch", fetchMock);
    await request("POST", "/api/v1/sessions/1/activities/x/answer",
      { body: { answer: "a" }, idempotencyKey: "K1" });
    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers["Idempotency-Key"]).toBe("K1");
  });

  it("throws ApiClientError from the frozen error envelope (409 STALE_ACTIVITY with details)", async () => {
    const envelope = {
      error: {
        code: "STALE_ACTIVITY",
        message: "This activity is no longer current; the authoritative turn is included.",
        retryable: false,
        turn: { type: "activity", activity: { id: "e002_vertices_edges" } },
      },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(err(409, envelope)));
    const exc = await request("POST", "/api/v1/sessions/1/activities/e001/answer",
      { body: { answer: "a" }, idempotencyKey: "K2" })
      .catch((e: unknown) => e);
    expect(exc).toBeInstanceOf(ApiClientError);
    const apiErr = exc as ApiClientError;
    expect(apiErr.status).toBe(409);
    expect(apiErr.code).toBe("STALE_ACTIVITY");
    expect(apiErr.retryable).toBe(false);
    expect((apiErr.details.turn as { activity: { id: string } }).activity.id).toBe("e002_vertices_edges");
  });

  it("maps retryable 503 envelopes to retryable ApiClientError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(err(503, {
      error: { code: "STORAGE_UNAVAILABLE", message: "Storage is temporarily unavailable.", retryable: true },
    })));
    const exc = await request("GET", "/api/v1/home").catch((e: unknown) => e);
    expect(exc).toBeInstanceOf(ApiClientError);
    expect((exc as ApiClientError).code).toBe("STORAGE_UNAVAILABLE");
    expect((exc as ApiClientError).retryable).toBe(true);
  });

  it("maps client-side network failure to retryable NETWORK_ERROR", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));
    const exc = await request("GET", "/api/v1/home").catch((e: unknown) => e);
    expect(exc).toBeInstanceOf(ApiClientError);
    expect((exc as ApiClientError).code).toBe("NETWORK_ERROR");
    expect((exc as ApiClientError).retryable).toBe(true);
  });

  it("maps a non-JSON error body to UNPARSEABLE_RESPONSE (no envelope)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(raw("<html>boom</html>", 500)));
    const exc = await request("GET", "/api/v1/home").catch((e: unknown) => e);
    expect(exc).toBeInstanceOf(ApiClientError);
    expect((exc as ApiClientError).code).toBe("UNPARSEABLE_RESPONSE");
    expect((exc as ApiClientError).retryable).toBe(false);
  });

  it("maps a non-JSON 2xx body to UNPARSEABLE_RESPONSE", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(raw("not json", 200)));
    const exc = await request("GET", "/api/v1/home").catch((e: unknown) => e);
    expect(exc).toBeInstanceOf(ApiClientError);
    expect((exc as ApiClientError).code).toBe("UNPARSEABLE_RESPONSE");
  });

  it("builds URLs from API_BASE without double slashes", async () => {
    expect(API_BASE.endsWith("/")).toBe(false);
    const fetchMock = vi.fn().mockResolvedValue(ok({}));
    vi.stubGlobal("fetch", fetchMock);
    await request("GET", "/api/v1/home");
    expect(fetchMock.mock.calls[0][0]).toBe(`${API_BASE}/api/v1/home`);
  });
})
