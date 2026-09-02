# Slice 1B Verification Record " + EM + " HTTP API implementation

**Date:** 2026-09-02 · **Contract:** `docs/V1_SLICE_1_API_BOUNDARY_DESIGN.md` v1.2 (approved)
**Result: 120 passed, 4 skipped, 0 failed** (full suite incl. 29 new API contract tests; V0 suite unchanged)

## Contract matrix (design §11 rows -> automated tests -> results)

| # | Design §11 scenario | Test | Result |
|---|---|---|---|
| 1 | start happy path (201, theory turn, why non-empty) | test_start_returns_theory_turn_with_engine_why | PASS |
| 2 | pace validation | test_start_rejects_invalid_pace | PASS |
| 3 | duplicate-session guard (409, finding F1) | test_start_rejects_second_session_while_one_exists | PASS |
| 4 | theory-seen advances | test_theory_seen_advances_exactly_once | PASS |
| 5 | theory-seen retry no-op + exactly-once event | test_theory_seen_retry_is_idempotent_noop | PASS |
| 6 | answer MCQ correct + attempt persisted | test_answer_mcq_correct_and_idempotent_replay | PASS |
| 7 | answer MCQ wrong -> struggle ladder / generated remediation | test_answer_wrong_triggers_engine_remediation | PASS |
| 8 | code_writing via subprocess runner | covered by V0 suite (test_builtin_provider + test_cli_e2e); API transport identical | PASS (transport) |
| 9 | stale activity 409 + fresh payload, no attempt | test_answer_stale_activity_with_new_key | PASS |
| 10 | duplicate submission replay semantics | test_answer_mcq_correct_and_idempotent_replay (same key -> replay; different key -> stale 409) | PASS |
| 11 | hint escalation L1..L5 | test_hint_escalation_and_exhaustion | PASS |
| 12 | ladder exhausted 409 | test_hint_escalation_and_exhaustion | PASS |
| 13 | reveal solution / no-solution 404 | test_reveal_solution_marks_assisted (+ V0 service tests) | PASS |
| 14 | explain (AI) | test_explain_returns_builtin_text | PASS |
| 15 | confidence valid/invalid/unknown skill | test_confidence_validation_and_targeting | PASS |
| 16 | progress shape (qualitative states only) | test_progress_contract_qualitative_only | PASS |
| 17 | home composition + resume availability | test_home_composition_and_resume_availability | PASS |
| 18 | malformed JSON / validation errors | test_answer_malformed_json_and_missing_field | PASS |
| 19 | stop -> resume -> answer transitions | test_stop_pause_resume_cycle | PASS |
| 20 | storage failure -> 503 retryable, no half-writes | test_storage_failure_maps_to_503_retryable | PASS |
| 21 | AI degradation (hybrid fallback) | test_explain_hybrid_fallback_when_ai_down | PASS |
| 22 | AI outage (openai-only) 503 | handler-verified (AIProviderError -> 503 AI_UNAVAILABLE); live-path covered by V0 mocked-provider tests | PASS |
| 23 | CORS allowed/disallowed origins | test_cors_allows_configured_dev_origins_only | PASS |
| 24 | engine authority (why present, no API-invented decisions) | test_engine_authority_every_activity_turn_has_why | PASS |
| 25 | grading secrets never projected (all 75 exercises) | test_grading_secrets_never_projected | PASS |
| 26 | theory-seen retry (review R1) | test_theory_seen_retry_is_idempotent_noop | PASS |
| 27 | GET read-only zero-writes (review R3) | test_get_session_snapshot_is_zero_write | PASS |
| 28 | resume retry (review R4) | test_stop_pause_resume_cycle (no-op assertions) | PASS |
| 29 | session targeting mismatch/another-active (review v1.2) | test_another_session_active_blocks_resume + 404 loop | PASS |

## Live smoke (uvicorn --offline, real HTTP over 127.0.0.1)

- POST /sessions -> 201 theory turn (u001_graph_definition), session.id=1, active
- POST theory-seen -> activity e001_graph_definition (answer_format=letter)
- POST answer (Idempotency-Key smoke-K1) -> correct=true, answered_by=engine-deterministic, advanced to e002_vertices_edges
- POST answer retry (same key) -> 200 replay, duplicate=true, current turn e002_vertices_edges, no second attempt
- GET /sessions/1 -> 200 read-only snapshot (activity e002, remaining minutes reported)
- CORS: preflight from allowed origin echoes ACAO; disallowed origin receives no ACAO header
- GET /home -> resume.available=true, plan.units=4, mastered=1/38

## Deviations / implementation notes

1. `result.assisted` is derived server-side from the persisted attempt's `independent_success` (matches §5.1).
2. GET snapshot sets `confidence_request = null` (the ask-once marker is process-local; OQ-7 unchanged).
3. Resuming a paused session that is NOT the latest paused session -> 409 `SESSION_MISMATCH` (the service
   resumes its latest session; multi-paused-session targeting would need a service change — deferred).
4. Hint/explain routes enforce the same stale-activity guard as answer (§3 MODIFY verdicts).
5. MySQL-only behaviors (migration 003 application via `setup-db`, the 4 live-MySQL tests) verify when a
   local MySQL 8 is available; they auto-skip otherwise (unchanged V0 behavior).
6. `answer` without prior theory-seen is technically possible for a client that guesses the activity id
   (the resume point already names the first check); well-behaved clients cannot reach it because theory
   turns expose no activity id. Flagged for Slice 1C review, no change made.

## Rollback

- `git revert <slice-1b-commit>` reverts the implementation (docs/plans untouched).
- Deeper rollback: `git checkout plan-slice1a-v1.0.0 -- .` restores the approved pre-1B tree.
- No database was created/modified during this slice (MySQL absent; migration 003 ships in schema.sql +
  db.py repair mechanism and applies only when `setup-db` runs against a real MySQL).
