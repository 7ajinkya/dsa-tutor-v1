# Slice 1B Implementation Audit — live API vs frozen 1A contract (v1.2)

| | |
|---|---|
| **Document version** | 1.0 (Slice 1C planning input) |
| **Date** | 2026-09-03 |
| **Audited implementation** | commit `4c0da98` (branch `main`), `dsa_tutor/api/*` |
| **Method** | (a) live walkthrough of `python -m dsa_tutor.api --offline` — 28 scripted calls captured with real request/response payloads in `plans/V1_SLICE_1C_API_CAPTURE.json`; (b) source inspection of `dsa_tutor/api/*` and `dsa_tutor/app/service.py` (file:line citations); (c) contract test suite `tests/test_api_contract.py` (29 tests) |
| **Contract** | `docs/V1_SLICE_1_API_BOUNDARY_DESIGN.md` v1.2 (frozen, approved) |
| **Verdict** | **The implementation honors the frozen contract.** 28/28 live observations match the expected statuses and envelope semantics. No blocking discrepancies; 2 medium frontend-adaptation items, 1 optional API hardening proposal. |

**Navigation:** [1 Conformance](#1-endpoint-conformance-matrix) · [2 Session flows](#2-session-flow-conformance) · [3 Real payload notes](#3-real-payload-notes-for-the-frontend) · [4 Discrepancy log](#4-discrepancy-log) · [5 Recommendations](#5-recommendations-summary)

---

## 1. Endpoint conformance matrix

Evidence labels `C-xx` refer to `plans/V1_SLICE_1C_API_CAPTURE.json` entries.

| Endpoint | Contract § | Observed live | Verdict |
|---|---|---|---|
| `POST /api/v1/sessions` | §4.1 | `C-01`: 201, theory turn for `u001_graph_definition`, session id=1, budget 25; `C-19`: 409 `SESSION_ALREADY_ACTIVE` + `resume` link while a session exists; `C-25`: 400 `INVALID_PACE` | CONFORMANT |
| `GET /api/v1/sessions/{id}` | §4.2 | `C-14`: 200 `{session, turn, plan}` from the read-only snapshot; zero-write verified by contract test 27 | CONFORMANT |
| `POST …/resume` | §4.3 | `C-17`: 200 resumed=true (paused→active); `C-18`: 200 resumed=false no-op, zero writes; `C-20` style 404 for unknown ids | CONFORMANT |
| `POST …/stop` | §4.4 | `C-15`: 200 paused, `end_reason_code=learner_stop`; `C-16`: 200 already-paused no-op, no second event | CONFORMANT |
| `POST …/theory-seen` | §4.12 | `C-02`: 200 advance to first check; retry → 200 no-op (contract test 5); unit-identity rule verified (contract test 5 + v1.2 semantics) | CONFORMANT |
| `POST …/answer` | §4.5 | `C-03`: 200 correct, `answered_by=engine-deterministic`, advanced; `C-04`: 200 replay `duplicate=true` + current turn, no second attempt; `C-05`: 409 `STALE_ACTIVITY` with fresh turn (unseen key); `C-21`: 400 `MALFORMED_JSON`; `C-22`: 400 `MISSING_IDEMPOTENCY_KEY` | CONFORMANT |
| `POST …/hint` | §4.6 | `C-06/C-07`: 200 ladder rungs; `C-28`: 409 `LADDER_EXHAUSTED`; contract tests 11–12 | CONFORMANT |
| `POST …/reveal-solution` | §4.7 | `C-08`: 200 solution text; `C-09`: 200 answer afterwards with `assisted=true` | CONFORMANT |
| `POST …/explain` | §4.8 | `C-10`: 409 `STALE_ACTIVITY` when aimed at a non-current activity (guard working); 200 for the current activity (contract test 14) | CONFORMANT |
| `POST …/confidence` | §4.9 | `C-11`: 200; `C-23`: 400 `UNKNOWN_SKILL`; `C-24`: 400 `INVALID_CONFIDENCE` | CONFORMANT |
| `GET /api/v1/learner/progress` | §4.10 | `C-12`: 200, 38 skills, qualitative states | CONFORMANT |
| `GET /api/v1/home` | §4.11 | `C-13`: 200 daily + plan + resume availability | CONFORMANT |
| Error envelope | §4.0 | every 4xx/5xx in the capture uses `{error: {code, message, retryable, …}}` | CONFORMANT |
| CORS | §9.2 | `C-26`: preflight from allowed origin echoes ACAO; `C-27`: disallowed origin gets no ACAO header | CONFORMANT |
| Extra endpoints | — | `GET /api/docs`, `GET /api/openapi.json` (tooling; see D-3) | OUT-OF-CONTRACT (harmless) |

## 2. Session-flow conformance (observed end-to-end, `C-01` → `C-28`)

1. **Start** → theory turn; `step.why` non-empty; `available_actions` correct for theory.
2. **theory-seen** → activity `e001_graph_definition` (`answer_format=letter`), position `{index:1, of:2}`.
3. **Answer (new key)** → 200, `result.correct`, advance to `e002_vertices_edges`.
4. **Answer (same key)** → 200 replay, `duplicate=true`, current turn returned, one attempt total.
5. **Answer (new key, stale path)** → 409 `STALE_ACTIVITY`, `error.turn` = authoritative current activity.
6. **Hints** → escalating rungs; exhaustion → 409 `LADDER_EXHAUSTED`.
7. **Reveal** → solution text; subsequent answer `assisted=true`.
8. **Explain on stale activity** → 409 (guard) — explain must target the current activity.
9. **Confidence** → 200 / 400 `UNKNOWN_SKILL` / 400 `INVALID_CONFIDENCE`.
10. **Stop/Resume** → lifecycle transitions fire exactly once; retries are 200 no-ops with zero writes.
11. **Second start while session exists** → 409 with resume link (finding F1 guard implemented).
12. **Unknown ids / malformed JSON** → 404 `SESSION_NOT_FOUND` / 400 `MALFORMED_JSON`.

## 3. Real payload notes for the frontend

Verified shapes the Vue client will code against (full raw payloads in the capture file):

- `turn.type` ∈ {`activity`, `theory`, `ended`, `notice`}; `turn.session` always present on session turns.
- `turn.activity` per-type public fields observed: mcq → `choices[{id,text}]`; `code` only for
  tracing/prediction; `starter`/`function_name` only for code_writing; `nodes` only for
  graph_construction; `kind` only for complexity_question. No secret keys observed in any projection
  (contract test 25 walks all 75 exercises).
- `turn.result`: `correct`, `score`, `feedback`, `confidence_signal`, `misconception`, `answered_by`
  (`engine-deterministic` observed), `assisted`, `duplicate`.
- `turn.hint`: `level`, `kind`, `text` (escalating).
- `turn.step`: `action` (`advance` observed), `why[]` (human-readable), `sequence` (`planned`/`adaptive`).
- `session`: `id`, `status`, `pace`, `budget_minutes`, `remaining_minutes` (live decreasing),
  `end_reason_code`/`end_reason_detail`, `daily`.
- Replay responses: top-level `result` (stored evaluation, `duplicate=true`) + current turn.

## 4. Discrepancy log

Default ruling rule (per slice authorization): **the frozen contract governs; the real implementation
informs.** Severity: H/M/L/Info. Recommendation: `frontend adapts` / `API fix proposed` / `none`.

| ID | Sev | Finding (evidence) | Ruling & recommendation |
|---|---|---|---|
| D-1 | M | §4.6/§4.7/§4.8 sketches show flat top-level shapes (`{hint, activity}`, `{solution, notice, activity}`, `{explanation}`); the implementation returns the universal §5.1 envelope for hint (`turn.hint`, `turn.activity`) and explain (`explanation` top-level only for reveal's `solution`) | Ruling: §5.1/§6 envelope governs; the §4.6–§4.8 shapes were schematic. **Frontend adapts** (consume `turn.hint`/`turn.activity`; read top-level `solution`/`explanation` where implemented) |
| D-2 | L | Answer responses carry `result` both inside `turn` and at top level; replay carries top-level `result` only (current turn has no evaluation yet) | Ruling: intentional and convenient. **Frontend adapts** (read top-level `result` on answer; `turn.result` otherwise) |
| D-3 | Info | Tooling endpoints `GET /api/docs`, `GET /api/openapi.json` exist beyond the contract | None. Optional: generate the typed client from `openapi.json` during 1C implementation |
| D-4 | M | Activity-scoped calls (hint/reveal/explain/answer) against a non-current activity always 409 `STALE_ACTIVITY` — observed on explain after an advance (`C-10`) | Expected behavior (finding F2 guard). **Frontend adapts**: every action button binds to the latest turn's `activity.id`; on 409 auto-adopt `error.turn` and toast |
| D-5 | M | Reveal + answer sequences shift the authoritative activity immediately; a client holding an old turn gets 409 on further actions | Same as D-4 — **frontend adapts** (single source of truth = latest turn; no optimistic state keeping) |
| D-6 | L | `THEORY_VIEWED` fires at theory *presentation* (start/resume/advance), not at theory-seen; theory-seen retry emits nothing | Contract-conformant (v1.2 R1 semantics). **Frontend adapts** (do not key anything off theory-seen events) |
| D-7 | M | A client that guesses the first check's activity id could answer before theory-seen (the resume point already names it server-side); normal clients cannot (theory turns expose no activity id) | **API fix proposed (optional, 1B patch):** server-side theory-pending check on answer → 409 `THEORY_NOT_SEEN`. Not applied in 1C. **Frontend adapts meanwhile**: render the answer UI only on `turn.type == "activity"` |
| D-8 | L | Custom stop reasons (e.g., `"break"`) map to `end_reason_code = "other"` with detail preserved (`C-15` uses the default; contract test covers `other`) | Contract-conformant (§7.4). **Frontend adapts** (display `end_reason_detail`; enum for icons) |
| D-9 | Info | `assisted` derived server-side from the persisted attempt (`independent_success`) | Documented implementation note. **Frontend adapts** (treat as authoritative) |
| D-10 | Info | 4 live-MySQL tests + migration 003 application defer until a local MySQL 8 exists | Unchanged V0 behavior; runs with `setup-db`. No frontend impact |
| D-11 | L | `GET /sessions/{id}` on a session whose latest active/paused is a different id → 409 `SESSION_MISMATCH` (multi-paused targeting unsupported) | Contract §4.13-conformant. **Frontend adapts** (single active/paused session in V1; home resume card points at the right one) |
| D-12 | Info | Interaction types served today: `theory` + mcq, free_form, code_writing, code_tracing, output_prediction, complexity_question, graph_construction (+ AI-generated remediation items, currently mcq-shaped) | Verified against curriculum (75 exercises) and live runs. No invented types in 1C |

## 5. Recommendations summary

1. **Frontend adapts (D-1, D-2, D-4, D-5, D-6, D-8, D-9, D-11):** treat the latest turn envelope as the
   single source of truth; never keep optimistic activity state; bind all action buttons to the current
   `activity.id`; auto-adopt `error.turn` on `STALE_ACTIVITY`.
2. **API fix proposed, not applied (D-7):** optional `THEORY_NOT_SEEN` 409 hardening on answer —
   decision deferred to the reviewer; not a 1C blocker.
3. **No contract amendments required** for Slice 1C to proceed.

**Audit conclusion:** Slice 1B may be treated as the reliable backend for the Vue frontend exactly as
specified in the frozen contract, with the adaptation notes above.
