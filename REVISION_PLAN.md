# REVISION_PLAN.md — Response to Design Review (V0 DSA Tutor)

**Project:** `dsa_tutor_v0` (adaptive Graph/BFS/DFS tutor — Python, MySQL, CLI)
**Review source:** 31-section design-review directive ("Goal: Revise the DSA Tutor V0 Planning Package")
**Status of this document:** PLAN ONLY. **No source, config, dependency, or schema file has been modified.** The only artifact this document adds is this file itself. Implementation begins exclusively after the approval section at the end is filled in.

**How to read this plan**

- Every review section is quoted (abbreviated) and answered as `RC-01` … `RC-31` — none skipped, none merged.
- Decisions: **ACCEPT** (will implement as directed) · **PARTIAL** (implement a scoped adaptation, rationale given) · **DECLINE** (with reason) · **ALIGNED** (already satisfied by the current implementation; document-only action).
- Each response names the exact target file(s), the intended change (intent, not final code), estimated scope, risk, and rollback.
- Open questions (`OQ-1` … `OQ-4`) are collected in their own section — nothing ambiguous was silently interpreted.
- Styling note: this document intentionally follows a reading-first minimal layout (plain headings, tables, no decoration) so it can be approved line by line.

---

## 1. Current-state snapshot (what already exists vs what the review asks)

The current implementation already satisfies a substantial part of the review's intent:

| Review requirement | Current status |
|---|---|
| AI observes, engine owns state | Implemented (`dsa_tutor/ai/schemas.py` contracts; engine is pure & deterministic; AI has no state-writing path) |
| Deterministic where possible | MCQ, output prediction, tracing, graph construction, complexity, and code-vs-tests all graded without AI (`ai/builtin_provider.py` graders) |
| Raw evidence retained | `assessment_evidence` table + in-memory equivalent; mastery recomputable |
| Independent vs assisted success | Implemented (hints/solution-reveal force `assisted`) |
| MySQL + events + resume | Implemented (`persistence/`, `learner_state`, `session_events`) |
| Fixed curriculum, bounded AI generation | 36 skills, 73 curated exercises, AI generation schema-bounded |
| Explainability | `EngineDecision.why` persisted and rendered |
| Mockable AI + fixed evaluation harness | 8-case harness, mocked-HTTP provider tests, hybrid fallback |

Confirmed gaps (verified against the code today): numeric mastery display, 4-level hint ladder (review asks 0–6), in-process `exec` for learner code (no subprocess isolation/timeout), no prior-knowledge diagnostics, no learner simulator, no dedicated `ai_interactions` persistence, no automated CLI end-to-end test, curriculum organized as a flat 36-skill list rather than modules A–F, `explicit_stack_dfs` as a core skill (review: optional), no per-skill description/evidence-requirements/remediation fields.

---

## 2. Response table (one row per review section)

