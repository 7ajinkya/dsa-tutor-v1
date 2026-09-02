/**
 * Public API types — derived from the REAL 1B responses captured in
 * plans/V1_SLICE_1C_API_CAPTURE.json (28 live entries) and frozen by
 * docs/V1_SLICE_1_API_BOUNDARY_DESIGN.md v1.2.
 *
 * Projection-only: these types describe what the server sends. Grading secrets
 * (answer_id, expected_output, solution, tests, acceptable, expected_edges,
 * reference_points) and internal engine/provider fields are intentionally absent.
 */

export type Pace = "slow" | "normal" | "fast";

export type ErrorCode =
  | "VALIDATION_ERROR"
  | "MALFORMED_JSON"
  | "MISSING_IDEMPOTENCY_KEY"
  | "INVALID_PACE"
  | "INVALID_CONFIDENCE"
  | "UNKNOWN_SKILL"
  | "SESSION_NOT_FOUND"
  | "ACTIVITY_NOT_FOUND"
  | "NO_SOLUTION"
  | "SESSION_ALREADY_ACTIVE"
  | "NO_SESSION_TO_RESUME"
  | "SESSION_NOT_ACTIVE"
  | "SESSION_MISMATCH"
  | "ANOTHER_SESSION_ACTIVE"
  | "STALE_ACTIVITY"
  | "LADDER_EXHAUSTED"
  | "AI_UNAVAILABLE"
  | "STORAGE_UNAVAILABLE"
  | "INTERNAL_ERROR"
  | "CONFIG_ERROR";

/** Client-side transport failures (no server envelope exists for these). */
export type ClientOnlyErrorCode = "NETWORK_ERROR" | "UNPARSEABLE_RESPONSE";

export interface DailyTarget {
  target_units: number;
  completed_units: number;
  status: string;
}

export interface SessionInfo {
  id: number;
  status: string;
  pace: string;
  budget_minutes: number;
  remaining_minutes: number | null;
  started_at: string | null;
  ended_at: string | null;
  end_reason_code: string | null;
  end_reason_detail: string | null;
  daily: DailyTarget | null;
  units_completed?: number;
}

export interface Step {
  action: string;
  why: string[];
  sequence: "planned" | "adaptive";
}

export interface UnitRef {
  id: string;
  title: string;
  goal: string;
}

export interface SkillRef {
  id: string;
  title: string;
}

export interface Choice {
  id: string;
  text: string;
}

export type ActivityMode =
  | "teach" | "practice" | "assess" | "apply"
  | "remediation" | "prerequisite_revisit" | "repeat" | "variation"
  | "increase_difficulty" | "reduce_difficulty" | "advance"
  | (string & {});

export type AnswerFormat =
  | "letter" | "text" | "code" | "lines" | "big_o" | "edges"
  | (string & {});

export interface HintsInfo {
  allowed: boolean;
  max_level: number;
}

/** Per-type public fields only — see design §2.3 map; grading secrets never appear. */
export interface Activity {
  id: string;
  type: "mcq" | "free_form" | "code_writing" | "code_tracing"
      | "output_prediction" | "complexity_question" | "graph_construction"
      | (string & {});
  mode: ActivityMode;
  purpose: string;
  prompt: string;
  answer_format: AnswerFormat;
  position: { index: number; of: number } | null;
  unit: UnitRef | null;
  skill: SkillRef;
  choices: Choice[] | null;            // mcq
  code: string | null;                 // code_tracing / output_prediction
  starter: string | null;              // code_writing
  function_name: string | null;        // code_writing
  nodes: string[] | null;              // graph_construction
  kind: string | null;                 // complexity_question
  generated: boolean;
  hints: HintsInfo;
  available_actions: string[];
}

export interface Theory {
  unit: UnitRef;
  text: string;
  checks_upcoming: number;
}

export type AnsweredBy =
  | "engine-deterministic" | "ai" | "builtin" | "builtin-fallback"
  | (string & {});

export interface Result {
  correct: boolean | null;
  score: number | null;
  feedback: string;
  confidence_signal: string | null;
  misconception: string | null;
  answered_by: AnsweredBy;
  assisted: boolean | null;
  duplicate: boolean;
}

export interface HintPayload {
  level: number;
  kind: string;
  text: string;
}

export interface Notice {
  kind: string;
  text: string;
}

export interface ConfidenceRequest {
  skill_id: string;
}

export type TurnType = "activity" | "theory" | "ended" | "notice";

/** Universal turn envelope (design §5.1). */
export interface TurnEnvelope {
  type: TurnType;
  session: SessionInfo | null;
  step: Step | null;
  notice: Notice | null;
  activity: Activity | null;
  theory: Theory | null;
  result: Result | null;
  hint: HintPayload | null;
  confidence_request?: ConfidenceRequest;
}

export interface PlanItem {
  skill: string;
  title: string;
  type: string;
  theory: boolean;
  questions: number;
}

export interface PlanPreview {
  items: PlanItem[];
  mastered: number;
  pace_budget: string;
  questions: number;
  remaining_minutes: number | null;
  theory_blocks: number;
  total_skills: number;
  units: number;
}

export interface PlanRow {
  skill: string;
  title: string;
  section: string;
  module: string;
  state: string;
  evidence: number;
  mastered: boolean;
  boundary: boolean;
  optional: boolean;
}

export interface ProgressReport {
  daily: { date: string; target_units: number; completed_units: number; status: string };
  skills: PlanRow[];
}

export interface HomePayload {
  daily: DailyTarget;
  plan: PlanPreview;
  progress_summary: { mastered: number; total_skills: number };
  resume: { available: boolean; session_id: number | null; pace: string | null };
}

/** Error envelope (design §4.0). `details` carries the non-standard extra keys
 *  (turn / activity / resume / session_id) served by specific errors. */
export interface ErrorEnvelope {
  error: {
    code: ErrorCode | (string & {});
    message: string;
    retryable: boolean;
  } & Record<string, unknown>;
}

// ------------------------------------------------------------ per-endpoint responses

export interface TurnResponse {
  turn: TurnEnvelope;
}

export interface StartResponse extends TurnResponse {
  session: SessionInfo;
}

export interface SnapshotResponse {
  session: SessionInfo | null;
  turn: TurnEnvelope;
  plan: PlanPreview;
}

export interface ResumeResponse extends TurnResponse {
  session: SessionInfo;
  resumed: boolean;
}

export interface StopResponse {
  session: SessionInfo | null;
  turn: TurnEnvelope | null;
  notice: Notice;
}

export interface AnswerResponse extends TurnResponse {
  /** Top-level result: the evaluation for new submissions; the stored evaluation
   *  with duplicate=true for keyed replays (design §4.5). */
  result: Result;
}

export interface RevealResponse {
  solution: string;
  turn: TurnEnvelope;
}

export interface ExplainResponse {
  explanation: string;
}

export interface ConfidenceResponse {
  recorded: boolean;
  skill_id: string;
}
