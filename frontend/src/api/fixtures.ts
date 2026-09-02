/**
 * Fixtures copied from the REAL 1B responses captured live in
 * plans/V1_SLICE_1C_API_CAPTURE.json (entries 01/03/04/05/06/12/13/14/15/17).
 * Keys and types are exact; long string values are trimmed but shape-identical.
 * Do not invent payload shapes here.
 */
import type {
  AnswerResponse, HomePayload, ProgressReport, ResumeResponse, SnapshotResponse,
  StartResponse, StopResponse, TurnEnvelope,
} from "./types";

const SESSION = {
  id: 1,
  status: "active",
  pace: "normal",
  budget_minutes: 25,
  remaining_minutes: 24.998166683333332,
  started_at: "2026-09-02T18:54:33.280326+00:00",
  ended_at: null,
  end_reason_code: null,
  end_reason_detail: null,
  daily: { target_units: 4, completed_units: 0, status: "active" },
};

export const startResponse: StartResponse = {
  turn: {
    type: "theory",
    session: SESSION,
    step: {
      action: "advance",
      why: [
        "skill 'graph_definition' not yet mastered (required dims: knowledge)",
        "advance to 'u001_graph_definition'",
      ],
      sequence: "planned",
    },
    notice: null,
    activity: null,
    theory: {
      unit: { id: "u001_graph_definition", title: "What is a graph? - study", goal: "Understand what is a graph?" },
      text: "A graph is a set of vertices connected by edges... (trimmed study text)",
      checks_upcoming: 2,
    },
    result: null,
    hint: null,
  },
  session: SESSION,
};

export const answerResponse: AnswerResponse = {
  turn: {
    type: "activity",
    session: SESSION,
    step: { action: "advance", why: ["answer recorded - evidence for 'graph_definition'"], sequence: "planned" },
    notice: null,
    activity: {
      id: "e002_vertices_edges",
      type: "mcq",
      mode: "practice",
      purpose: "Practice check on 'Vertices and edges'",
      prompt: "Which statement best describes vertices and edges?",
      answer_format: "letter",
      position: { index: 1, of: 2 },
      unit: { id: "u002_vertices_edges", title: "Vertices and edges", goal: "Tell vertices and edges apart" },
      skill: { id: "vertices_edges", title: "Vertices and edges" },
      choices: [
        { id: "a", text: "Vertices are the dots; edges are the lines between them" },
        { id: "b", text: "Vertices are the lines; edges are the dots" },
        { id: "c", text: "They are the same thing" },
        { id: "d", text: "Edges only exist in directed graphs" },
      ],
      code: null,
      starter: null,
      function_name: null,
      nodes: null,
      kind: null,
      generated: false,
      hints: { allowed: true, max_level: 4 },
      available_actions: ["answer", "hint", "explain", "progress", "solution", "stop"],
    },
    theory: null,
    result: {
      correct: true,
      score: 1.0,
      feedback: "Correct - a graph is vertices connected by edges.",
      confidence_signal: "calibrated",
      misconception: null,
      answered_by: "engine-deterministic",
      assisted: false,
      duplicate: false,
    },
    hint: null,
  },
  result: {
    correct: true,
    score: 1.0,
    feedback: "Correct - a graph is vertices connected by edges.",
    confidence_signal: "calibrated",
    misconception: null,
    answered_by: "engine-deterministic",
    assisted: false,
    duplicate: false,
  },
};

export const replayResponse: { turn: TurnEnvelope; result: AnswerResponse["result"] } = {
  turn: answerResponse.turn, // authoritative CURRENT turn after the original submission advanced
  result: {
    correct: true,
    score: 1.0,
    feedback: "Correct - a graph is vertices connected by edges.",
    confidence_signal: "calibrated",
    misconception: null,
    answered_by: "engine-deterministic",
    assisted: false,
    duplicate: true,
  },
};

export const staleError409 = {
  status: 409,
  body: {
    error: {
      code: "STALE_ACTIVITY",
      message: "This activity is no longer current; the authoritative turn is included.",
      retryable: false,
      turn: answerResponse.turn,
    },
  },
};

export const hintTurn: TurnEnvelope = {
  type: "activity",
  session: SESSION,
  step: null,
  notice: null,
  activity: answerResponse.turn.activity,
  theory: null,
  result: null,
  hint: { level: 1, kind: "socratic", text: "Think about what the dots and lines could represent." },
};

export const snapshotResponse: SnapshotResponse = {
  session: SESSION,
  turn: answerResponse.turn,
  plan: {
    items: [
      { skill: "graph_definition", title: "What is a graph?", type: "teach", theory: true, questions: 2 },
      { skill: "vertices_edges", title: "Vertices and edges", type: "practice", theory: false, questions: 2 },
    ],
    mastered: 1,
    pace_budget: "normal",
    questions: 2,
    remaining_minutes: 24.99,
    theory_blocks: 1,
    total_skills: 38,
    units: 4,
  },
};

export const stopResponse: StopResponse = {
  session: {
    ...SESSION,
    status: "paused",
    ended_at: "2026-09-02T19:01:00.000000+00:00",
    end_reason_code: "learner_stop",
    end_reason_detail: "learner requested stop",
  },
  turn: {
    type: "ended",
    session: { ...SESSION, status: "paused", units_completed: 1 },
    step: null,
    notice: { kind: "ended", text: "Session paused - state persisted (learner requested stop)." },
    activity: null,
    theory: null,
    result: null,
    hint: null,
  },
  notice: { kind: "stopped", text: "Session paused - state persisted (learner requested stop)." },
};

export const resumeResponse: ResumeResponse = {
  turn: answerResponse.turn,
  session: { ...SESSION, status: "active" },
  resumed: true,
};

export const progressResponse: ProgressReport = {
  daily: { date: "2026-09-03", target_units: 4, completed_units: 0, status: "active" },
  skills: [
    {
      skill: "graph_definition",
      title: "What is a graph?",
      section: "foundations",
      module: "A - Graph mental model",
      state: "INTRODUCED",
      evidence: 2,
      mastered: false,
      boundary: false,
      optional: false,
    },
  ],
};

export const homeResponse: HomePayload = {
  daily: { target_units: 4, completed_units: 1, status: "active" },
  plan: {
    items: [
      { skill: "vertices_edges", title: "Vertices and edges", type: "practice", theory: false, questions: 2 },
    ],
    mastered: 1,
    pace_budget: "normal",
    questions: 2,
    remaining_minutes: 24.5,
    theory_blocks: 1,
    total_skills: 38,
    units: 4,
  },
  progress_summary: { mastered: 1, total_skills: 38 },
  resume: { available: true, session_id: 1, pace: "normal" },
};
