# V0.1 Implementation Plan & Acceptance Criteria (revised)

## Phases (executed per approved REVISION_PLAN.md)

1. **Pedagogy core** — evidence-predicate mastery states, assistance ladder L0–L6 as evidence, remediation-as-intervention, progress trend.
2. **AI layer hardening** — 5-operation interface with schemas, AI self-confidence gating, `ai_interactions`/`hint_events` persistence, configurable raw logging, subprocess code runner.
3. **Curriculum & graph** — modules A–F, new skills (adjacency, conversion), optional explicit-stack DFS, per-skill evidence requirements, activity roles/scopes, readiness gate, placement via high-information diagnostics.
4. **Tooling & docs** — learner simulator (6 profiles + regression learner G), E2E CLI test, explainability polish, session effort recording, this document set.

## Acceptance matrix (review RC-29, 24 criteria)

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Start a Graph session | done | `cli start`, E2E test |
| 2 | Know learner's current skill state | done | `learner_state`, resume test |
| 3 | Inspect prerequisite relationships | done | `curriculum.prerequisites`, validate test |
| 4 | Select appropriate next activity | done | engine tests |
| 5 | Multiple activity types | done | 75 exercises, 9 interaction types |
| 6 | Deterministic evaluation | done | local MCQ/trace/code graders |
| 7 | Semantic responses to AI Tutor | done | service evaluate path |
| 8 | Validated structured AI output | done | schema tests |
| 9 | AI cannot mutate state | done | integration test |
| 10 | Engine makes final decision | done | `decide_after_attempt` tests |
| 11 | Assistance level recorded | done | `max_assistance_level`, hint_events |
| 12 | Independent vs assisted | done | mastery/integration tests |
| 13 | Skill evidence persisted | done | assessment_evidence |
| 14 | Mastery derived from evidence | done | derive_state (predicates) |
| 15 | Remediation targets prerequisite | done | engine test |
| 16 | Budgets respected | done | engine/service tests |
| 17 | Stop/resume exact state | done | restart tests (memory + MySQL) |
| 18 | Events persisted | done | session_events |
| 19 | Explainable decisions | done | decision.why + `why` command |
| 20 | Synthetic profiles exercise logic | done (Phase 4) | simulation tests |
| 21 | Mock AI in engine tests | done | MockAITutor + conftest |
| 22 | MySQL end-to-end | done | live persistence tests |
| 23 | Curriculum inspected & validated | done | validation tests |
| 24 | Fundamentals → BFS/DFS → independent application | done | progression integration test |