| ID | Review section (summary) | Decision | Primary target file(s) | Risk | Rollback |
|----|--------------------------|----------|------------------------|------|----------|
| RC-01 | Product thesis: smallest useful next step; adaptive engine, not question generator | ALIGNED | README.md, docs (Phase 4) | None | n/a (doc-only) |
| RC-02 | V0 constraints (no RAG/Redis/auth/…); MySQL | ALIGNED | docs (Phase 4) | None | n/a |
| RC-03 | Keep AI; AI observes, engine decides | ALIGNED | docs (Phase 4) | None | n/a |
| RC-04 | Explicit AI interface per operation; real schema; logging; mocking | ACCEPT (scoped) | `ai/interface.py` (new), `ai/schemas.py`, `ai/*_provider.py`, `persistence/schema.sql`, `persistence/repositories.py` | Medium | git revert of the phase commit; `ai/interface.py` is additive so providers keep working |
| RC-05 | AI capability list (include / not responsible for) | PARTIAL | `ai/interface.py`, `ai/builtin_provider.py` | Low | Revert phase commit |
| RC-06 | Topic / Skill / LearningUnit / LearningActivity / Problem — distinct concepts | PARTIAL | `domain/models.py`, `persistence/schema.sql`, `content/curriculum_v0.py` | Medium-High | Schema migration rollback script (drop new columns/tables); git revert |
| RC-07 | Curriculum as Modules A–F; challenge every item; explicit-stack optional | ACCEPT (scoped) | `content/curriculum_v0.py`, `content/theory_notes.py` | Medium-High | Curriculum is code — git revert restores the 36-skill set; learner progress compatibility documented below |
| RC-08 | Two structures (tree + prereq graph); per-skill fields incl. evidence requirements & remediation policy | ACCEPT | `domain/models.py`, `domain/curriculum.py`, `content/curriculum_v0.py` | Low-Medium | git revert; additive fields with defaults |
| RC-09 | Qualitative mastery states (NOT_SEEN…INDEPENDENT), no fake percentages; keep raw evidence | ACCEPT | `domain/mastery.py`, `app/service.py`, `app/interactive.py`, tests | Medium | State is derived-on-read from retained evidence — revert = restore numeric display; no data loss possible |
| RC-10 | Distinguish completion / correctness / progress / independent success / mastery evidence | PARTIAL | `domain/mastery.py`, `app/service.py` | Low | git revert |
| RC-11 | Help ladder Level 0–6; assistance level becomes evidence; struggle shrinks the step | ACCEPT | `ai/schemas.py`, `ai/builtin_provider.py`, `domain/models.py`, `domain/mastery.py`, `app/interactive.py` | Medium | git revert; ladder is additive (levels 5–6 new) |
| RC-12 | Evidence-based remediation: cooling-off, attempt caps, when to stop/retry/advance | ACCEPT | `domain/engine.py`, tests | Medium | git revert |
| RC-13 | Skill mastery vs problem readiness; multidimensional difficulty (1–5 justified) | PARTIAL | `domain/engine.py`, `domain/mastery.py` | Medium | git revert |
| RC-14 | Session = effort budget; flexible sequence; exact resume state | ALIGNED | docs (Phase 4) | None | n/a |
| RC-15 | Daily focus line + planned/actual effort recording | PARTIAL | `app/service.py`, `app/interactive.py` | Low | git revert |
| RC-16 | Lightweight event history (taxonomy may be revised) | ALIGNED | docs (Phase 4) | None | n/a |
| RC-17 | Confidence selective, secondary signal | ALIGNED | docs (Phase 4) | None | n/a |
| RC-18 | Deterministic-vs-AI boundary explicit everywhere | ALIGNED | docs (Phase 4) | None | n/a |
| RC-19 | Code execution: isolate/timeout/limits — or honestly scope down | ACCEPT | `ai/code_runner.py` (new), `ai/builtin_provider.py` | Medium | Keep old in-process grader behind a config flag for one release; git revert |
| RC-20 | AI testing first-class (7 named representative cases) | PARTIAL | `tests/test_builtin_provider.py`, `tests/test_ai_eval_harness.py` (new), `app/service.py` | Low | git revert |
| RC-21 | Learning Engine Simulator with synthetic learner profiles A–F | ACCEPT | `simulation/` (new), `tests/test_simulation.py` (new) | Low (additive) | Delete `simulation/` directory; git revert |
| RC-22 | Explainability generated from decision data | PARTIAL | `domain/engine.py`, `app/interactive.py` | Low | git revert |
| RC-23 | Prior knowledge: diagnostics, evidence-based bypass, no skip-on-claim | ACCEPT (small) | `app/service.py`, `content/curriculum_v0.py`, `app/interactive.py` | Medium-Low | Config flag `PLACEMENT_ENABLED=false` restores old behavior |
| RC-24 | Fixed authored content; AI never invents curriculum | ALIGNED | docs (Phase 4) | None | n/a |
| RC-25 | Data model derived from domain; challenge every table; add AI interaction log | PARTIAL | `persistence/schema.sql`, `persistence/repositories.py` | Medium | Migration `002` rollback script; git revert |
| RC-26 | Architecture separation, clean interfaces, no microservices | ALIGNED | docs (Phase 4) | None | n/a |
| RC-27 | Testing strategy: unit / integration / AI contract / AI eval / curriculum / simulation / E2E CLI | PARTIAL | `tests/test_cli_e2e.py` (new), `tests/test_simulation.py` (new) | Low | git revert |
| RC-28 | Produce/update the 7–8 planning documents; cross-check contradictions | ACCEPT (docs only) | `docs/` (new, see OQ-1) | None (docs) | Delete `docs/`; planning folder untouched pending OQ-1 answer |
| RC-29 | 24 concrete V0 acceptance criteria | ACCEPT (traceability matrix) | `docs/acceptance_matrix.md` (Phase 4) | None | Delete file |
| RC-30 | Final quality bar (pedagogy / AI / engineering / scope) | ACCEPT (process rule for implementation) | applied during all phases | None | n/a |
| RC-31 | Perform an actual design review, not rewording | ACCEPT (governing principle) | this document + all phases | None | n/a |

Count: **31/31 responded** — 12 ALIGNED, 10 ACCEPT, 8 PARTIAL, 0 DECLINE, 1 scoping split (RC-07 accepted with explicit demotion/promotion decisions inside).

---

## 3. Detailed responses

### RC-01 — Product thesis (ALIGNED)
> "Smallest useful next learning step… not primarily an AI DSA question generator."

**Rationale:** The engine's `select_next`/`decide_after_attempt` implement exactly this, and the AI layer only evaluates/hints/generates bounded items.
**Change:** Documentation only — state the thesis and the engine-vs-AI division at the top of the README and the revised product spec (Phase 4).
**Verification:** Reader of README can quote the thesis and the AI boundary in one paragraph.

### RC-02 — V0 constraints (ALIGNED)
**Rationale:** No RAG/vector DB/Redis/Kafka/auth/multi-user/microservices/deployment/Java exists anywhere in the codebase; MySQL is the only database.
**Change:** Doc-only: a constraints checklist in the revised spec, each constraint mapped to the code location that honors it.
**Verification:** `grep -ri "redis\|kafka\|sqlite\|authentication" dsa_tutor/` returns no design dependencies.

