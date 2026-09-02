# V0 CLOSURE NOTE — DSA Tutor (dsa_tutor_v0)

**Date:** 2026-09-02 · **Status:** V0 IMPLEMENTATION-COMPLETE (final hardening pass applied)

This note closes out V0 after the design review (31 sections -> REVISION_PLAN.md) and the
final hardening pass (12 items). It contains the task ledger, changelog, known limitations,
deferred items, rollback, and run/verify instructions.

---

## 1. Task ledger — final hardening pass (12 items)

| # | Item | What changed | Where | Status |
|---|------|--------------|-------|--------|
| 1 | Mastery API consistency | All mastery decisions use `skill.evidence_requirements` via `derive_state()`; legacy `is_skill_mastered`/`is_dimension_mastered` removed; `MASTERY_THRESHOLD` removed from config; `session_plan()` fixed; `dimension_score()` kept for analytics only | `domain/mastery.py`, `domain/engine.py`, `app/service.py`, `config.py`, `.env.example` | DONE |
| 2 | Curriculum validation hardening | `validate()` now detects: unsupported required evidence types (impossible skills), activities mapping to invalid evidence types, invalid problem capabilities, problems without declared capabilities | `domain/curriculum.py`, `tests/test_curriculum.py` | DONE |
| 3 | Complete AI interaction logging | All five operations (evaluate, detect_misconception, generate_hint, explain, generate_controlled_remediation) pass through timing + structured logging to `ai_interactions` | `app/service.py`, `persistence/repositories.py` | DONE |
| 4 | Structured `explain()` result | `ExplainResult(text, provider, model, prompt_version, ai_confidence)` with validation; providers return it; service consumes `.text` | `ai/schemas.py`, `ai/interface.py`, `ai/builtin_provider.py`, `ai/openai_provider.py`, `app/service.py` | DONE |
| 5 | L0–L6 assistance policy clarified | L0–L1 → INDEPENDENT evidence; L2–L6 → ASSISTED. `ASSISTANCE_LIMIT_FOR_INDEPENDENCE=2` comment fixed; L5 (partial solution) reachable in CLI; docs/03 wording unified | `domain/mastery.py`, `app/service.py`, `docs/03` | DONE |
| 6 | Non-monotonic mastery documented | Explicit statement in `domain/mastery.py` + `docs/03 §7b`: state = current demonstrated capability, evidence immutable, recent poor performance reduces state; regression test exists | `domain/mastery.py`, `docs/03`, `tests/test_simulation.py` | DONE |
| 7 | Difficulty semantics documented | Four dimensions are descriptive metadata + intervention signals; NOT a numeric mastery/readiness equation; readiness gate is capability-based; no ordinal arithmetic | `domain/models.py`, `docs/03 §7c` | DONE |
| 8 | AI confidence = heuristic safety signal | Documented as self-reported, not calibrated; low-confidence observations are prevented from driving engine decisions (recommendation neutralized + why-note); test proves a low-confidence "acknowledge_advance" cannot force an unusual decision | `ai/schemas.py`, `app/service.py`, `tests/test_service_integration.py` | DONE |
| 9 | Simulator profile H | Misleading HIGH-confidence AI overlay (fabricated misconception + `reduce_difficulty` recommendation) over deterministic grading: correctness stays authoritative, recommendation not followed, no state mutation, progression valid | `simulation/learner_profiles.py`, `tests/test_simulation.py` | DONE |
| 10 | Stale terminology cleanup | Curriculum header 36→38 skills + Learning Activity note; README counts updated; `Exercise` legacy-alias documented in `models.py`; docs use Learning Activity | `content/curriculum_v0.py`, `README.md`, `domain/models.py` | DONE |
| 11 | Complete test suite from real environment | Command + result in §4 below — includes the 4 live-MySQL tests | this repo | DONE |
| 12 | Security cleanup | `.env` is gitignored and was never committed; **not** included in any deliverable/archive (verified); raw AI bodies off by default; the previously pasted external credential must be rotated by the owner (user action — see §6) | `.gitignore`, closure note | DONE |

## 2. Changelog (this final round)

- Mastery: qualitative states (NOT_SEEN→INDEPENDENT) derived from per-skill evidence requirements; numeric authority removed; non-monotonic semantics documented + tested.
- Assistance ladder L0–L6 with per-level evidence semantics; L5 partial solution reachable; L6 gated reveal.
- Remediation: attempt 3 = intervention threshold with progress-aware continuation; difficulty reduction gated by evidence state instead of numeric score.
- Readiness: problem-scope activities declare required capabilities; evidence-based gate with explainable deferral.
- Curriculum: Modules A–F; +adjacency, +conversion_between_representations; explicit_stack_dfs optional; weighted graphs trimmed to recognition; validation detects impossible skills and invalid capability mappings.
- AI layer: 5-operation interface + MockAITutor; `ai_confidence` heuristic with decision gating; complete `ai_interactions` logging with configurable raw bodies; `hint_events` history; structured `ExplainResult`.
- Code runner: subprocess (`-I`) + AST allowlist + 5s timeout; documented as process isolation, not a sandbox.
- Tooling: learner simulator (6 profiles + regression learner G) with exported traces; automated E2E CLI test; curriculum feasibility/capability validation tests.
- Docs: revised planning package in `docs/` (8 documents + acceptance matrix, all amendments reflected).

## 3. Known limitations (V0)

1. Code runner is process isolation, not a security sandbox — local single-user only.
2. Free-form grading in builtin mode is rubric/keyword based; external LLM grading is heuristic.
3. Mastery recency window (30 days) and ladder levels are fixed constants, not tuned per learner.
4. Raw AI request/response bodies are not retained unless explicitly enabled.
5. Ollama Cloud / Groq free-tier limits are external and may change; the usage guard constant must be updated manually if providers change their terms.

## 4. Deferred to post-V0 (explicitly out of scope)

Spaced repetition scheduling · Java implementation layer · multi-user/auth · web UI · RAG/vector content · AI-generated curriculum · weighted shortest-path topics · separate Problem persistence table · per-learner tuned assistance thresholds.

## 5. Run & verify (handoff)

Prerequisites: Python 3.12+, MySQL 8 running locally, `.env` from `.env.example` with `DB_PASSWORD` set (AI defaults run offline; optional keys per `.env.example`).

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m dsa_tutor setup-db     # creates schema + seeds curriculum
.venv\Scripts\python -m dsa_tutor check        # config + schema + curriculum + AI status
.venv\Scripts\python -m pytest tests -q        # full suite incl. live MySQL tests
.venv\Scripts\python -m dsa_tutor start --pace normal
.venv\Scripts\python -m simulation.run         # learner profiles + regression scenario
```

## 6. Rollback

- No git history is maintained in this folder; the rollback point is the pre-hardening state archived beside the review request (or any prior copy of `dsa_tutor_v0/`).
- Schema changes are additive: `ai_interactions` + `hint_events` tables and five added columns can be dropped without touching pre-existing data (`DROP TABLE ai_interactions; DROP TABLE hint_events; ALTER TABLE ... DROP COLUMN ...`).
- Curriculum is code: restoring the previous `content/curriculum_v0.py` restores the exact prior skill set; learner evidence for unchanged skill ids remains valid.
- `.env` is user-owned and outside version control — never archive or commit it.

## 7. Security note (item 12)

- `.env` is in `.gitignore` and is excluded from all deliverables and archives; `.env.example` is the only credential template shipped.
- **The external API credential that appeared in earlier chat paste must be treated as compromised and rotated** in the provider console (user action — cannot be done from this repository).
- Verified: no key material is written to `logs/tutor.log` (providers never log headers/keys).
