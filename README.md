# DSA Tutor V0 — Adaptive Learning for Graphs, BFS & DFS

> **V1 baseline note (2026-09-02).** This folder is the frozen V0 codebase copied as the V1
> starting baseline; see `V1_BASELINE_REPORT.md`. V1 isolation adjustment vs V0 (no engine/AI/CLI
> code changed): the MySQL database is now `dsa_tutor_v1` (`.env.example`, `config.py` default,
> `persistence/schema.sql`) so V1 never touches the V0 database. The sibling `../v0/` folder is
> frozen - do not modify it.

Local, single-learner adaptive DSA tutor implementing the V0 planning baseline in
`../dsa_tutor_v0_planning_mysql/`. It validates the pedagogical loop
**concept → representation → mechanism → implementation → reasoning → application**
over the Graph V0 curriculum (36 skills: foundations, representation, traversal
fundamentals, BFS, DFS, comparison & readiness).

```
python -m dsa_tutor start --pace normal
```

---

## 1. Quick start

```powershell
# 1. one-time environment setup (from this folder)
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# 2. configure
Copy-Item .env.example .env        # then edit DB_PASSWORD (your MySQL root/user password)

# 3. create the schema (auto-creates the 'dsa_tutor_v0' database if missing),
#    repair/upgrade tables, and seed the full curriculum — idempotent, safe to re-run
.venv\Scripts\python -m dsa_tutor setup-db

# 4. verify everything
.venv\Scripts\python -m dsa_tutor check

# 5. learn
.venv\Scripts\python -m dsa_tutor start --pace normal
.venv\Scripts\python -m dsa_tutor start --resume    # continue a paused session
.venv\Scripts\python -m dsa_tutor progress          # mastery report
```

**No MySQL at hand?** `--offline` runs a fully in-memory demo session (no persistence,
no resume across processes): `python -m dsa_tutor start --offline`.

---

## 2. In-session commands

| command      | effect                                                    |
|--------------|-----------------------------------------------------------|
| `hint`       | next rung of the assistance ladder L1–L5, then `solution` (L6) |
| `solution`   | L6 complete reveal after the ladder — counts as *assisted*, never independent |
| `why`        | engine explainability: why this unit/exercise was chosen   |
| `explain`    | targeted concept explanation connected to the current task |
| `progress`   | inline mastery report                                      |
| `stop`       | pause — exact state persisted, resume with `--resume`      |
| Ctrl+C / EOF | interrupts safely — session paused, state persisted        |

Outside a session:

| command             | effect                                                     |
|---------------------|------------------------------------------------------------|
| `setup-db`          | create database (if missing) + tables + seed curriculum     |
| `reset-progress`    | wipe learner progress (keeps curriculum and schema)         |
| `check`             | verify config, MySQL, schema completeness, curriculum, AI   |

Answers: MCQ → letter; code → type code, finish with a line `END`; predictions → expected
output; complexity → big-O; free-form → sentences.

---

## 3. Architecture

Dependency direction (strictly one-way, per planning doc 06 §4):

```
CLI (dsa_tutor/app/interactive.py, cli.py)
  → Application layer (dsa_tutor/app/service.py)      use cases + transaction boundaries
    → Learning engine (dsa_tutor/domain/engine.py)     DETERMINISTIC: progression, prerequisites,
      → Curriculum (domain/curriculum.py)              mastery aggregation, session budget,
      → Mastery (domain/mastery.py)                    next-step selection, explainability
    → AI Tutor (dsa_tutor/ai/*)                        SEMANTIC: evaluation, hints, misconceptions,
    → Persistence (dsa_tutor/persistence/*)            generation — never owns state
```

- **The engine never calls the AI and does no I/O.** All decisions are pure functions of
  `(learner state, curriculum, configuration, evidence)` → `EngineDecision` with human-readable
  `why` reasons (spec 03 §10).
- **The AI never mutates state.** It returns schema-validated observations
  (`EvaluationResult`, `HintResult`, `GeneratedExercise`); only the engine turns them into
  actions. Hint results can never be flagged `is_solution=true` (schema rejects it).
- **One interaction = one transaction** (`storage.record_interaction`): attempt → evaluation →
  evidence → assessment → learner state → events commit together or roll back (spec 06 §7).
- **MCQs are graded deterministically** in the service layer — zero AI calls for simple checks
  (spec 04 §7 cost controls).

## 4. The AI layer — providers

Configured via `AI_PROVIDER` in `.env`:

| provider   | behaviour                                                                 |
|------------|---------------------------------------------------------------------------|
| `builtin`  | **default.** Offline semantic engine authored by AutoClaw: per-exercise hint ladders, misconception pattern library, rubric-based free-form grading, output-trace diagnosis (reverse order / duplicates / early stop / wrong algorithm), complexity normalization (`O(N+M)` ≡ `O(V+E)`), AST-guarded code execution against test cases. Deterministic, no network, no key. |
| `openai`   | **backward-compatible external LLM path.** Any OpenAI-compatible `/chat/completions` endpoint. JSON-mode output validated by `ai/schemas.py`; retries with backoff; per-session call cap; timeout. |
| `hybrid`   | external first; on any failure/invalid output falls back to builtin and marks the result `degraded=True`. |