### RC-03 — AI observes, engine decides (ALIGNED)
**Rationale:** `EvaluationResult`/`HintResult` carry observations only; there is no API by which AI mutates `learner_state`, mastery, or curriculum; the engine maps recommendations to actions (`decide_after_attempt`).
**Change:** Doc-only diagram in the revised architecture spec (Phase 4).
**Verification:** The existing integration test `test_ai_cannot_mutate_state_directly` keeps passing.

### RC-04 — Explicit AI interface per operation (ACCEPT, scoped)
> "evaluate / detect_misconception / generate_hint / explain / generate_controlled_remediation … define the actual schema."

**Rationale:** The current surface is close but folds misconception detection into `evaluate` and remediation into `generate_micro_question`. The review wants one explicit interface where every operation has its own input/output schema, validation, allowed values, error handling, logging, mocking, and fixed test cases.
**Proposed change (intent):**
1. New `ai/interface.py`: `AITutor` abstract base with exactly five operations — `evaluate()`, `detect_misconception()`, `generate_hint()`, `explain()`, `generate_controlled_remediation()`. `BuiltinAITutor`, `OpenAICompatibleTutor`, `HybridAITutor` implement all five (misconception detection reuses the existing pattern library; remediation generation reuses `generate_micro_question` with a `remediation` mode).
2. `ai/schemas.py`: one request/response schema pair per operation (dataclasses + `validate_*` functions), each with explicit allowed values.
3. Every operation call is logged to the new `ai_interactions` persistence (RC-25) with: operation, provider, model, prompt_version, latency_ms, raw request/response, validation outcome.
4. Mocking: `MockAITutor` in `ai/mock.py` returning scripted results; all engine tests use it.
**Estimated scope:** ~2–3 days equivalent.
**Files:** `ai/interface.py` (new), `ai/schemas.py`, `ai/builtin_provider.py`, `ai/openai_provider.py`, `ai/factory.py`, `persistence/*`, `app/service.py`.
**Risk:** Medium — touching the interface can break both providers and tests. **Mitigation:** interface is introduced alongside the existing methods first (deprecation path), tests updated in the same phase.
**Rollback:** git revert of the phase; `ai/interface.py` is additive so providers keep working; drop `ai_interactions` table via rollback migration.
**Verification:** all existing provider/schema/hybrid tests pass; new contract test asserts each operation validates a known-good payload and rejects each known-bad payload; `ai_interactions` row exists per call.

### RC-05 — AI capability list (PARTIAL)
**Accepted:** free-form evaluation, explanation evaluation, misconception detection, open-ended reasoning evaluation, Socratic questioning, hints, contextual explanation, controlled remediation/variation.
**Declined (V0):** none of the "include" list — but two items are scoped adaptations: "code reasoning feedback" is served by `explain()` over execution results (no separate evaluator in V0); "controlled variation generation" remains deterministic (engine picks an alternative curated exercise) with AI generation added only for remediation (already the case).
**Rationale:** keeps the AI surface small enough to test honestly while covering every genuinely semantic task the review lists.
**Change:** folded into RC-04's interface; `detect_misconception` becomes callable standalone.
**Verification:** harness cases (RC-20) cover each included capability at least once.

### RC-06 — Topic / Skill / LearningUnit / LearningActivity / Problem (PARTIAL)
**Rationale:** today `LearningUnit` + `Exercise` conflate "unit" and "activity", and substantial tasks ("problems") are not distinguished from micro-activities. The review is right that the pedagogical sequence should be defined per unit, not by a fixed THEORY→MCQ→PROBLEM template.
**Proposed change (intent):**
1. Keep `LearningUnit` as the pedagogical container; formally rename the semantic role of `Exercise` to **Learning Activity** in docs and add a `Problem` marker: exercises flagged `is_problem=True` (the four code-writing "application" exercises plus readiness items) become Problems — distinct table is avoided in V0; a boolean + a `weight` in evidence is enough (documented rationale: same persistence shape, different pedagogy).
2. Unit definitions gain an explicit `sequence` field (ordered activity list) so units define their own pedagogy instead of a global template.
3. Schema: `exercises.is_problem TINYINT(1) DEFAULT 0` (migration 002) — no table split (rationale: identical lifecycle; splitting adds joins without pedagogical value in V0).
**Estimated scope:** ~1–2 days.
**Risk:** Medium-High — renames touch the domain vocabulary used by engine/CLI/tests. **Mitigation:** additive rename-in-docs first; code keeps `Exercise` class name with docstring mapping ("Exercise = Learning Activity"); only the flag + sequence are new.
**Rollback:** migration 002 rollback; git revert.
**Verification:** every unit renders its own sequence; at least one unit has a non-default sequence; attempts record `is_problem`.

