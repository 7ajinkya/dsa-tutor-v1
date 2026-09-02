# V0.1 AI Tutor Specification (revised)

## 1. Interface (review RC-04 as amended)

Five operations, each with explicit schemas, validation, allowed values, error handling, logging, mocking, and fixed test cases:

| Operation | Input | Output |
|---|---|---|
| `evaluate` | exercise, response, context | EvaluationResult |
| `detect_misconception` | exercise, response, context | EvaluationResult (observation-focused) |
| `generate_hint` | exercise, response, hints_used, context | HintResult (level 1–5) |
| `explain` | theory, connect-back | text |
| `generate_controlled_remediation` | skill_id, context | GeneratedExercise (skill-locked, schema-validated) |

Implementations: `BuiltinAITutor` (offline, deterministic, authored rubrics — default), `OpenAICompatibleTutor` (any OpenAI-compatible API), `HybridAITutor` (external first, builtin fallback, degraded flag), `MockAITutor` (tests).

## 2. AI self-confidence (amendment 6)

Every semantic observation may carry `ai_confidence` (0–1): the **model's confidence in its own interpretation** — never the learner's correctness probability. Rules:

- `ai_confidence < 0.5` → the service neutralizes the observation (recommended_action/missing_skill are not passed to the engine); the engine decides from deterministic evidence only.
- Builtin deterministic graders report 1.0; rubric-based free-form grading reports 0.85.
- External providers are prompted to self-report; missing/invalid values are tolerated (None = unknown, no gating).

## 3. Guardrails (unchanged)

AI never mutates mastery/state/curriculum; hints can never be flagged as solutions; generated remediation is skill-locked and schema-validated; all outputs validated before use.

## 4. Logging (amendment 9)

Every AI call is persisted to `ai_interactions` (operation, provider, model, prompt_version, validation_ok, latency). **Raw request/response bodies are logged only when `AI_LOG_RAW_REQUESTS=true`** — structured observations are always retained. Retention assumption: local V0 keeps history indefinitely in MySQL; no external transmission.

## 5. Evaluation harness (review RC-20)

Fixed cases: correct · partial · misconception · wrong-reasoning · overconfident · underconfident · hint escalation without leakage · solution-copying · **cross-evidence mismatches** (correct code + wrong explanation; wrong code + correct explanation). Engine tests use `MockAITutor`; provider tests mock HTTP; harness tests run the builtin engine deterministically.
