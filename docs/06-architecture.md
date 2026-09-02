# V0.1 Architecture (revised)

```
CLI (interactive loop, rendering only)
  → Application/Session layer (service: use cases, transactions, event emission)
    → Learning Engine (deterministic: curriculum, prereqs, states, readiness, budget, decisions)
    → AI Tutor interface (5 operations) → builtin | openai-compatible | hybrid | mock
    → Repositories → MySQL
```

## Boundary rules (review RC-18)

Deterministic: curriculum, prerequisites, state transitions, session budget, activity constraints, MCQ/numeric/trace/code-vs-tests grading, persistence, final next-step decision.
AI: semantic evaluation, misconceptions, hints, explanations, controlled remediation. AI is advisory; engine is authoritative.

## Code execution (review RC-19, honest terminology)

Learner Python runs in a **subprocess with static restrictions and timeout protection**: `-I` isolated interpreter, AST import allowlist (collections only), dunder/eval/exec/open rejection, 5-second wall-clock kill, stdout/stderr capture, per-test results. **This is process isolation with static restrictions — it is NOT a security sandbox** and must not be used for hostile/untrusted code or in production multi-user settings. Local single-user V0 only.