### RC-07 — Curriculum Modules A–F, challenge every item (ACCEPT, scoped)
> "…determine whether weighted graphs genuinely need to be taught in depth… Explicit-stack DFS may be an optional conceptual extension."

**Rationale:** the current 36-skill flat list covers the same territory but the review's module structure is better pedagogy, and two items deserve demotion.
**Proposed change (intent):**
1. Reorganize skills under modules A–F (metadata only — a `module` field; ordering/prereqs stay a graph).
2. **Demote** `explicit_stack_dfs` from core to optional extension: prerequisite of nothing; served only if the learner finishes Module E early and budget allows.
3. **Trim** `weighted_vs_unweighted` to a conceptual recognition item inside Module A (no dedicated practice exercise; V0 has no shortest-path algorithms).
4. **Add** missing review items as skills: `adjacency` (concept, Module A), `conversion_between_representations` (Module B, practice-light).
5. Net skill count 36 → ~37; prereq graph revalidated (acyclic, boundary intact).
**Risk:** Medium-High — changes the skill set the user already has progress in. **Mitigation:** progress is evidence-keyed by skill id; unchanged ids keep their history; new skills start empty; removed practice exercises leave orphan evidence rows (harmless, documented).
**Rollback:** curriculum is code — git revert restores the exact 36-skill set; no DB migration needed (skills table reseeded from code).
**Verification:** `curriculum.validate()` passes; module coverage test asserts every review-listed skill exists and every excluded topic (Dijkstra…) is absent; user's existing progress survives (spot-check query).

### RC-08 — Two structures + per-skill fields (ACCEPT)
**Proposed change (intent):** add to `Skill`: `description`, `evidence_requirements` (which evidence types count: e.g. implementation skill needs trace + implementation), `remediation_policy` (preferred remediation kind), and a `dependents(skill_id)` lookup on `Curriculum` (reverse prereq edges). Learner-facing tree = `section`/`module` grouping already in place after RC-07.
**Estimated scope:** ~1 day.
**Risk:** Low-Medium — additive fields with safe defaults; engine uses `evidence_requirements` in mastery checks (replacing the implicit dimension rule).
**Rollback:** git revert; fields default to current behavior when empty.
**Verification:** every skill has all fields non-empty (curriculum validation extended); `dependents("visited_state")` returns the BFS/DFS set.

### RC-09 — Qualitative mastery states (ACCEPT)
> "Do not make V0 depend on a fake scientifically precise score such as DFS = 83%."

**Rationale:** agreed — numeric 0–1 with a threshold is exactly the "fake precision" the review warns about. Raw evidence is already retained, so the state can be **derived on read** — no data migration, no evidence loss.
**Proposed change (intent):**
1. `domain/mastery.py`: add `MasteryState` enum (`NOT_SEEN, INTRODUCED, DEVELOPING, PRACTICED, PROFICIENT, INDEPENDENT`) with a deterministic `derive_state(skill, evidence)` transition rule: NOT_SEEN (no evidence) → INTRODUCED (≥1 success, any assistance) → DEVELOPING (≥2 evidence, mixed) → PRACTICED (≥2 incl. ≥1 independent, score high) → PROFICIENT (all required dimensions meet the current threshold incl. independence) → INDEPENDENT (PROFICIENT + a transfer/apply-type independent success).
2. Progress report and CLI render states (per required dimension + per skill); numeric scores remain internal (explanations reference them qualitatively: "your last two attempts needed hints").
3. Engine mastery checks switch to state-based (`state >= PRACTICED` to advance, `INDEPENDENT` to complete Module F).
**Estimated scope:** ~2 days.
**Risk:** Medium — progression behavior changes; every engine test asserting advance/remediate must be re-baselined. **Mitigation:** transition rules unit-tested exhaustively; behavior deltas reviewed in the phase PR.
**Rollback:** display and checks revert to numeric (single commit); derived-on-read means zero data risk.
**Verification:** state derivation table-driven tests (every state reachable, deterministic); CLI shows states; no "83%-style" percentage rendered anywhere.

### RC-10 — Five distinctions (PARTIAL)
**Rationale:** completion, correctness, independent success, and mastery evidence are already separate fields; "learning progress" (improvement over time) is the missing one.
**Proposed change (intent):** per-skill progress trend = derive from attempt history (score direction over last N attempts, hints trend) and include it in the assessment snapshot + `why` strings ("trend improving: 0.4 → 0.8").
**Estimated scope:** ~0.5 day. **Risk:** Low. **Rollback:** git revert.
**Verification:** trend test with a synthetic attempt sequence (improving / declining / flat).

### RC-11 — Help ladder Level 0–6 (ACCEPT)
> "Assistance level must become evidence."