Switching to an external LLM later changes **one env var** — no code changes. Prompts are
versioned (`ai/prompts.py`, `PROMPT_VERSION`) and every attempt stores
`ai_provider` / `ai_model` / `prompt_version` (spec 04 §8).

## 5. Mastery model (evidence predicates — review-amended)

Mastery is **qualitative and evidence-based** — the app never shows percentages:

| State | Meaning |
|---|---|
| NOT_SEEN | no evidence |
| INTRODUCED | exactly one demonstrated success |
| DEVELOPING | some evidence, required evidence types incomplete/inconsistent |
| PRACTICED | every required evidence type demonstrated at least once |
| PROFICIENT | every required type demonstrated independently (recent), ≥2 independent successes |
| INDEPENDENT | PROFICIENT + recent independent application/transfer evidence |

Assistance is evidence: the ladder is L0 none · L1 reflective · L2 directional · L3 conceptual · L4 pseudocode-level · L5 partial solution · L6 complete solution. Only L0–L1 successes count as independent; L5–L6 can never be independent. Numeric metrics exist for analytics only and are never authoritative.

Mastery is deliberately **non-monotonic**: PROFICIENT/INDEPENDENT require recent evidence (30 days); a previously strong learner whose recent work degrades transitions down and gets refresh practice.

Struggle triggers intervention (never mechanical termination): attempt 1 → smaller remediation step; attempt 2 → prerequisite-linked revisit; attempt 3 → reassessment (continue if progressing, otherwise reduce the reasoning step / park for a variation).

Problems (`scope=problem`) declare required capabilities; the readiness gate compares them with demonstrated evidence and explains any deferral.

## 5b. What a session actually looks like (and why)

The flow per skill is **theory → understanding check → (for core skills) practice → assess**.
Foundations skills are light by design; from Graph Representation onward you get tracing,
prediction, free-form reasoning and code-writing exercises. Two intentional mechanics:

- **Two evidence pieces per skill.** Mastery requires repeated performance (planning doc 03 §6):
  one perfect answer is not proof. The second interaction is always a *different* question
  (a new angle or a harder exercise type), never the identical question twice.
- **Hints make success count — differently.** A correct answer after hints is *assisted*
  evidence: it advances learning but never counts as independent mastery (spec 01 §7).

Use `why` in-session to see the engine's full reasoning for any choice.

## 5c. The AI options - no external API keys required

The default `builtin` provider is deterministic and free: evaluation rubrics, hints and
content were authored at build time, so nothing calls out to an API. Two ways to add a
live LLM on top:

**Option A - Ollama (local, keyless).** The tutor speaks the OpenAI-compatible protocol,
so your local Ollama plugs in directly:

```
AI_PROVIDER=hybrid
AI_MODEL=qwen2.5:3b                        # fits ~8 GB RAM machines
OPENAI_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_API_KEY=ollama                      # ignored by Ollama
```

- `qwen2.5:3b` runs 100% on your machine - no account, no key, no internet after download.
- Bigger local model? `ollama pull qwen2.5:7b` (needs ~6 GB free RAM).
- **GLM - the same model family that powers AutoClaw - is already in your Ollama
  (`glm-5:cloud`)**. Run `ollama signin` once in a terminal, then set `AI_MODEL=glm-5:cloud`.
  Uses your Ollama account, no separate API key inside the app.
- `hybrid` = live LLM first, offline engine as automatic fallback; if Ollama is not running,
  start it with `ollama serve` (or just launch the Ollama app).

**Option B - the AutoClaw coaching loop (zero setup).** After a session run:

```
python -m dsa_tutor export-session
```

It writes the full session transcript (every answer, score, misconception, hint level) to
`exports/session_<id>.md`. Drop that file into a chat with AutoClaw and it reviews your
reasoning like a human tutor - the richest feedback available without any runtime API.


**Option C - free hosted APIs (recommended once you outgrow local models).** Two providers
verified as of 2026-09, both key-in-and-go with this app, no card required:

