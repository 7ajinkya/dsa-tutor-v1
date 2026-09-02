# V0.1 Product & Learning Specification (revised)

Status: Implementation baseline V0.1 — incorporates the 2026-09 design review + approved amendments (REVISION_PLAN.md).

## 1. Thesis

The tutor continuously determines the **smallest useful next learning step** toward independent problem solving. It is an adaptive learning engine with an advisory AI layer — not an AI question generator. V0 is a controlled pedagogical experiment.

## 2. Constraints (unchanged)

One learner · Graphs · Python · CLI · MySQL · fixed authored curriculum · AI tutor (advisory) · session budgets · evidence/event history · deterministic engine. Excluded: RAG, vector DB, Redis, Kafka, scraping, auth, multi-user, microservices, calendar, deployment, Java, AI-generated curriculum, large question banks, frontend.

## 3. Domain vocabulary (distinct concepts)

- **Topic** — broad subject ("Graphs").
- **Skill** — a demonstrable capability with prerequisites, evidence requirements, and a mastery state.
- **Learning Unit** — a small pedagogical container that defines its own activity sequence.
- **Learning Activity** — one concrete interaction (explain, MCQ, predict, trace, construct, answer, write code, analyze complexity, reflect). Each activity has an explicit **role** (RECOGNITION, RECALL, EXPLANATION, TRACE, CONSTRUCTION, IMPLEMENTATION, APPLICATION, TRANSFER, REFLECTION) and a **scope** (micro | problem).
- **Problem** — any activity with `scope = problem` (substantial application). Problems are not limited to code-writing.
- **Attempt** — one graded response, preserving completion, correctness, assistance level, independent success, and mastery evidence.

## 4. Mastery (evidence predicates — amendment 1)

Qualitative states derived ONLY from evidence predicates per skill:

| State | Predicate |
|---|---|
| NOT_SEEN | no evidence |
| INTRODUCED | exactly one demonstrated success (any assistance) |
| DEVELOPING | some evidence but required evidence types incomplete/inconsistent |
| PRACTICED | every required evidence type has ≥1 success |
| PROFICIENT | every required type demonstrated independently (recent), ≥2 independent successes |
| INDEPENDENT | PROFICIENT + recent independent APPLICATION/TRANSFER evidence |

Numeric metrics exist for analytics only and are never the authority. Mastery is **non-monotonic**: PROFICIENT/INDEPENDENT require recent evidence (30-day window); stale proficiency decays and refresh practice is scheduled naturally.

## 5. Assistance ladder (amendment: levels are evidence)

L0 none · L1 reflective question · L2 directional hint · L3 conceptual hint · L4 pseudocode-level guidance · L5 partial solution · L6 complete solution (deterministic reveal, gated). Correct after L0–L1 → independent evidence; L2–L4 → assisted; L5–L6 → strongly assisted (never independent).

## 6. Sessions

Pace budgets: slow ≈12 min, normal ≈25, fast ≈45. Every session opens with a **session plan** (units, study sections, question count). End: budget exhausted, natural stopping point, or learner choice — exact state persisted for resume. Struggle triggers **intervention**, never mechanical termination (see engine spec).

## 7. Daily planning

"Today's focus" = the session plan display. Recorded: planned effort, actual effort, completed/unfinished units, recommended continuation. No calendar subsystem.