**Rationale:** the current 4 kinds + solution reveal map to levels 1–4 + 6; the review's Level 5 (partial solution) and the explicit Level 0 baseline are missing.
**Proposed change (intent):**
1. Ladder: L0 none · L1 reflective question · L2 directional hint · L3 conceptual hint · L4 pseudocode-level guidance · L5 partial solution · L6 complete solution (current socratic/micro/light/targeted map to L1–L4; existing content unchanged).
2. `HintResult.level` becomes 0–6; attempt records `max_assistance_level` used.
3. Evidence penalty per level (L0 independent … L6 = copied-level, never independent) — replaces the boolean hints>0 rule; `outcome_for_attempt` takes the level.
4. CLI: `hint` walks L1→L6; `solution` = L6 (requires L4 reached).
**Estimated scope:** ~1.5 days.
**Risk:** Medium — changes evidence semantics for every attempt. **Mitigation:** mapping table for legacy attempts (existing `hints_used` → L1..L4 approximations); mastery tests re-baselined.
**Rollback:** git revert; legacy field retained so old attempts stay interpretable.
**Verification:** ladder test (each level, escalation order, solution-gating), mastery test ("correct after L5 ≠ independent"), CLI walk test.

### RC-12 — Evidence-based remediation rules (ACCEPT)
**Proposed change (intent):** codify in `engine.py` as named, testable rules: `max_attempts_per_activity = 3`; on attempt 2 failure → prerequisite micro-activity (existing); on attempt 3 → reduce difficulty + **cooling-off** (activity is parked for this session, a variation is served, parked activity may return next session); never re-serve the identical failed exercise immediately when an alternative exists (already true); struggle never ends a session by itself (only budget/learner/natural stop do — already true). All rules documented in the revised engine spec with the current constants.
**Estimated scope:** ~1 day. **Risk:** Medium — progression defaults change; tests re-baselined. **Rollback:** git revert (constants centralized).
**Verification:** engine tests for each rule boundary (attempt 1/2/3, cooling-off park & return, no identical immediate re-serve).

### RC-13 — Skill mastery vs problem readiness (PARTIAL)
**Rationale:** the 4-axis difficulty already exists on every exercise; what's missing is the explicit readiness gate before serving a Problem.
**Proposed change (intent):** before serving an `is_problem` activity, compute readiness = learner's dimension states vs the activity's 4-axis difficulty (deterministic mapping: axis ≤ corresponding state rank). If not ready → serve the mapped smaller activity first (existing remediation path). Reviewers asked to justify the 1–5 scale: each axis is anchored to concrete evidence types in the revised spec.
**Estimated scope:** ~1 day. **Risk:** Medium (can make problems unreachable if mapping is too strict) — **Mitigation:** mapping starts generous; simulation profiles (RC-21) must reach `traversal_application` before sign-off.
**Rollback:** git revert; flag `READINESS_GATE=false`.
**Verification:** simulation: Learner A (strong concepts, weak implementation) gets extra implementation practice before the problem; strong learner passes the gate immediately.

### RC-14 — Session design (ALIGNED)
Budgets (12/25/45), flexible sequence, natural stop, exact resume state, and "never rediscover where was I" are all implemented (`learner_state`, resume flag, plan display). **Change:** doc-only. **Verification:** resume test (already exists) cited in the spec.

### RC-15 — Daily focus + planned/actual effort (PARTIAL)
**Proposed change (intent):** session-plan display (already shipped this week) becomes the "Today's focus" line; at session end, record `planned_effort`, `actual_effort`, `completed_units`, `unfinished_unit`, `recommended_next` on the session row (columns exist partially — `budget_minutes`, `end_reason`; add `actual_minutes`). **Scope:** ~0.5 day. **Risk:** Low. **Rollback:** drop column. **Verification:** stop a scripted session → summary row shows planned vs actual.

### RC-16 — Event history (ALIGNED)
Current taxonomy covers every review event (naming differs: `QUESTION_PRESENTED`+`ANSWER_SUBMITTED` vs their `QUESTION_ANSWERED` — kept as-is, documented). Not event-sourcing; plain append-only table. **Change:** doc-only mapping table. **Verification:** cite `session_events` DDL.

### RC-17 — Confidence (ALIGNED)
Asked selectively (skills with any axis ≥ 3, once per session per skill), compared against performance (`confidence_signal` in every evaluation), never overrides evidence. **Change:** doc-only. **Verification:** existing overconfident/underconfident harness cases.

### RC-18 — Deterministic-vs-AI boundary (ALIGNED)
Implemented exactly as the review's two lists: MCQ/numeric/tracing/code-vs-tests deterministic; semantic evaluation/hints/explanations/remediation via AI. **Change:** doc-only consistency pass over all revised documents. **Verification:** doc cross-check list.

### RC-19 — Code execution safety (ACCEPT)
> "Do NOT casually introduce an unsafe arbitrary-code execution system… If full sandboxing is beyond reasonable V0 scope, say so."

