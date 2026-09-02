# V0.1 Data Model (revised)

MySQL, InnoDB, utf8mb4, UTC timestamps. Schema lives in `dsa_tutor/persistence/schema.sql`; the curriculum is code-authored and mirrored into MySQL by `setup-db` (idempotent).

## Entities (post-amendment)

users · topics · skills (+ module, description, evidence_requirements, is_optional) · skill_prerequisites · learning_units · exercises (+ role, scope, required_capabilities) · attempts (+ max_assistance_level) · assessment_evidence (+ evidence_type, assistance_level) · skill_assessments (cached analytics; authority = evidence) · sessions · session_events · daily_plans · learner_state · **ai_interactions** (structured AI observation log; raw bodies only when `AI_LOG_RAW_REQUESTS=true`) · **hint_events** (per-hint level/kind/provider history).

## Principles applied

- Derived mastery is never stored as truth — `assessment_evidence` retains raw records and states are recomputed by predicates.
- Historical records (attempts, evidence, events, ai_interactions, hint_events) are immutable; `learner_state` and `skill_assessments` are the only mutable-current-state tables.
- Indexes on learner/session query paths; FKs enforce curriculum integrity; generated AI exercises are persisted (`ensure_exercise`) so attempts satisfy FKs.
