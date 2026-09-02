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

import * as endpoints from "../api/endpoints";

const mockEndpoints = vi.mocked(endpoints);

beforeEach(() => {
  vi.clearAllMocks();
  setActivePinia(createPinia());
  mockEndpoints.makeIdempotencyKey.mockReturnValue("key-1");
});

import { useLearnerStore } from "./learner";

describe("useLearnerStore", () => {
  it("fetchHome stores the home composition", async () => {
    mockEndpoints.home.mockResolvedValue({
      daily: { target_units: 4, completed_units: 1, status: "active" },
      plan: { items: [], mastered: 1, pace_budget: "normal", questions: 2,
              remaining_minutes: 24.5, theory_blocks: 1, total_skills: 38, units: 4 },
      progress_summary: { mastered: 1, total_skills: 38 },
      resume: { available: true, session_id: 1, pace: "normal" },
    });
    const store = useLearnerStore();
    await store.fetchHome();
    expect(store.home?.plan.total_skills).toBe(38);
    expect(store.home?.resume.available).toBe(true);
    expect(store.homeLoading).toBe(false);
    expect(store.homeError).toBeNull();
  });

  it("fetchProgress stores the qualitative report", async () => {
    mockEndpoints.progress.mockResolvedValue({
      daily: { date: "2026-09-03", target_units: 4, completed_units: 0, status: "active" },
      skills: [{ skill: "graph_definition", title: "What is a graph?", section: "foundations",
                 module: "A", state: "INTRODUCED", evidence: 2, mastered: false,
                 boundary: false, optional: false }],
    });
    const store = useLearnerStore();
    await store.fetchProgress();
    expect(store.progress?.skills).toHaveLength(1);
    expect(store.progress?.skills[0].state).toBe("INTRODUCED");
  });

  it("records fetch errors instead of throwing", async () => {
    mockEndpoints.home.mockRejectedValue(new Error("network down"));
    const store = useLearnerStore();
    await store.fetchHome();
    expect(store.homeError).toBe("network down");
    expect(store.home).toBeNull();
  });
});
