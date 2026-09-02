# V1 Slice 1A — HTTP API Boundary Design

| | |
|---|---|
| **Document version** | 1.2 (consolidated review revision — supersedes v1.1; implementation-ready) |
| **Date** | 2026-09-02 |
| **Authorized by** | Plan `plans/V1_SLICE_1A_PLAN.md` v0.2.0, tagged `plan-slice1a-v1.0.0` (commit `3fb229e`) |
| **Scope** | Design/inspection ONLY. No HTTP implementation, no engine/domain/schema/curriculum/AI changes. |
| **Source of truth** | The actual V1 codebase (files cited inline as `file:line`); the baseline report was used only as orientation. |
| **Status** | DELIVERED FOR REVIEW — Slice 1B must not start until this document is approved. |

**Navigation:** [1 Current boundary](#1-current-application-boundary) · [2 TurnView](#2-turnview-inspection) · [3 Endpoints](#3-proposed-endpoints--classification) · [4 Schemas](#4-public-json-schemas) · [5 Activity model](#5-activity-response-model) · [6 Mapping](#6-turnview--public-api-mapping) · [7 Session model](#7-session-model) · [8 Errors](#8-error-handling) · [9 Security](#9-securityexposure-boundary) · [10 Storage](#10-storage) · [11 Tests](#11-testing-strategy) · [12 Invariants](#12-architectural-invariants) · [13 Migration](#13-migration-consideration) · [14 Open questions](#14-open-questions--decisions-needed) · [A Gate results](#appendix-a--slice-1a-gate-results)

---

## 1. Current application boundary

### 1.1 Actual flow (verified in code)

```
CLI  (dsa_tutor/cli.py: commands;  dsa_tutor/app/interactive.py: rendering only)
  -> TutorService  (dsa_tutor/app/service.py)          use cases + ONE transaction per interaction
       -> LearningEngine (dsa_tutor/domain/engine.py)   DETERMINISTIC progression, no I/O, never calls AI
       -> AI Tutor       (dsa_tutor/ai/*)               5 operations, schema-validated observations, never mutates state
       -> Storage        (dsa_tutor/persistence/*)      MySQLStorage | MemoryStorage (one interface)
            -> MySQL 8 (15 tables) / in-memory
```

The CLI renders `TurnView` objects and never decides (`interactive.py` docstring: "Renders; it never decides").
This is exactly the seam the HTTP layer will occupy: **transport adapter over `TutorService`**.

### 1.2 TutorService public method inventory (complete — runtime-verified)

Enumeration cross-checked at runtime with `inspect.getmembers(TutorService, predicate=inspect.isfunction)`
(12 public methods; no others). Line references are to `dsa_tutor/app/service.py` unless noted.

| # | Method | Parameters | Returns | Side effects | Persistence | Errors | HTTP exposure verdict |
|---|---|---|---|---|---|---|---|
| 1 | `start_session` | `pace: Pace = normal`, `resume: bool = False` | `TurnView` | Creates a new `TutoringSession` **unconditionally** when `resume=False` (service.py:139-151 — no active-session guard, finding F1); resume path re-activates latest active/paused session (service.py:123-137) and appends a `SESSION_STARTED` event | `create_session`, `upsert_daily_plan`, `append_event`, `save_state`; resume: `update_session` | `RuntimeError("configuration invalid…")` (service.py:120) | **EXPOSE** -> `POST /api/v1/sessions` (new session) and `POST …/resume` |
| 2 | `stop_session` | `reason: str = "learner requested stop"` | `TurnView` (kind `ended`) | Sets status `paused`, records end reason + resume point event | `update_session`, `save_state`, `append_event` | none — info view "No active session." when none (service.py:156) | **EXPOSE** -> `POST …/stop` (idempotent) |
| 3 | `mark_theory_seen` | — | `TurnView` | Appends `theory:{unit}` to `completed_unit_ids`, moves to the unit's first exercise | `save_state` | none | **EXPOSE (ADD)** -> `POST …/theory-seen` — REQUIRED: teach units cannot advance without it (CLI: Enter key -> `mark_theory_seen`, interactive.py:138); no proposed endpoint covered it |
| 4 | `submit_response` | `response: str` | `TurnView` (next activity + evaluation) | Grades response (MCQ deterministic, else AI), engine `decide_after_attempt`, resolves next exercise, budget guard | **One transaction**: `record_interaction(attempt, evidence, assessment, state, events)` (service.py:405); `log_ai_interaction` for non-MCQ | info view "No exercise in progress." (service.py:293) | **EXPOSE (MODIFIED)** -> `POST …/answer` — API must reject stale `activity_id` (see §3/§4; service grades the *authoritative current* exercise, service.py:291) |
| 5 | `request_hint` | — | `TurnView` (hint or info) | `hints_used_current += 1`, HINT_REQUESTED/HINT_DELIVERED events | `save_state`, `append_event` x2, `record_hint_event`, `log_ai_interaction` | info views: no exercise (service.py:508); ladder exhausted (service.py:510-513) | **EXPOSE (MODIFIED)** -> `POST …/hint` — escalates ladder L1..L5, cap `max_hints + 1` |
| 6 | `reveal_solution` | — | `TurnView` (info) | Sets `pending_action = "solution_revealed"` (attempt can never count as independent afterwards) | `save_state` | info views: no exercise (service.py:537); no stored solution (service.py:543) | **EXPOSE (MODIFIED)** -> `POST …/reveal-solution` |
| 7 | `report_confidence` | `skill_id: str`, `rating: int` | `TurnView` (info) | Updates in-process confidence map + `assessment.confidence_avg`, CONFIDENCE_REPORTED event | `upsert_assessment`, `append_event` | info view if rating outside 1..5 (service.py:549); **no skill-existence check** (service.py:548-559) -> API layer must validate | **EXPOSE** -> `POST /api/v1/sessions/{id}/confidence` |
| 8 | `explain_current` | — | `TurnView` (info) | AI `explain()` call | `log_ai_interaction` | info view "Nothing to explain yet." (service.py:564) | **EXPOSE (MODIFIED)** -> `POST …/explain` |
| 9 | `session_plan` | — | `dict` (planned units, theory blocks, question counts, mastered/total, budget/remaining) | none (read-only) | none | none | **EXPOSE (read)** — inside `GET /home` and session snapshot |
| 10 | `progress_report` | — | `dict` (qualitative states per skill, daily plan) | none (read-only) | none | none | **EXPOSE** -> `GET /api/v1/learner/progress` |
| 11 | `export_last_session` | `out_dir='exports'` | `str` (file path) | **Writes a markdown file to the filesystem** (service.py:688) | reads storage | `RuntimeError("No sessions recorded yet.")` (service.py:660) | **NOT EXPOSED in V1** — filesystem side effect; CLI/AutoClaw coaching feature. Revisit as a download endpoint in Slice 1B (open question OQ-5) |
| 12 | `finish_session_if_due` | `decision: EngineDecision` | `bool` | none | none | none | **NOT EXPOSED** — internal helper; redundant with `_present_from_decision` END_SESSION handling |

Public attributes (`engine`, `ai`, `storage`, `config`, `curriculum`, `learner`, `session`) are internal
wiring — never mapped to HTTP.

### 1.3 Storage interface (what the API inherits without touching it)

`MySQLStorage` and `MemoryStorage` implement one identical interface (verified: same method set in
`persistence/repositories.py` / `persistence/memory_repositories.py`): learner, sessions, events,
attempts, evidence, assessments, state, daily plans, `record_interaction` (atomic), `ensure_exercise`
(for AI-generated items), `log_ai_interaction`, `record_hint_event`. The API layer consumes
`TutorService` only — it must not import `pymysql` or touch SQL (invariant 10).

---

## 2. TurnView inspection

### 2.1 Field-by-field audit (`TurnView`, service.py:27-39; runtime-verified)

| Field | Type | Always present? | Possible values / shapes | Internal or learner-facing? |
|---|---|---|---|---|
| `kind` | `str` | always | `theory` \| `exercise` \| `ended` \| `info` | Facing — becomes `turn.type` (`activity`/`theory`/`ended`/`notice`) |
| `decision` | `EngineDecision \| None` | exercise/theory/ended | action + `skill_id`, `unit_id`, `exercise_id`, `why: list[str]` (engine.py:15-33) | Partially facing — `step {action, why[]}`; ids feed activity context |
| `unit` | `LearningUnit \| None` | theory turns | id/title/goal/unit_type/theory text | Facing for theory turns (theory text is meant to be read); ids facing as context |
| `exercise` | `Exercise \| None` | exercise turns | full domain object — **payload contains grading secrets** (see §2.3) | Facing ONLY through the filtered activity envelope (§5) |
| `generated` | `bool` | exercise turns | True for AI-generated remediation items (`rem_*` ids) | Facing — activity flag `generated` |
| `evaluation` | `EvaluationResult \| None` | after submit | 15 fields — see §6 mapping | Mixed: `correct/score/feedback/confidence_signal/identified_misconception` facing; `missing_skill/recommended_action/ai_confidence/provider/model/prompt_version/raw` internal |
| `hint` | `HintResult \| None` | after hint request | level 1..5, kind, text, `is_solution` (always False by schema), provider/model/prompt_version | `level/kind/text` facing; provider fields internal |
| `confidence_request` | `str \| None` | exercise turns of high-complexity skills, once per session | skill_id | Facing — drives the rating prompt |
| `remaining_minutes` | `float \| None` | active sessions | 0..budget | Facing — `session.remaining_minutes` |
| `daily` | `DailyPlan \| None` | active sessions | target_units/completed_units/status | Facing — `session.daily` |
| `extra` | `dict` | varies | **5 observed keys** (§2.2) | Per-key decision (§6) — never passed through generically |

### 2.2 `extra` key census (review amendment RC-4 — every key gets a contract decision)

All construction sites enumerated in `service.py` + `interactive.py` (grep, this inspection):

| Key | Produced where | Shape | Public-contract decision |
|---|---|---|---|
| `message` | every `info`/`ended` view (service.py:125, 156, 168, 247, 293, 508-513, 537-545, 549-573) | str | **TRANSFORM** -> `notice.text` (plus `notice.severity` derived from turn kind); messages are learner-facing already |
| `unit_position` | `_exercise_view` (service.py:218-225) | tuple `(k, n)` | **EXPOSE** -> `activity.position = {"index": k, "of": n}` |
| `ai_degraded` | `submit_response` (service.py:419) | str (fallback reason) | **TRANSFORM** -> `result.answered_by = "builtin-fallback"` + `notice.text` (no raw provider error strings to the learner) |
| `revealed` | `reveal_solution` (service.py:545) | bool | **EXPOSE** -> `notice.kind = "solution_revealed"` |
| `units_completed` | `_end_naturally` (service.py:247-248) | int | **EXPOSE** -> `session.units_completed` on ended turns |

No generic untyped `extra` object is exposed. Any future key must be added to this table first.

### 2.3 `Exercise.payload` exposure map (grading secrets — runtime census over all 75 exercises)

| interaction_type | payload keys present (count) | PUBLIC to frontend | SECRET (never sent) |
|---|---|---|---|
| `mcq` (50) | `choices`, `answer_id`, `explanation` | `choices[{id,text}]` | `answer_id`, `explanation` |
| `code_tracing` / `output_prediction` (10) | `code`, `expected_output` | `code` | `expected_output` |
| `free_form` (6) | `reference_points`, `min_points` | — (prompt only) | `reference_points`, `min_points` |
| `code_writing` (4) | `function_name`, `starter`, `tests`, `solution` | `function_name`, `starter` | `tests`, `solution` |
| `complexity_question` (4) | `acceptable`, `kind` | `kind` | `acceptable` |
| `graph_construction` (1) | `nodes`, `expected_edges` | `nodes` | `expected_edges` |

Also internal to the envelope, never exposed: `hint_ladder` (contains all hint texts incl. L5 partial
solution — hints are delivered one at a time by `request_hint`), `difficulty`, `required_capabilities`,
`ordering`, `requires_ai`, `prompt_version`.

### 2.4 Stable public JSON proposal

The frontend contract is defined by JSON shapes in §4-§5, independent of Python class layout
(invariant 6). Python renames (e.g., `Exercise` -> activity) or internal refactors must not break it;
the API layer owns the mapping (§6).

---

## 3. Proposed endpoints — classification

Verdicts are evidence-based (code citations) and requirement-based (the learner must be able to do
everything the CLI does: start/stop/resume, study theory, answer, hint, reveal, explain, rate
confidence, see progress/plan). **Endpoint count is not a success metric** — one REMOVE and one ADD
below; the final set is the smallest coherent API for the V1 learner experience.

| # | Proposed endpoint | Verdict | Evidence & reasoning |
|---|---|---|---|
| 1 | `POST /api/v1/sessions` | **KEEP** | `start_session(pace, resume=False)` (service.py:139-151). Design requirement for 1B: reject with `409 SESSION_ALREADY_ACTIVE` when an active/paused session exists — current code creates a new session unconditionally (finding F1, service.py:142); double-click would stack sessions |
| 2 | `GET /api/v1/sessions/{session_id}` | **MODIFY** | Read-only snapshot (session meta + current turn + plan). **Genuinely read-only (review R3; wording per v1.2 review):** Slice 1B MUST provide a genuinely read-only snapshot path — it may use persisted state plus deterministic engine reconstruction, **provided the implementation is verified to perform zero writes**. Do NOT reuse `start_session(resume=True)` — that path writes (service.py:127-137). Resolves former OQ-2 |
| 3 | `POST /api/v1/sessions/{session_id}/resume` | **KEEP** | `start_session(resume=True)` semantics + path-id targeting (§4.13). Target matrix (review v1.2): paused → activate (200); already active → 200 no-op; completed/abandoned → 409 `SESSION_NOT_ACTIVE`; nonexistent → 404; **another session active while the target is paused** → 409 `ANOTHER_SESSION_ACTIVE` (V1 keeps at most one active session) |
| 4 | `POST /api/v1/sessions/{session_id}/stop` | **KEEP** | `stop_session` (service.py:153-170) + path-id targeting (§4.13): stops the **identified** session, not "whatever the service currently considers active". Already paused → 200 no-op; nonexistent → 404; completed → 409 `SESSION_NOT_ACTIVE` |
| 5 | `POST …/activities/{activity_id}/answer` | **MODIFY** | `submit_response(response)` (service.py:289-426) grades the **authoritative current** exercise (service.py:291). Resolution order (§4.5, review v1.2): idempotency-key lookup **first** (replay, even if the activity has since advanced) → stale-activity check **second** (409 `STALE_ACTIVITY` with fresh payload, unseen keys only) → process |
| 6 | `POST …/activities/{activity_id}/hint` | **MODIFY** | `request_hint` (service.py:504-527): escalates ladder, capped at `max_hints + 1` -> `409 LADDER_EXHAUSTED` (service.py:510-513). Same stale validation as #5. Hints never bypass the engine — assistance level feeds evidence (mastery.py `outcome_for_attempt`) |
| 7 | `POST …/activities/{activity_id}/reveal-solution` | **MODIFY** | `reveal_solution` (service.py:530-545): sets `solution_revealed` (evidence can never be independent afterwards — mastery.py). `404 NO_SOLUTION` when the exercise stores none (service.py:543). Same stale validation |
| 8 | `POST …/activities/{activity_id}/explain` | **MODIFY** | `explain_current` (service.py:561-573) — AI operation; activity_id validated, otherwise ignored by the service. Hybrid fallback makes this near-always available (factory.py) |
| 9 | `GET /api/v1/sessions/{session_id}/why` | **REMOVE** | Redundant: every activity/theory turn already carries `step.why` (the full `EngineDecision.why` chain, engine.py:15-33); the CLI `why` command merely re-renders the same object (interactive.py:161-164). A GET would re-serve data the client already holds. Revisit only if a future async UI needs server-side recompute after disconnect |
| 10 | `POST /api/v1/sessions/{session_id}/confidence` | **KEEP (scoped)** | `report_confidence(skill_id, rating)` (service.py:548-559); body carries `skill_id` (it is skill-scoped, not activity-scoped — driven by `TurnView.confidence_request`). API layer validates rating 1..5 **and skill existence** (service has no skill check); session targeting per §4.13 |
| 11 | `GET /api/v1/learner/progress` | **KEEP** | `progress_report` (service.py:615-637): qualitative `MasteryState` per skill + evidence counts + daily plan; no numeric percentages are exposed anywhere (README §5 contract) |
| 12 | `GET /api/v1/home` | **MODIFY** | Thin read-only composition: `{daily, plan (from session_plan), progress_summary, resume {available, session_id}}`. No single service method returns it; composition only — no pedagogic logic (invariant 2) |
| ADD | `POST /api/v1/sessions/{session_id}/theory-seen` | **ADD** | `mark_theory_seen` (service.py:231-244) — without it the API cannot advance past teach-unit theory (the CLI uses Enter -> `mark_theory_seen`, interactive.py:138). Discovered from code; not in the original proposal |

**Final API set: 11 endpoints** (12 proposed − 1 removed + 1 added; count is a consequence, not a goal).

---

## 4. Public JSON schemas

Conventions: JSON only; `snake_case`; UTC ISO-8601 timestamps; ids are strings (exercise ids) or
integers (session/learner ids); every mutation response returns the **authoritative current turn as
applicable** (review R8) — the next activity/theory when the engine advances, the current activity
for hint/explain/confidence, the ended summary on session end, or a notice — so the client never
needs a follow-up GET to stay current. Unknown fields must be ignored by clients (forward compatibility).

### 4.0 Error envelope (consistent everywhere; refined from actual exceptions in §8)

```json
{
  "error": {
    "code": "STALE_ACTIVITY",
    "message": "This activity is no longer current. The fresh activity is included in `activity`.",
    "retryable": false,
    "activity": { "...": "fresh authoritative activity envelope, when applicable" }
  }
}
```

Error codes: `VALIDATION_ERROR` (400), `MALFORMED_JSON` (400), `MISSING_IDEMPOTENCY_KEY` (400),
`INVALID_PACE` (400), `INVALID_CONFIDENCE` (400), `UNKNOWN_SKILL` (400), `SESSION_NOT_FOUND` (404),
`ACTIVITY_NOT_FOUND` (404), `NO_SOLUTION` (404), `SESSION_ALREADY_ACTIVE` (409),
`NO_SESSION_TO_RESUME` (409), `SESSION_NOT_ACTIVE` (409), `SESSION_MISMATCH` (409),
`ANOTHER_SESSION_ACTIVE` (409), `STALE_ACTIVITY` (409 — unseen keys only; keyed replays take
precedence, §4.5), `LADDER_EXHAUSTED` (409), `AI_UNAVAILABLE` (503, retryable),
`STORAGE_UNAVAILABLE` (503, retryable), `INTERNAL_ERROR` (500, not retryable).
Derivation from real exceptions: §8.

### 4.1 POST /api/v1/sessions — start a new session

- Request: `{"pace": "slow" | "normal" | "fast"}` (maps to engine budgets 12/25/45 min, config.py:86)
- 201 -> turn payload (§5) for the first activity/theory + `"session": {"id": 7, "status": "active", …}`
- 400 `INVALID_PACE`; 409 `SESSION_ALREADY_ACTIVE` (1B guard, finding F1); 503 `STORAGE_UNAVAILABLE`
- Idempotent: **no** (each call creates a session — hence the 409 guard). State-changing: yes.

### 4.2 GET /api/v1/sessions/{session_id} — session snapshot

- 200 -> `{"session": {...}, "turn": {...}, "plan": {...}}` (shapes: §5, §7)
- 404 `SESSION_NOT_FOUND` (unknown id); 409 `SESSION_NOT_ACTIVE` when the id exists but is completed/abandoned
- Idempotent: yes. State-changing: **no by contract** (see §3 #2 caveat / OQ-2)

### 4.3 POST /api/v1/sessions/{session_id}/resume

- Request: `{}` (pace is kept from the paused session)
- 200 -> turn payload; 404 `SESSION_NOT_FOUND`; 409 `NO_SESSION_TO_RESUME`; 409 `SESSION_NOT_ACTIVE`
  (target session is completed/abandoned — completed sessions never resume)
- **Retry-safe semantics (review R4):** resume on a **paused** session performs the paused→active
  transition exactly once (one `SESSION_STARTED` event); resume on an **already-active** session is a
  200 idempotent no-op — the authoritative current turn is returned and **no second event and no
  session-row write** occur. Lifecycle events fire only on real transitions (see §7.3; test row 28).
  State-changing: only on a real transition.

### 4.4 POST /api/v1/sessions/{session_id}/stop

- Request: `{"reason": "string (optional, max 200 chars)"}`
- 200 -> `{"session": {"id", "status", "budget_minutes", "end_reason_code", "end_reason_detail"}, "notice": {...}}`
- 404 `SESSION_NOT_FOUND`; 409 `SESSION_NOT_ACTIVE` (target completed/abandoned)
- **Retry-safe semantics (review R5):** stop on an **active** session performs active→paused exactly
  once (one `SESSION_ENDED` event); stop on an **already-paused** session is a 200 idempotent no-op —
  the paused snapshot is returned with **no second event**. Ending reasons: closed enum, §7.4.
  State-changing: only on a real transition.

### 4.5 POST /api/v1/sessions/{session_id}/activities/{activity_id}/answer

- Request headers: `Idempotency-Key: <client-generated unique submission id>` — **required** for this
  endpoint (review v1.2; resolves the duplicate-vs-stale contradiction, former OQ-1)
- Request: `{"answer": "string"}` — MCQ letter (`a`-`d`), free text, code as a raw multi-line string
  (the CLI `END` marker is a CLI concern, not an API one), predicted output lines, big-O expression,
  edge list — per `activity.answer_format`
- **Request-resolution order (unambiguous — review v1.2):**
  1. session targeting + status validation (404/409, §4.13)
  2. **idempotency-key lookup FIRST**: if `(session_id, key)` already has a stored result → **200
     replay**: the stored `result` with `result.duplicate = true` + the **authoritative current
     turn** — regardless of whether the originally answered activity is still current; no new
     attempt, no evidence, no state change
  3. **stale-activity check SECOND** (unseen keys only): path `activity_id` != current exercise id
     → 409 `STALE_ACTIVITY` with the fresh activity payload (finding F2)
  4. process: record the attempt (carrying the key), evaluate, engine decision, advance
- **Why a key and not a response hash (review v1.2):** a hash cannot distinguish "same request
  retried" from "same answer intentionally submitted again"; the key makes retry identity explicit.
  Lost network response → retry with the SAME key → replay. Intentional new submission → NEW key →
  normal rules (and the stale-activity rule rejects it if the referenced activity is no longer
  current). Evidence semantics preserved: every stored attempt is a distinct learner performance;
  replays fabricate nothing.
- **Where the identity is persisted (storage decision — additive in Slice 1B, NO schema change in
  1A):** `attempts.idempotency_key VARCHAR(64) NULL` + unique index `(session_id, idempotency_key)`
  (migration 003, applied via the existing `db.py EXPECTED_COLUMNS` repair mechanism;
  `MemoryStorage` mirrors it as a `(session_id, key) -> attempt` map). The stored attempt already
  carries the full `evaluation` JSON (schema.sql, attempts table), so replay reads
  `attempts.evaluation` — no new table. Keys bind on successful (2xx) processing only; failed
  requests never consume a key.
- 200 (new submission) -> turn payload: `result` (evaluation) + next `activity`/`theory`/`ended` +
  `step.why`; 200 (key replay) -> stored `result` (`duplicate = true`) + authoritative current turn
- 400 missing `Idempotency-Key` (`MISSING_IDEMPOTENCY_KEY`) / `MALFORMED_JSON` / `VALIDATION_ERROR`;
  404 `ACTIVITY_NOT_FOUND` / `SESSION_NOT_FOUND`; 409 `SESSION_NOT_ACTIVE` / `SESSION_MISMATCH` /
  `STALE_ACTIVITY` (unseen keys only)
- State-changing: yes on first processing; **no** on key replay

### 4.6 POST …/hint

- Request: `{}` — 200 -> `{"hint": {"level", "kind", "text"}, "activity": {...}}` (same activity)
- 409 `LADDER_EXHAUSTED` (cap `max_hints + 1`, service.py:510-513; message points to reveal-solution);
  409 `STALE_ACTIVITY`/`SESSION_NOT_ACTIVE`; 503 `AI_UNAVAILABLE` (openai-only mode)
- Idempotent: no (each call escalates — by design). State-changing: yes (assistance evidence)

### 4.7 POST …/reveal-solution

- Request: `{}` — 200 -> `{"solution": "string", "notice": {"kind": "solution_revealed", …}, "activity": {...}}`
- 404 `NO_SOLUTION` (no stored solution/explanation, service.py:543); 409s as above
- Idempotent: yes (repeated reveals set the same state). State-changing: yes (evidence penalty forever)

### 4.8 POST …/explain

- Request: `{}` — 200 -> `{"explanation": "string (2-4 sentences, connects to current task)"}`
- 409s as above; 503 `AI_UNAVAILABLE` (openai-only). Idempotent: yes (pure read through AI; no state).
  State-changing: no (only `ai_interactions` log row)

### 4.9 POST /api/v1/sessions/{session_id}/confidence

- Request: `{"skill_id": "string", "rating": 1..5}` — 200 -> `{"recorded": true, "skill_id": "..."}`
- 400 `INVALID_CONFIDENCE` / `UNKNOWN_SKILL`; 404 `SESSION_NOT_FOUND`
- Idempotent: yes (last value wins). State-changing: yes (assessment field + event)

### 4.10 GET /api/v1/learner/progress

- 200 -> `{"daily": {"date", "target_units", "completed_units", "status"},
  "skills": [{"skill", "title", "section", "module", "state": "NOT_SEEN..INDEPENDENT",
  "evidence_count", "mastered", "boundary", "optional"}]}` (shape mirrors `progress_report`, service.py:615-637)
- Idempotent: yes. State-changing: no

### 4.11 GET /api/v1/home

- 200 -> `{"daily": {...}, "plan": {"items": [{"skill", "title", "type", "theory", "questions"}],
  "questions_total", "theory_blocks", "units", "mastered", "total_skills"},
  "progress_summary": {"mastered", "total_skills"}, "resume": {"available": true|false, "session_id", "pace",
  "remaining_minutes"}}` — composed from `session_plan()` + `progress_report()` + latest active session
- Idempotent: yes. State-changing: no

### 4.12 POST /api/v1/sessions/{session_id}/theory-seen  (ADD)

- Request: `{}` — 200 -> next turn payload (first checks of the unit, or engine-selected next step)
- 404 `SESSION_NOT_FOUND`; 409 `SESSION_NOT_ACTIVE` (no active session); 409 `STALE_ACTIVITY` (the
  current turn is not this unit's theory AND the theory is not yet marked seen — e.g., a stale client
  calls theory-seen after the unit already advanced)
- **Retry-safe semantics (review R1) — exact state transition:**
  1. *theory pending, current turn is theory* → mark `theory:{unit_id}` seen (membership-checked —
     never a duplicate list entry), emit `THEORY_VIEWED` **exactly once**, advance to the unit's first
     unchecked exercise → 200 turn payload
  2. *theory already seen* (retry after advancing, or double-submit) → **200 idempotent no-op**: the
     authoritative current turn is returned; no event, no list mutation, no re-advance
  3. *no active session* → 409
  Retry definition: N identical calls after the first produce the same authoritative current turn,
  exactly one `THEORY_VIEWED` event per (session, unit), and no duplicate `completed_unit_ids` entries.
  1B implementation note: the current code appends unconditionally (service.py:231-234) — it must
  membership-check before appending. State-changing: only on the first call
- **Unit identity (review v1.2):** the endpoint has no `unit_id` parameter **by design** — it is bound
  to the currently displayed theory turn / its already-seen state, not a generic "mark some theory
  seen" operation. The server infers the unit from the authoritative current turn
  (`state.current_unit_id`) and its `theory:{unit}` seen-state; a retry from a stale unit A after the
  session advanced to unit B therefore resolves via the no-op (already seen) or `STALE_ACTIVITY`
  (not current, not seen) rules above — the client can never mark an arbitrary unit
### 4.13 Session targeting — `{session_id}` is authoritative (review v1.2)

`TutorService` methods operate on the service's **current session context** — none of them take a
session-id parameter (verified signatures, service.py:114-573), while every HTTP path carries
`{session_id}`. Contract rule:

**The path `{session_id}` is authoritative for request targeting. The application layer must verify
that the current TutorService session matches it before invoking any session-scoped mutation
(answer, hint, reveal-solution, explain, theory-seen, confidence, stop, resume).**

Mechanics (application/API layer only — no engine change):
- storage lookup: path id does not exist → 404 `SESSION_NOT_FOUND`
- current-service-session check: `service.session.id != path_session_id` → 409 `SESSION_MISMATCH`
- status checks per endpoint (§4.2–§4.4, §4.12): completed/abandoned → 409 `SESSION_NOT_ACTIVE`
- resume with another session active while the target is paused → 409 `ANOTHER_SESSION_ACTIVE`
  (§3 #3 matrix)
- Slice 1B adds a small **additive targeting helper** (e.g., `ensure_session_target(service,
  session_id)`) implementing these checks once, shared by all session-scoped endpoints; no engine
  change, no schema change
- `confidence` is learner+skill scoped in the service (service.py:548-559) but is flow-meaningful
  only inside an active session — the same targeting rule applies

---

## 5. Activity response model

Every mutation and the session snapshot return the same **turn envelope**. The frontend determines
everything it needs from this envelope alone — no engine logic, no sequence assumptions.

### 5.1 Turn envelope

```json
{
  "turn": {
    "type": "activity",                       // activity | theory | ended | notice
    "session": {
      "id": 7, "status": "active", "pace": "normal",
      "budget_minutes": 25, "remaining_minutes": 18.5,
      "daily": {"target_units": 4, "completed_units": 1, "status": "active"},
      "units_completed": 2,                   // on ended turns
      "plan_scope": "adaptive"                // planned | adaptive (see 5.4)
    },
    "step": {
      "action": "advance",                    // EngineAction value: advance | repeat | variation |
                                              // remediation | prerequisite_revisit | reduce_difficulty |
                                              // increase_difficulty | end_session
      "why": ["skill 'vertices_edges' not yet mastered (required dims: knowledge)",
              "advance to 'vertices_edges' — unit 'u002_vertices_edges'"],
      "sequence": "adaptive"                  // per-transition label, recomputed every turn (see 5.4)
    },
    "notice": null,                           // {"kind": "...", "text": "..."} on notice turns / degraded AI
    "activity": {                             // present when turn.type == "activity"
      "id": "e003_vertices_edges_mcq1",
      "type": "mcq",                          // mcq | free_form | code_writing | code_tracing |
                                              // output_prediction | complexity_question | graph_construction
      "mode": "practice",                     // see 5.3 (diagnostic/instructional/remediation/...)
      "purpose": "Quick check on 'Vertices and edges' (practice)",
      "prompt": "Which statement best describes a graph?",
      "answer_format": "letter",              // letter | text | code | lines | big_o | edges
      "position": {"index": 1, "of": 2},      // where known (unit_position)
      "unit": {"id": "u002_vertices_edges", "title": "Vertices and edges", "goal": "..."},
      "skill": {"id": "vertices_edges", "title": "Vertices and edges"},
      "choices": [{"id": "a", "text": "A set of vertices connected by edges…"}],   // mcq only
      "code": null,                           // code_tracing/output_prediction: the snippet to trace
      "starter": null, "function_name": null, // code_writing
      "nodes": null,                          // graph_construction
      "kind": null,                           // complexity_question: "sum" | "space"
      "generated": false,                     // AI-generated remediation item (rem_* id)
      "hints": {"allowed": true, "max_level": 4},
      "available_actions": ["answer", "hint", "explain", "progress", "solution", "stop"]
    },
    "theory": null,                           // theory turns: {"unit": {...}, "text": "...",
                                              //  "checks_upcoming": 2}
    "result": null                            // after answer: {"correct": true, "score": 1.0,
                                              //  "feedback": "...", "confidence_signal": "calibrated",
                                              //  "misconception": null, "answered_by": "engine-deterministic",
                                              //  "assisted": false, "duplicate": false}
  }
}
```

Rules:
- `theory` turns require `POST …/theory-seen` to advance (the API-level "Enter" key).
- `ended` turns carry the session summary; the only legal follow-ups are `resume` or `home`.
- `result.answered_by`: `engine-deterministic` (MCQ/deterministic graders, provider "deterministic"),
  `ai` (external LLM), or `builtin-fallback` (hybrid degraded — replaces raw `ai_degraded` strings).
- `available_actions` (renamed from `allowed_actions`, review R9) is derived, not authoritative:
  `answer` only on `activity` turns; `solution` gated behind ladder exhaustion messaging
  (service.py:510-513); `stop`/`progress` always on active sessions.

### 5.2 Diagnostic vs instructional vs remediation (`mode`) — derived, not decided

| Source (code) | Contribution to `mode` |
|---|---|
| `unit.unit_type` (teach/practice/assess/apply, models.py) | base: `teach` (theory) / `practice` / `assess` / `apply` |
| `EngineAction` (engine.py) | `remediation` / `prerequisite_revisit` / `repeat` / `variation` override the base label |
| `Exercise.scope` (`problem`) | badge "application problem" — plus readiness deferral reason already in `step.why` (engine `check_readiness` message) |
| placement bypass / PRACTICED+ skip (engine `select_next`) | shows up as `step.why` ("not re-taught — evidence already at …") — no separate flag needed |

`mode` is a rendered view of engine truth; the engine stays the only authority (invariant 5).

### 5.3 Per-type input contract (`answer_format`)

| type | answer_format | expected request body | Graded by |
|---|---|---|---|
| mcq | `letter` | `{"answer": "a"}` | deterministic (`grade_mcq`, zero AI calls) |
| free_form | `text` | `{"answer": "…"}` | AI/builtin rubric |
| output_prediction, code_tracing | `lines` | `{"answer": "line1, line2"}` | deterministic normalization |
| complexity_question | `big_o` | `{"answer": "O(V+E)"}` | deterministic normalization (`O(N+M)` ≡ `O(V+E)`) |
| code_writing | `code` | `{"answer": "def …\n…\n"}` (multi-line string; the CLI `END` marker is a CLI concern, not an API one) | subprocess runner with tests + AST guard |
| graph_construction | `edges` | `{"answer": "A-B, B-C"}` | deterministic edge-set comparison |

### 5.4 Planned vs adaptive (no misleading promises)

- `GET /home` and the session snapshot carry the **planned preview** (`session_plan()`: next units in
  curriculum order bounded by the daily target, with question counts). The plan itself labels these
  items as a preview.
- Every turn carries `step.sequence`: `planned` while the engine walks the preview, `adaptive` the
  moment the engine deviates (remediation, prerequisite revisit, difficulty shifts, budget stops).
- Question counts are estimates; the API never promises a count (invariant 8; stale-activity
  semantics in §4.5).
- **`step.sequence` is a per-transition label (review R7):** it classifies how THIS step came about —
  `planned` while the engine walks the deterministic preview order, `adaptive` the moment it deviates
  (remediation, prerequisite revisit, difficulty shift, budget stop). It is recomputed from the engine
  decision on every turn, is not stored anywhere, is not sticky, and does not constrain the next step.
  The session-level `plan_scope` describes the preview as a whole; neither value promises question counts.

---

## 6. TurnView → public API mapping

`Y` = exposed, `T` = exposed after transformation, `N` = internal (never sent). "Reason" cites the
governing instruction (§9 security, RC-4) or code fact.

| TurnView / nested field | Public path | Exposed | Transformation | Reason |
|---|---|---|---|---|
| `kind` | `turn.type` | T | theory→`theory`, exercise→`activity`, ended→`ended`, info→`notice` | stable vocabulary independent of Python layout |
| `decision.action` | `step.action` | T | enum value as string | learner-facing step semantics |
| `decision.why` | `step.why` | Y | list as-is (already human-readable, engine-generated) | explainability is a V1 goal (spec 03) |
| `decision.explanation` | — | N | derived (`"\n".join(why)`) — client composes | redundant convenience |
| `decision.skill_id` / `unit_id` / `exercise_id` | `activity.skill.id` / `activity.unit.id` / `activity.id` | T | folded into context objects | ids needed for answer/hint paths |
| `unit` (theory turns) | `theory.{unit, text, checks_upcoming}` | T | unit{id,title,goal} + theory text + count of unit exercises | theory is meant to be read |
| `unit` (exercise turns) | `activity.unit` | T | {id,title,goal} | context |
| `exercise.id` | `activity.id` | Y | as-is | path identity for answer/hint |
| `exercise.interaction_type` | `activity.type` + `activity.answer_format` | T | enum → type + input contract (§5.3) | drives the input UI |
| `exercise.prompt` | `activity.prompt` | Y | as-is | the ask |
| `exercise.payload` | per-type public keys only (§2.3 map) | T | strip all SECRET keys | **payload contains grading secrets** (`answer_id`, `expected_output`, `solution`, `tests`, `acceptable`, `expected_edges`, `reference_points`) |
| `exercise.role` / `scope` | `activity.mode` badge / problem badge | T | folded into mode/badge | diagnostic vs instructional clarity |
| `exercise.difficulty`, `required_capabilities`, `ordering` | — | N | — | internal metadata |
| `exercise.hint_ladder` | — | **N** | — | contains all hint texts incl. L5 — hints are delivered one at a time |
| `exercise.max_hints` | `activity.hints.max_level` | Y | as-is (4) | ladder UI |
| `exercise.requires_ai`, `prompt_version`, `language`, `source` | — | N (`generated` flag exposed instead) | — | internal provenance; `activity.generated` is the learner-relevant part |
| `generated` | `activity.generated` | Y | as-is | transparency about AI-generated remediation |
| `evaluation.correct` / `score` | `result.correct` / `result.score` | Y | as-is | core feedback |
| `evaluation.feedback` | `result.feedback` | Y | as-is | core feedback |
| `evaluation.identified_misconception` | `result.misconception` | T | renamed | learner-relevant |
| `evaluation.confidence_signal` | `result.confidence_signal` | Y | as-is | over/underconfident flag |
| `evaluation.understood_concept`, `hint_level` | — | N | — | internal rubric detail |
| `evaluation.missing_skill`, `recommended_action` | — | N | — | engine inputs (AI advisory); leaking them would let the client predict engine moves |
| `evaluation.ai_confidence` | — | N | — | model self-report heuristic, internal safety signal |
| `evaluation.degraded` + `extra.ai_degraded` | `result.answered_by` + `notice.text` | T | `builtin-fallback` + sanitized notice (no raw provider error) | RC: learner sees fallback without internal reason strings |
| `evaluation.provider` / `model` / `prompt_version` / `raw` | — | **N** | — | raw AI internals/prompts must never cross the boundary |
| `hint.level` / `kind` / `text` | `hint.{level,kind,text}` | Y | as-is | the hint itself |
| `hint.is_solution` | — | N | schema-guaranteed False (schemas.py rejects `is_solution=true`) | solutions only via reveal endpoint |
| `hint.provider/model/prompt_version` | — | N | — | AI internals |
| `confidence_request` | `turn.confidence_request` (skill_id) + client prompt | Y | as-is | drives rating UI (once per high-complexity skill per session) |
| `remaining_minutes` | `session.remaining_minutes` | Y | rounded 0.1 | budget visibility |
| `daily` | `session.daily` | T | {target_units, completed_units, status} — drop id/learner_id/updated_at | learner-facing daily target |
| `extra.message` | `notice.text` | T | renamed | RC-4 decision |
| `extra.unit_position` | `activity.position` | T | tuple → {index, of} | RC-4 decision |
| `extra.ai_degraded` | `result.answered_by` + notice | T | sanitized | RC-4 decision |
| `extra.revealed` | `notice.kind = "solution_revealed"` | T | folded | RC-4 decision |
| `extra.units_completed` | `session.units_completed` | Y | renamed | RC-4 decision |
| `session.*` (TutoringSession) | `session.{id,status,pace,budget_minutes,remaining_minutes,end_reason}` | T | whitelist; drop `learner_id`, `last_unit_id`, raw datetimes → ISO strings | single-learner internals stay internal |
| `state` (LearnerState), `storage`, `engine`, `ai`, `config`, `learner` | — | **N** | — | internal wiring/state; resume point is server-side only |

---

## 7. Session model

### 7.1 Persistent learner state (survives restarts; MySQL / MemoryStorage)

| Artifact | Where | Notes |
|---|---|---|
| Learner identity | `users` row (`local_learner`, single-user) | no auth in V1 |
| Exact resume point | `learner_state`: current skill/unit/exercise, `pending_action`, `completed_unit_ids`, per-exercise failure counts, difficulty shift | `--resume` / `POST …/resume` restores this precisely |
| Attempts + evaluation payloads | `attempts` (incl. `max_assistance_level`, `independent_success`, provider/model/prompt_version) | raw evidence — mastery is recomputable |
| Evidence | `assessment_evidence` (typed records, assistance level, outcomes) | non-monotonic mastery source |
| Assessments | `skill_assessments` (dimension scores — analytics only) | never exposed as percentages |
| Sessions | `sessions` (status active/paused/completed, budget, end_reason) | multiple rows may exist (finding F1 — 1B guard) |
| Events | `session_events` (13 types, ordered) | audit log; `why` chains derivable |
| Daily plans | `daily_plans` (target/completed, adaptive ±1 by yesterday's rate) | |
| AI/hint logs | `ai_interactions`, `hint_events` | latency, provider, validation_ok; raw bodies only if enabled |

### 7.2 Session-scoped / process-local state (does NOT survive a process restart)

| Item | Location | Consequence for the API |
|---|---|---|
| Current `TurnView` | rebuilt from persisted state on demand | GET-snapshot caveat (§3 #2, OQ-2) |
| `_confidences` map + `_confidence_asked` set | `TutorService` instance memory | confidence ratings persist (assessment), but the ask-once-per-session marker resets on restart — a skill may be re-asked after a restart (minor, documented) |
| `_gen_counter` | instance memory | only affects generated `rem_*` exercise numbering |
| In-flight turn | none — state is persisted before every response | the API is crash-safe between calls |

### 7.3 Lifecycle & budget

```
POST /sessions -> active ──(stop/Ctrl+C/budget guard)──> paused ──(resume)──> active
                     │                                      └──(all skills mastered)──> completed
                     └────────────(natural completion)────────────────────────────────────> completed
```

- Budget: pace -> minutes {slow: 12, normal: 25, fast: 45} (config.py:86). The frontend may pick a
  **pace**; arbitrary minute values would require an engine-config change — deferred (OQ-6).
- `remaining_minutes = budget - elapsed` (service `_remaining_minutes`); below the 5-minute short window
  the engine prefers short checks and stops at natural boundaries (engine `select_next` + service budget
  guard, service.py:393-403).
- The engine decides what fits the remaining budget (invariant 3); the API never computes activities.

---

Lifecycle event rules (review R4/R5): `SESSION_STARTED` fires only on a real transition (new session
or paused→active); `SESSION_ENDED` fires only on active→paused/completed. Retried resume/stop calls
on an already-reached state are 200 no-ops with **zero** new events (see §4.3/§4.4).

### 7.4 Public session ending reasons (review R6)

`end_reason` in storage is free text; the public contract exposes a **closed enum** plus the detail:

| `end_reason_code` | Trigger (code evidence) | Detail source |
|---|---|---|
| `learner_stop` | stop command / `stop_session()` default (service.py:153) | optional client reason string |
| `interrupted` | EOF/Ctrl+C handler (interactive.py:83) | fixed text |
| `budget_exhausted` | engine END_SESSION why: "session budget exhausted" (engine `select_next`) | engine why chain |
| `short_window_stop` | stop at a natural boundary with minutes remaining (service.py:393-403) | engine why chain |
| `curriculum_complete` | all V0 skills mastered (engine "all skills complete") | engine why chain |
| `other` | anything unrecognized (fallback) | sanitized raw text |

Public shape: `session.end_reason_code` (stable enum) + `session.end_reason_detail` (engine-generated
human text, informational). Derivation is a deterministic Slice 1B mapping over the decision why chain
— no engine change.

---

## 8. Error handling

### 8.1 Application exceptions → HTTP semantics (every row cites a real raise site)

| Application source | Actual behavior | HTTP | Envelope code | Retryable | Frontend handling |
|---|---|---|---|---|---|
| Malformed request body | — (API layer) | 400 | `MALFORMED_JSON` | no | inline field error |
| `pace` not in {slow,normal,fast} / `rating` not 1..5 / unknown `skill_id` | `report_confidence` returns info view for rating (service.py:549); no skill check (service.py:548-559) — API validates | 400 | `INVALID_PACE` / `INVALID_CONFIDENCE` / `UNKNOWN_SKILL` | no | inline |
| Unknown session id in path | no such storage row | 404 | `SESSION_NOT_FOUND` | no | navigate home |
| `POST /sessions` while active/paused exists | current code stacks sessions (finding F1, service.py:142) — API/1B guard | 409 | `SESSION_ALREADY_ACTIVE` | no | inline + offer resume |
| resume with nothing to resume | info view (service.py:125) | 409 | `NO_SESSION_TO_RESUME` | no | navigate home |
| mutation (answer/hint/reveal/explain/theory-seen) with no active session | info views (service.py:293, 508, 537, 564) | 409 | `SESSION_NOT_ACTIVE` | no | navigate home |
| stale `activity_id` with an UNSEEN idempotency key (browser behind authoritative state) | service grades the current exercise regardless (service.py:291) — API layer checks idempotency replay FIRST, then compares and rejects **before** calling the service (§4.5 order) | 409 | `STALE_ACTIVITY` | no | **inline auto-recovery**: replace local activity with `error.activity` |
| path `session_id` ≠ current TutorService session (any session-scoped mutation) | service methods carry no session id (service.py:114-573) — API-layer targeting check (§4.13) | 409 | `SESSION_MISMATCH` | no | navigate to the authoritative session / home |
| resume targeting a paused session while another session is active | V1 single-active-session invariant (§3 #1 guard) | 409 | `ANOTHER_SESSION_ACTIVE` | no | modal: stop the active session first |
| hint beyond ladder cap | info view (service.py:510-513) | 409 | `LADDER_EXHAUSTED` | no | inline + reveal-solution CTA |
| reveal with no stored solution | info view (service.py:543) | 404 | `NO_SOLUTION` | no | inline |
| external AI down / invalid output, `AI_PROVIDER=openai` | `AIProviderError` propagates (openai_provider.py:45-178) | 503 | `AI_UNAVAILABLE` | yes | modal with retry |
| external AI down, `AI_PROVIDER=hybrid` | hybrid falls back to builtin, `degraded=True` (factory.py) — **never an error**; proven at baseline (`reports/ai_fallback_demo.txt`) | 200 | — (`result.answered_by = "builtin-fallback"`) | — | inline notice |
| daily external AI budget exhausted | UsageGuard message via `AIProviderError` -> hybrid fallback (usage_guard.py) | 200 | — (same as above) | — | inline notice |
| MySQL down / schema incomplete | `pymysql` errors from storage; CLI pre-checks (`_build_service`, cli.py:17-35) | 503 | `STORAGE_UNAVAILABLE` | yes | modal with retry |
| invalid configuration (`RuntimeError`, service.py:120) | raised on first use | 500 | `CONFIG_ERROR` | no | navigate home + setup instructions |
| anything unexpected | — | 500 | `INTERNAL_ERROR` | no | modal; **generic message only — no tracebacks** (logged server-side to `logs/tutor.log`) |

### 8.2 Semantics notes

- `info` TurnViews are **not errors** by themselves; the API layer pre-checks state and maps the known
  info messages to the codes above. Unknown info turns pass through as `200 {"turn": {"type": "notice"}}`
  (safe path — never fail on a graceful service answer).
- Distinguish **validation** (client fixable), **state conflicts** (client must resync — `STALE_ACTIVITY`
  always carries the fresh payload), **degradation** (AI fallback — success with notice), **backend
  unavailability** (503 retryable), and **unexpected** (500). Raw tracebacks, SQL, paths and provider
  payloads never appear (§9).

---

## 9. Security/exposure boundary

### 9.1 Never exposed to the browser (checked against the mapping in §6)

- AI API keys, DB credentials, any environment variables (`OPENAI_API_KEY`, `DB_PASSWORD`, …)
- Raw AI provider requests/responses (`EvaluationResult.raw`), prompt templates (`ai/prompts.py`),
  provider/model/prompt-version metadata
- Grading secrets inside `Exercise.payload` (§2.3 map) and the full `hint_ladder`
- SQL, storage internals, filesystem paths (`PROJECT_ROOT`, `exports/...`), stack traces (server-side log only)
- Internal engine inputs: `missing_skill`, `recommended_action`, `ai_confidence`; `LearnerState` internals
- Arbitrary server configuration beyond the public session/plan/progress data

### 9.2 CORS (local development)

- **CORS is browser-origin control, not authentication.** V1 remains a local single-user application
  with no auth (explicit scope).
- Allowed origins (proposed, final list = OQ-4): `http://localhost:5173`, `http://127.0.0.1:5173`
  (Vite dev defaults). No wildcard `*` for the actual V1 browser workflow.
- No credentials/cookies are involved; still, `Access-Control-Allow-Origin` must echo only the
  configured origins. This is **not** a production security architecture — it prevents casual cross-site
  use of a localhost tutor, nothing more.

---

## 10. Storage

- **Running application:** MySQL via `.env` (`DB_NAME=dsa_tutor_v1`), selected exactly like the CLI does
  (`_build_service`, cli.py:17-35: healthcheck + schema completeness gate -> `MySQLStorage`).
  `python -m dsa_tutor setup-db` remains the bootstrap.
- **Automated tests:** `MemoryStorage` (identical interface) + `AIConfig(provider="builtin")` — hermetic
  (conftest.py fixtures); the 4 live-MySQL tests activate with credentials.
- **The API layer is storage-agnostic**: it constructs `TutorService(storage, config)` and never imports
  `pymysql`, never issues SQL (invariant 10). Storage choice is configuration, not code.

---

## 11. Testing strategy

API tests run against `TutorService` with `MemoryStorage` (hermetic) through the HTTP adapter of
Slice 1B; `MockAITutor`/builtin provider remove network flakiness. Matrix (each row = at least one test):

| # | Area | Scenario | Expected |
|---|---|---|---|
| 1 | start | POST /sessions, fresh learner | 201; turn = theory of `graph_definition`; `step.why` non-empty |
| 2 | start | pace validation | 400 `INVALID_PACE` for "banana" |
| 3 | start | duplicate session (F1 guard) | 409 `SESSION_ALREADY_ACTIVE` (1B) |
| 4 | theory | theory-seen advances | 200; next turn = first checks of the unit |
| 5 | answer | MCQ correct | 200; `result.correct=true`; next activity; `attempt` persisted (verify via storage) |
| 6 | answer | MCQ wrong | 200; `result.correct=false`; `step.action` reflects struggle ladder (remediation) |
| 7 | answer | free-form rubric pass/fail | deterministic builtin grading; no network |
| 8 | answer | code_writing via subprocess runner | timeout/test-failure paths surface in `result.feedback` |
| 9 | answer | **stale activity** | 409 `STALE_ACTIVITY` + fresh payload; **no attempt recorded** (verify) |
| 10 | answer | **duplicate submission (idempotency key)** | same key → 200 replay: `result.duplicate=true`, exactly one attempt, exactly one evidence record, no second state advance; different key on a stale activity → 409 `STALE_ACTIVITY` (§4.5) |
| 11 | hint | escalation L1..L5 | levels increase; `record_hint_event` rows exist |
| 12 | hint | ladder exhausted | 409 `LADDER_EXHAUSTED` |
| 13 | reveal | with/without stored solution | 200 solution / 404 `NO_SOLUTION`; subsequent success never independent |
| 14 | explain | hybrid fallback | 200 with builtin text (degraded path) |
| 15 | confidence | valid / invalid / unknown skill | 200 / 400 `INVALID_CONFIDENCE` / 400 `UNKNOWN_SKILL` |
| 16 | progress | shape contract | qualitative states only; no numeric mastery percentages |
| 17 | home | composition | plan preview + daily + resume availability |
| 18 | errors | malformed JSON / unknown ids | 400 `MALFORMED_JSON` / 404 `SESSION_NOT_FOUND` |
| 19 | transitions | stop -> resume -> answer | paused state persisted; resume returns exact same exercise |
| 20 | storage | storage raises | 503 `STORAGE_UNAVAILABLE` retryable; no partial writes (transaction) |
| 21 | AI degradation | hybrid + unreachable endpoint | 200 with `answered_by="builtin-fallback"` (baseline-proven pattern) |
| 22 | AI outage | openai-only provider down | 503 `AI_UNAVAILABLE` retryable |
| 23 | CORS | preflight from allowed/disallowed origin | headers present/absent; no wildcard |
| 24 | **engine authority** | any mutation | `step.why` present and identical to the engine decision the service recorded — the API never invents or filters progression (assert via storage events) |
| 25 | secrets | any activity payload | grader-only keys absent (§2.3 map) — automated schema assertion |
| 26 | **theory-seen retry (R1)** | theory-seen called twice; and again after advancing | first call advances with exactly one `THEORY_VIEWED` event; retries are 200 no-ops returning the authoritative current turn; no duplicate `completed_unit_ids` entries; no duplicate events |
| 27 | **GET read-only (R3)** | GET /sessions/{id} | 200 turn envelope; assert **zero** new events, session row untouched, storage snapshot identical before/after (resume path never invoked) |
| 28 | **resume retry (R4)** | resume paused, then resume again while active | first: paused→active + one `SESSION_STARTED`; second: 200 no-op, zero new events, no session-row write |

---

## 12. Architectural invariants

1. **The HTTP layer is transport and projection only (rewritten — review R10).** Endpoints adapt
   `TutorService` use cases to HTTP: some 1:1, some composed (`GET /home` composes three read-only
   calls), one API-added convenience (`theory-seen`) backed by an existing use case, plus API-layer
   transport preconditions (stale-activity and lifecycle checks). The earlier "1:1 mapping" claim was
   inaccurate and is removed. The layer makes no pedagogical decisions — all learning decisions come
   from the engine via the service.
2. **TutorService remains the application/use-case boundary** — the adapter calls it; it never bypasses it to storage or AI.
3. **Learning Engine remains authoritative** — progression, prerequisites, mastery/evidence, readiness, selection, remediation stay in `domain/engine.py` (§5.2 mode is rendered, not decided).
4. **AI produces observations; it never mutates learner state** — schema-guaranteed (no state fields in AI results); low-confidence AI output is even barred from driving engine decisions (service.py:324-325).
5. **Frontend renders engine truth** — `step.why` + `mode` are rendered views; the client cannot advance, skip, or grade anything.
6. **API contract is independent of Python class layout** — §6 mapping owns every rename/transform; `raw`, internal enums and dataclass shapes never leak.
7. **No secrets cross the browser boundary** — §9.1 list; §2.3 payload map; gate G8.
8. **No universal THEORY → MCQ → PROBLEM sequence** — the envelope renders the engine's per-unit sequence (`theory` turns, `unit_position`, unit types teach/practice/assess/apply); nothing in the API hardcodes an order.
9. **V0/V1 behavior is preserved** — the API adds zero pedagogy; gate G9 proves zero non-doc changes.
10. **HTTP concerns never require engine changes** — every gap found (stale-activity guard, duplicate sessions, GET snapshot helper) is handled at the API layer or queued as a 1B additive service helper (OQ-2/OQ-3); the engine is untouched.

---

## 13. Migration consideration

V1 uses a **Python HTTP layer** because the learning engine, AI contracts, and persistence already
exist in Python and are fully tested (95-test baseline); a thin adapter delivers the Vue-frontend
architecture with the smallest possible change surface (plan §2, smallest-coherent-API principle).

Because the frontend binds **only to the JSON contract in this document** (invariant 6), a future
backend rewrite does not force a frontend rewrite: a Spring Boot service could re-implement the same
`/api/v1` contract. Honest scope note: the pedagogical engine itself is Python — replacing the Python
HTTP layer with Spring Boot in practice means porting or re-implementing the backend behind the
contract, not just a proxy swap. The contract independence is what makes that migration tractable;
no Spring Boot work is in scope now (instruction §13).

---

## 14. Open questions / decisions needed

| ID | Question | Context / recommendation |
|---|---|---|
| OQ-1 | ~~Duplicate-answer protection~~ **RESOLVED (v1.2): idempotency key** | Client `Idempotency-Key` header (required on answer); persisted as `attempts.idempotency_key` with unique `(session_id, idempotency_key)` (migration 003 in 1B); replay = stored evaluation + authoritative current turn; key lookup precedes the stale check. Full contract: §4.5 |
| OQ-2 | ~~`GET /sessions/{id}` snapshot helper~~ **RESOLVED (review R3, v1.1)** | GET is genuinely read-only: Slice 1B adds an additive `session_snapshot()` service helper (zero writes; engine untouched). The resume path is never reused for GET — see §3 #2, §4.2 |
| OQ-3 | `POST /sessions` duplicate-session guard: `409` or auto-resume? | Finding F1: no guard today. Recommendation: `409 SESSION_ALREADY_ACTIVE` + `resume` link in the error envelope (explicit beats magic) |
| OQ-4 | Final CORS origin list/ports for the Vite dev server | Proposed: localhost:5173 + 127.0.0.1:5173 |
| OQ-5 | `export_last_session` as an HTTP download (AutoClaw coaching loop) | Filesystem write today; defer to 1B behind a safe download handler, or keep CLI-only |
| OQ-6 | Arbitrary session budgets (e.g., 10/25/40 requested minutes) | Engine budgets are pace-mapped constants (config.py:86); supporting arbitrary values needs an `EngineConfig` change — deferred until a real learner need appears |
| OQ-7 | Confidence prompt timing across restarts | The ask-once marker is process-local; after a restart a skill may be re-asked (harmless). Persist the marker if it annoys |
| OQ-8 | HTTP framework + server for Slice 1B | Deliberately undecided here (invariant/framework neutrality). The contract above is framework-agnostic |

---

## Appendix A — Slice 1A gate results

Filled at delivery; see the final report for details.

| Gate | Result | Evidence |
|---|---|---|
| G1 doc exists at exact path | PASS | `docs/V1_SLICE_1_API_BOUNDARY_DESIGN.md` (49,760 bytes, 613 lines at verification) |
| G2 all 14 sections present | PASS | heading grep: 14/14 mandated sections found |
| G3 traceability complete | PASS | grep coverage over endpoints (12), envelope codes, invariants, per-key decisions, plan-slice1a-v1.0.0: 0 missing markers |
| G4 method inventory complete | PASS | 12/12 public `TutorService` methods inventoried with all six attributes; runtime-verified via `inspect.getmembers` (no other public methods exist) |
| G5 TurnView fields + extra keys decided | PASS | 11/11 fields audited; 5/5 observed `extra` keys carry explicit decisions (message->notice.text, unit_position->activity.position, ai_degraded->answered_by, revealed->notice.kind, units_completed->session.units_completed) |
| G6 all 12 proposals classified | PASS | 12/12 rows in §3 (5 KEEP, 6 MODIFY, 1 REMOVE) + 1 evidence-based ADD (`theory-seen`); count not padded |
| G7 error envelope from real exceptions | PASS | 16 codes in §4.0, each derived in §8.1 from cited raise sites / info views (service.py:120,125,156,293,508-513,537-545,549,660; openai_provider.py:45-178; usage_guard.py) |
| G8 secrets scan clean | PASS | value-pattern scan: 0 secret hits (2 `sk-` regex matches were the English words "ask-once") |
| G9 tests green + only-doc diff | PASS | `pytest tests -q`: 91 passed, 4 skipped, 0 failed (9.92s); `git diff 3fb229e` shows ONLY this document; 0 protected-path changes |
| G10 final report delivered | PASS | chat report: file created, sources inspected, findings, unresolved questions, git status, no-behavior-change confirmation |

---

## Revision history

| Version | Date | Trigger | Corrections |
|---|---|---|---|
| 1.0 | 2026-09-02 | Initial Slice 1A deliverable (gates G1–G10 pass) | — |
| 1.1 | 2026-09-02 | Consolidated review of v1.0 — ONE revision, 11 corrections (R1–R11), no implementation | R1 theory-seen retry-safe + exact transition (§4.12); R2 duplicate-answer strategy resolved from evidence semantics (§4.5, OQ-1); R3 GET genuinely read-only, resume never reused (§3, §4.2, OQ-2); R4 resume retry semantics + no duplicate lifecycle events (§4.3, §7.3); R5 stop when already paused (§4.4); R6 public ending-reason enum (§7.4); R7 step.sequence is per-transition (§5.1, §5.4); R8 "authoritative current/next turn as applicable" phrasing (§4, §5.1); R9 allowed_actions → available_actions (§5.1); R10 invariant #1 rewritten — false 1:1 claim removed (§12); R11 tests added: theory-seen retry, GET read-only, resume retry (§11 rows 26–28). Everything else unchanged. |
| 1.2 | 2026-09-02 | Consolidated review of v1.1 — ONE revision, 8 corrections (C1–C8), no implementation | C1 duplicate-vs-stale contradiction resolved: required `Idempotency-Key` + `attempts.idempotency_key` persistence design, key lookup before stale check (§4.5, OQ-1); C2 `{session_id}` targeting made authoritative + targeting helper (§4.13, §3, §8.1); C3 stale test row #10 rewritten (§11); C4 resume target matrix incl. another-session-active (§3, §4.3); C5 stop targets the identified session (§3, §4.4); C6 GET snapshot wording de-prescribed (§3 #2); C7 theory-seen unit identity explicit (§4.12); C8 `SESSION_MISMATCH`/`ANOTHER_SESSION_ACTIVE` codes added (§4.0, §8.1). Reviewer approved unchanged: step.sequence semantics, available_actions, security/exposure boundary, AI-vs-engine boundary. |

Rollback: any prior version is retrievable from git history — v1.0 at `9e397f3`, v1.1 at `4366362`
(e.g. `git checkout 4366362 -- docs/V1_SLICE_1_API_BOUNDARY_DESIGN.md`).
**Implementation:** Slice 1B delivered — the contract above is implemented by
`dsa_tutor/api/*` (FastAPI adapter) with the contract test matrix in
`tests/test_api_contract.py`; verification record in `reports/SLICE1B_VERIFICATION.md`.
Deviations from the letter of this document are listed in that record (none are contractual).