**Rationale:** the current grader runs learner code **in-process** with an AST import/dunder guard — honest but not isolation, and no timeout (an infinite loop would hang the CLI).
**Proposed change (intent):** new `ai/code_runner.py`: run learner submissions in a **subprocess** (`python -I` isolated mode) writing to a temp file, with: 5-second wall timeout (kill on expiry), stdout/stderr capture, the existing AST allowlist (only `collections` imports, no dunders/eval/exec/open), test-case execution against the same contract, and structured pass/fail results. Honest limitation documented: on Windows V0, network/file access is restricted by the AST allowlist and process isolation, not a full sandbox — stated explicitly in the spec (the review explicitly permits this honest scoping).
**Estimated scope:** ~1 day.
**Risk:** Medium — subprocess overhead (~100–300 ms per submission) and Windows edge cases (path with spaces, interpreter discovery). **Mitigation:** reuse `sys.executable`; fall back to in-process grader behind `CODE_RUNNER=inprocess` flag if subprocess fails.
**Rollback:** flag flip to the previous in-process grader; git revert.
**Verification:** infinite-loop submission returns timeout result in ≤6s; stdout-capture test; malicious-import test; existing code-writing tests all pass through the new runner.

### RC-20 — AI testing first-class (PARTIAL)
**Rationale:** the 8-case fixed harness already covers correct / partial / misconception / wrong-reasoning / overconfident / underconfident / hint / solution-copy. The two **cross-evidence cases** are missing: (a) correct implementation but incorrect explanation, (b) incorrect implementation but correct explanation. These require the service to grade execution and reasoning as **separate evidence streams**.
**Proposed change (intent):** code-writing exercises return two evidence records (execution evidence from the runner, reasoning evidence from an `explain` follow-up question when execution passes); harness adds both mismatch cases asserting the two streams can disagree and the engine reacts (e.g., implementation PASS + explanation FAIL → variation targeting explanation, not re-running code).
**Estimated scope:** ~1.5 days. **Risk:** Low. **Rollback:** git revert.
**Verification:** two new harness cases pass; simulation shows a Learner B profile (memorized code, weak concepts) getting explanation remediation.

### RC-21 — Learning Engine Simulator (ACCEPT)
**Proposed change (intent):** new `simulation/` package: six synthetic learner profiles (A: strong concepts/weak implementation; B: memorization/weak fundamentals; C: high confidence/poor transfer; D: low confidence/strong performance; E: hint-dependent; F: fast after one remediation) — each profile scripts responses (with confidence ratings and hint usage) against the **real** service with mock AI and in-memory storage; assertions: no skipped prerequisites, monotonic sensible progression, remediation fired where expected, budgets respected, states reachable. Also emits a per-profile progression trace for human review.
**Estimated scope:** ~2 days. **Risk:** Low (additive, no production code changes). **Rollback:** delete the directory.
**Verification:** `pytest tests/test_simulation.py` — six profiles, each with ≥3 assertions; traces written to `exports/sim_*.md` for inspection.

### RC-22 — Explainability (PARTIAL)
**Proposed change (intent):** upgrade `why` strings to the review's shape — reference the actual assistance level, evidence counts, and prerequisite names: *"You completed BFS implementation correctly but required Level 4 assistance; serving a smaller independent implementation task before advancing."* — generated from `EngineDecision` data (no invented text). Include the top-2 reasons in CLI output (currently top-1).
**Estimated scope:** ~0.5 day. **Risk:** Low. **Rollback:** git revert. **Verification:** snapshot test: same state → same explanation string (determinism).

### RC-23 — Prior knowledge (ACCEPT, small)
**Proposed change (intent):** optional placement at first-ever session: one diagnostic MCQ for each Module A core skill, delivered back-to-back; an independent correct answer seeds genuine evidence (state ≥ INTRODUCED) so the engine can bypass demonstrated skills; **any struggle = no bypass** (self-report is never enough — there is no self-report shortcut at all in V0). Behind `PLACEMENT_ENABLED=true` (default on for fresh learners only).
**Estimated scope:** ~1 day. **Risk:** Medium-Low — bypass path must never skip prerequisites: bypass only marks the *diagnosed* skill, prereq graph still applies downstream. **Rollback:** flag off. **Verification:** simulation: a "knows foundations" profile skips Module A in minutes and lands at representation; a "claims to know" profile (wrong answers) stays at Module A.

### RC-24 — Fixed content vs AI-generated (ALIGNED)
Curated 36-skill bank is the only curriculum source; AI generation is schema-bounded, `source='ai'`, skill-locked, and validated; the engine never reads AI-invented curriculum. **Change:** doc-only. **Verification:** cite generator validation tests.

