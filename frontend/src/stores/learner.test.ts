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
import type { AnswerResponse, SessionInfo, TurnEnvelope } from "../../api/types";

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