| Provider | Base URL | Model | Free tier |
|----------|----------|-------|-----------|
| **Groq** (fastest) | `https://api.groq.com/openai/v1` | `openai/gpt-oss-120b` | ~30 req/min, ~1,000 req/day |
| **Gemini** | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-2.5-flash` | ~5-15 req/min |

A tutor session makes only ~10-30 LLM calls, so either free tier covers many sessions
per day (Groq's 1,000 req/day = dozens of sessions). Keys: console.groq.com / aistudio.google.com. Limits are per-model and change over
time - trust the rate-limits page of your own console. With `AI_PROVIDER=hybrid`, hitting
a free-tier 429 falls back to the offline engine automatically - the session never breaks.
The app's own daily guard (`AI_DAILY_REQUEST_LIMIT`, default 1,000) stops external calls
before the provider's wall is hit.
For complex topics in future versions (segment trees, DP), these hosted models are the
correct tool; local 3B-class models are for offline tinkering.

The learning engine stays deterministic in every mode - the LLM evaluates and coaches, it
never touches your mastery state (spec 04 section 4).


## 6. Data model (MySQL, spec 05)

`users, topics, skills, skill_prerequisites, learning_units, exercises, attempts,
assessment_evidence, skill_assessments, sessions, session_events, daily_plans, learner_state`
— normalized, InnoDB, FKs, UTC timestamps, indexes on learner/session query paths. Raw
evidence rows are retained so mastery can be recalculated. The curriculum is encoded in
code (`dsa_tutor/content/curriculum_v0.py`, source of truth for the engine) and mirrored
into MySQL by `setup-db` for inspection and future DB-driven evolution.

## 7. Tests

```powershell
.venv\Scripts\python -m pytest tests -q
```

63 tests, all passing (4 MySQL tests auto-skip until `.env` credentials work):

| suite                        | covers                                                              |
|------------------------------|---------------------------------------------------------------------|
| `test_curriculum.py`         | 36 skills, acyclic prereq DAG, V0 boundary enforcement, advanced-topic leak check |
| `test_mastery.py`            | formula, independence rule (hints ⇒ assisted), recency, mastery gates |
| `test_engine.py`             | selection order, skipping mastered skills, struggle ladder, budget stop, explainability |
| `test_ai_schemas.py`         | structured contracts reject unknown skills/actions/solutions        |
| `test_builtin_provider.py`   | **fixed evaluation harness** (spec 04 §10): correct, partial, misconception, wrong-reasoning, over/under-confidence, hint escalation without solution leakage, solution-copy detection |
| `test_openai_provider.py`    | external provider with mocked HTTP: parsing, retries, schema violations, hybrid fallback |
| `test_service_integration.py`| full loop: theory→check→advance, assisted vs independent, events order, stop/resume, daily-plan adaptation, AI-cannot-mutate-state |
| `test_persistence_mysql.py`  | real-MySQL: attempts/events persist, restart+resume, transaction rollback on FK violation |

## 8. Assumptions & decisions (V0 build)

1. **AI = builtin AutoClaw-authored engine by default.** Your instruction: "You will be the
   AI … change the external API based system for LLMs to your direction for the time being
   with backward compatibility for external LLMs." Implemented as the provider table above:
   the semantic layer is authored at build time and runs offline; external LLMs stay fully
   supported via `AI_PROVIDER=openai|hybrid`.
2. **Deterministic grading wherever possible** (MCQs, traces, complexity, code tests);
   free-form uses rubric matching in builtin mode. This maximizes determinism (spec 03 §11).
3. **Pace budgets use window midpoints** (slow 12, normal 25, fast 45) — spec gives ranges.
4. **Curriculum source of truth is code**, mirrored to MySQL. Simplest deterministic V0;
   DB tables exist for the future swap.
5. **`v0_readiness` is the single boundary skill**; the engine cannot advance beyond it and
   the curriculum validator rejects anything depending on it.
6. **Code exercises execute locally** with an AST guard (only `collections` imports, no
   dunders/`eval`/`exec`/`open`). Local single-user tool; do not expose it to untrusted input.
7. **Confidence ratings** are collected once per important skill (complexity ≥ 3) per session
   and compared with performance to flag over/under-confidence (secondary signal only).

## 9. Known limitations & risks

- All 67 tests pass against a live MySQL 8 (including the 4 persistence tests); they
  auto-skip only when `.env` credentials are absent or wrong.
- Builtin free-form grading is keyword-rubric based: it can miss unusual phrasings. The
  fixed harness keeps its behavior observable; `hybrid` mode upgrades quality when you add
  an API key.
- Hint-ladder content covers all curated exercises; AI-generated remediation items are
  bounded to current-skill scope but only curated items are difficulty-tuned.
- Session events grow unbounded in MySQL — fine for single-learner V0.
- No authentication/multi-user (explicit V0 exclusion).

## 10. Rollback / review method

- The project is fully additive in `dsa_tutor_v0/` — nothing outside the folder was
  modified. Rollback = delete the folder (planning docs untouched).
- All engine decisions are explainable at runtime (`why` command) and replayable from
  persisted `attempts` + `assessment_evidence` + `session_events`; to audit a session:
  `SELECT * FROM session_events WHERE session_id=<id> ORDER BY seq;`
- Configuration is hot-editable in `.env`; `python -m dsa_tutor check` validates it.
- Schema changes: add a numbered migration file in `dsa_tutor/persistence/` and re-run
  `setup-db` (idempotent DDL).

## 11. Natural next steps (beyond V0)

Spaced repetition hooks (`assessment_evidence` already timestamps outcomes) · Java
implementation layer (skills are language-independent; exercises carry a `language`
attribute) · external problem integration · multi-user + auth · real LLM prompt-caching.
