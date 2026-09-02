# V0.1 Learning Engine Specification (revised)

## 1. Authority

The engine owns learner state, prerequisites, mastery transitions, session budgeting, and all progression decisions. AI provides schema-validated observations; a low-confidence observation (ai_confidence < 0.5) is not allowed to drive aggressive decisions — the engine then uses deterministic evidence only.

## 2. Mastery transitions (amendment 1)

Defined by explicit evidence predicates per skill (see product spec). No hidden numeric scores, no ordinal state arithmetic in transitions. Non-monotonic: PROFICIENT/INDEPENDENT require recent (≤30 days) independent successes; degradation schedules refresh practice through normal selection.

## 3. Assistance ladder (amendment: levels are evidence)

L0 none · L1 reflective · L2 directional · L3 conceptual · L4 pseudocode guidance · L5 partial solution · L6 complete solution (deterministic reveal after ladder; recorded as max_assistance_level=6). Evidence outcome mapping: L0–L1 → independent; L2–L4 → assisted; L5–L6 → strongly assisted, never independent.

## 4. Remediation & intervention (amendment 5)

- Failure 1 → remediation micro-activity (smaller reasoning step).
- Failure 2 → prerequisite-linked revisit (AI-observed missing capability mapped through the prereq graph) or variation.
- Failure 3 → **intervention threshold**: if the attempt trend is improving, continue with a variation at the same difficulty; otherwise reduce difficulty or park the activity for a smaller one. The engine never terminates an activity purely because an attempt counter hit 3 while the learner is making meaningful progress.
- The identical failed exercise is never re-served immediately when an alternative exists.
- Struggle alone never ends a session.

## 5. Problem readiness (amendment 3)

Problems (`scope=problem`) declare **required capabilities** (evidence types). Readiness = every required capability demonstrated independently (recent). Not ready → a smaller mapped activity is served first, with an explainable message: "This problem requires independent X, but your current evidence shows only guided attempts. A smaller activity is therefore selected first."

## 6. Session budget

slow ≈12 / normal ≈25 / fast ≈45 min; short-window (<5 min) → no new units, stop at natural boundaries. Exact resume state persisted (skill, unit, activity, evidence, pending action).

## 7. Explainability

Every decision carries data-derived reasons (state names, assistance levels, evidence counts, prerequisite names). Same state → same explanation (deterministic).

## 8. Prior knowledge (amendment 2)

No self-report bypass. Placement = the first Module A study checks themselves (small, high-information). An independent success seeds exactly the evidence type the activity demonstrates (MCQ → RECOGNITION). Skills whose required evidence is demonstrated reach PRACTICED and are bypassed; partial demonstrations never bypass.