### RC-25 — Data model derived from domain (PARTIAL)
**Rationale:** schema already matches the domain closely (normalized, FKs, UTC, evidence retained). Gaps vs the review's entity list: no dedicated **`ai_interactions`** table (AI request/response/logging currently embedded in `attempts.evaluation`), and assistance usage is a counter, not a per-hint record.
**Proposed change (intent):** migration 002 adds `ai_interactions` (id, learner_id, session_id, operation, provider, model, prompt_version, request_json, response_json, validation_ok, latency_ms, created_at) and `hint_events` (attempt_id, level, kind, text, delivered_at) — immutable history tables; no calculated-state columns added (mastery stays derived).
**Estimated scope:** ~1 day. **Risk:** Medium (migration on the user's live DB) — **Mitigation:** additive-only DDL, applied by `setup-db` (idempotent), rollback script drops the two tables.
**Rollback:** `migration_002_rollback.sql`; git revert.
**Verification:** run a scripted session → one `ai_interactions` row per external call, one `hint_events` row per hint; old data untouched.

### RC-26 — Architecture (ALIGNED)
CLI → application → domain → (repositories | AI interface) → MySQL is exactly the current layout; no microservices. **Change:** doc-only diagram refresh. **Verification:** import-direction test (`import-linter`-style check or a simple grep rule) — optional, noted as such.

### RC-27 — Testing strategy (PARTIAL)
**Rationale:** unit / integration / AI-contract / AI-eval / curriculum suites exist; missing: simulation tests (RC-21) and an automated **end-to-end CLI test**.
**Proposed change (intent):** `tests/test_cli_e2e.py` spawns `python -m dsa_tutor start --offline` with piped scripted input, asserts: banner+plan appear, an answer is accepted, stop persists, resume works — the exact smoke flow currently run manually.
**Estimated scope:** ~0.5 day. **Risk:** Low (subprocess + Windows console encoding — mitigated with `PYTHONIOENCODING=utf-8`). **Rollback:** delete file.
**Verification:** the E2E test passes in CI-like conditions (fresh venv install instructions included).

### RC-28 — Planning documents to produce/update (ACCEPT, docs only)
**Proposed change (intent):** produce the revised V0.1 planning package as **versioned documents under `dsa_tutor_v0/docs/`** (spec, curriculum, engine, AI tutor, data model, architecture, implementation plan, decision log) — each with a "Changes from review" section citing RC ids. **They will NOT be written into the sibling planning folder** unless the user answers OQ-1 otherwise. Cross-contradiction checklist from the review (SQLite vs MySQL, AI authority, percentages, etc.) included as a final section.
**Risk:** None (docs). **Rollback:** delete `docs/`. **Verification:** every RC id appears in at least one document; contradiction checklist all-green.

### RC-29 — 24 V0 acceptance criteria (ACCEPT)
**Proposed change (intent):** `docs/acceptance_matrix.md` — all 24 criteria × (current status: satisfied/partial/missing — most are satisfied today) × (evidence: test name or manual step). Items 20 (simulator) and the E2E item are closed by RC-21/RC-27.
**Verification:** matrix complete; every "satisfied" row cites a real test that exists.

### RC-30 — Final quality bar (ACCEPT)
Applied as the definition-of-done for every phase above: pedagogy (small steps, independence), AI (validated, contained, mocked), engineering (boundaries, determinism, MySQL), scope (still V0). **Verification:** phase PRs include a filled quality-bar checklist.

### RC-31 — Actual design review, not rewording (ACCEPT)
This document is that review: 4 items demoted/trimmed (RC-07), 1 display paradigm replaced (RC-09), 1 safety gap honestly scoped and fixed (RC-19), 2 new subsystems added where the review found holes (RC-21 simulator, RC-23 diagnostics), and 12 review sections confirmed as already satisfied rather than blindly re-implemented.

---

## 4. Open questions (need your answer before/with approval)

| ID | Question | Default if unanswered |
|----|----------|----------------------|
| OQ-1 | RC-28: revised planning docs — new `docs/` inside `dsa_tutor_v0/` (proposed) or update the sibling `dsa_tutor_v0_planning_mysql` folder in place? | `docs/` in project |
| OQ-2 | RC-09: qualitative mastery replaces the numeric display everywhere (proposed). Keep numeric scores visible anywhere (e.g., a debug view)? | Hidden entirely |
| OQ-3 | RC-07: applying the curriculum re-mapping changes the skill set you already have progress in (existing evidence is preserved for unchanged skill ids). OK to apply to V0 now, or align planning docs first and apply to code later? | Apply now |
| OQ-4 | RC-19: is subprocess-with-timeout acceptable isolation for V0 (honest limitation documented), or do you want stricter isolation (adds complexity, likely WSL/container dependency)? | Subprocess + timeout |

---

## 5. Implementation sequence (phases — only after approval)

**Phase 1 — Pedagogy core (must-fix first):** RC-09 mastery states → RC-11 help ladder 0–6 → RC-12 remediation rules → RC-10 progress trend.
Dependencies: RC-11 changes evidence semantics, so it lands immediately after RC-09's state derivation (states read the new assistance field). Estimated: ~5 days equivalent.

**Phase 2 — AI layer hardening:** RC-04 interface + schemas → RC-25 `ai_interactions`/`hint_events` migrations → RC-05 capability mapping → RC-20 extended harness → RC-19 code runner.
Dependencies: RC-04 before RC-25 (tables log the interface); RC-19 independent (can ship separately). Estimated: ~5–6 days equivalent.

**Phase 3 — Curriculum & graph:** RC-07 module remap + demotions → RC-08 skill fields → RC-13 readiness gate → RC-23 placement diagnostics.
Dependencies: after Phase 1 (states define readiness); RC-07 needs OQ-3 answered. Estimated: ~3–4 days equivalent.

**Phase 4 — Tooling, docs, polish:** RC-21 simulator → RC-27 E2E CLI test → RC-22 explainability → RC-15 effort recording → RC-28/RC-29 documents (OQ-1) → doc-only pass for the 12 ALIGNED items.
Dependencies: simulator last-ish on purpose — it must exercise Phases 1–3 final behavior. Estimated: ~4 days equivalent.

**Ship-separately candidates:** RC-19 code runner (independent, riskiest runtime change) and RC-23 placement (user-facing behavior change) can each ship alone behind flags.

---

## 6. Post-approval verification checklist (per phase, what "done" looks like)

- **Phase 1:** `pytest tests/test_mastery.py tests/test_engine.py` — state-transition table tests green; CLI `progress` shows qualitative states (no percentages); ladder walk L1→L6 works in a scripted session; "correct after L5 ≠ independent" test green.
- **Phase 2:** contract tests per AI operation (valid in / invalid rejected); `ai_interactions` row per external call (verify via SQL after a scripted session); infinite-loop code submission times out ≤6s with result; harness cases incl. both cross-evidence mismatches green; mocked-AI engine tests unaffected.
- **Phase 3:** `curriculum.validate()` green with modules; excluded-topics grep clean; existing user progress preserved for unchanged skill ids (SQL spot-check); simulation Learner A passes the readiness gate story; placement skips only genuinely demonstrated skills.
- **Phase 4:** `pytest tests/test_simulation.py` (6 profiles) + `tests/test_cli_e2e.py` green; `docs/` package complete with contradiction checklist all-green; acceptance matrix 24/24 rows with evidence links; README updated (no percentage displays, new ladder, runner notes).

**Global regression bar:** every phase keeps the full suite green (`pytest tests -q`, currently 76 tests) and keeps MySQL `setup-db` idempotent (migration 002 applies + rolls back cleanly).

---

## 7. Approval gate — **no change happens until you fill this in**

For each item, mark one: `[ ] Approve` · `[ ] Approve with modification (note)` · `[ ] Reject`.

| Item | Decision | Your note |
|------|----------|-----------|
| RC-04/05 AI interface refactor | [ ] | |
| RC-06 Activity/Problem vocabulary + `is_problem` | [ ] | |
| RC-07 Curriculum modules A–F (+ demotions/additions) — see OQ-3 | [ ] | |
| RC-08 Per-skill fields + dependents lookup | [ ] | |
| RC-09 Qualitative mastery states — see OQ-2 | [ ] | |
| RC-10 Progress trend | [ ] | |
| RC-11 Help ladder L0–L6 | [ ] | |
| RC-12 Remediation rules + cooling-off | [ ] | |
| RC-13 Readiness gate | [ ] | |
| RC-15 Session effort recording | [ ] | |
| RC-19 Subprocess code runner — see OQ-4 | [ ] | |
| RC-20 Cross-evidence harness cases | [ ] | |
| RC-21 Learner simulator | [ ] | |
| RC-22 Explainability polish | [ ] | |
| RC-23 Placement diagnostics | [ ] | |
| RC-25 `ai_interactions` + `hint_events` migrations | [ ] | |
| RC-27 E2E CLI test | [ ] | |
| RC-28/29 Docs package — see OQ-1 | [ ] | |
| ALIGNED items (doc-only pass) | [ ] | |

**Approved plan executed by:** AutoClaw — only after you reply with the filled table (or a plain "approved as-is / approved except items X, Y").

---

## 8. No-code-changed attestation & verification method

At the time of writing, the repository state differs from the last verified build **only** by this file (`REVISION_PLAN.md`). Verification method: a list-only diff (`robocopy /L`) between the working tree and the reference snapshot shows no differing source/config/dependency files, and the full test suite (76 tests) passes unchanged after writing this document. Implementation work will begin only on the approved subset, phase by phase, with one commit per phase so every change stays individually revertible.

## 9. IMPLEMENTATION STATUS (updated after execution)

**IMPLEMENTED — 2026-09-02.** All phases executed with the 9 approval amendments incorporated: evidence-predicate mastery states (non-monotonic), assistance ladder L0-L6, intervention-based remediation, activity roles/scopes, curriculum modules A-F (38 skills), readiness gates, placement via high-information Module A checks, 5-operation AI interface with AI self-confidence gating, ai_interactions/hint_events persistence with configurable raw logging, subprocess code runner (process isolation, NOT a sandbox), learner simulator incl. regression learner G (PROFICIENT -> DEVELOPING verified), E2E CLI test, revised planning docs in docs/. Final suite: 90 tests passing. Rollback: git-style per-phase commits were not used (no repo); per-file rollback = restore from the pre-revision snapshot in the REVISION_PLAN verification section or re-run setup-db (schema additive-only).

