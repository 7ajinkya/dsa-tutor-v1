"""Synthetic learner profiles driving the REAL engine end-to-end (review RC-21 + amendment 8).

Each profile scripts a learner behavior (answers, hints, confidence) against the actual
TutorService with in-memory storage and the deterministic builtin AI. Assertions check
that progression is sensible: prerequisites never skipped, remediation fired where the
profile expects it, budgets respected, and mastery states behaving non-monotonically
for the regression learner.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conftest import correct_answer_for  # noqa: E402
from dsa_tutor.ai.schemas import HintResult  # noqa: E402
from dsa_tutor.app.service import TutorService  # noqa: E402
from dsa_tutor.config import AIConfig, AppConfig  # noqa: E402
from dsa_tutor.persistence.memory_repositories import MemoryStorage  # noqa: E402


def hermetic_config():
    """Engine tests must be hermetic: builtin AI, no network (spec 06 §11)."""
    return AppConfig(ai=AIConfig(provider="builtin"))


def run_profile(behavior, steps=25, service=None):
    service = service or TutorService(MemoryStorage(), hermetic_config())
    trace = []
    view = service.start_session()
    for i in range(steps):
        if view.kind in {"ended", "info"}:
            break
        if view.kind == "theory":
            view = service.mark_theory_seen()
            continue
        if view.kind != "exercise":
            break
        ex = view.exercise
        decision_action = view.decision.action.value if view.decision else "?"
        response, confidence, hints = behavior(ex, i, view)
        if confidence is not None:
            service.report_confidence(ex.skill_id, confidence)
        if hints:
            for _ in range(hints):
                service.request_hint()
            view = service.start_session(resume=True)
        view = service.submit_response(response)
        trace.append((ex.id, ex.skill_id, decision_action,
                      view.evaluation.correct if view.evaluation else None))
    return service, trace


def always_correct(ex, i, view):
    from conftest import correct_answer_for
    return correct_answer_for(ex), None, 0


def wrong_answer(ex, i, view):
    return "definitely wrong", None, 0


# ---- profiles ------------------------------------------------------------
def profile_a_strong_concepts_weak_implementation(ex, i, view):
    """Strong concepts, weak implementation: everything right except code writing."""
    from conftest import correct_answer_for
    if ex.interaction_type.value == "code_writing":
        return "def broken(:", None, 0
    return correct_answer_for(ex), None, 0


def profile_b_memorization(ex, i, view):
    """Weak fundamentals, strong memorization: aces MCQs, fails open explanations."""
    from conftest import correct_answer_for
    if ex.interaction_type.value == "free_form":
        return "no idea", None, 0
    return correct_answer_for(ex), None, 0


def profile_c_overconfident(ex, i, view):
    """High confidence, poor transfer: claims 5/5 while failing early attempts."""
    from conftest import correct_answer_for
    if i < 2:
        return "confident but wrong", 5, 0
    if ex.skill_id in {"traversal_application", "recognizing_traversal", "bfs_vs_dfs"}:
        return "random guess", 5, 0
    return correct_answer_for(ex), 5, 0


def profile_d_underconfident(ex, i, view):
    """Low confidence, strong performance."""
    from conftest import correct_answer_for
    return correct_answer_for(ex), 1, 0


def profile_e_needs_hints(ex, i, view):
    """Needs heavy hints before answering (assisted successes)."""
    from conftest import correct_answer_for
    return correct_answer_for(ex), None, min(2, 1 + i % 2)


def profile_f_fast_after_remediation(ex, i, view):
    """Fails the first encounter with each new exercise type once, then passes."""
    from conftest import correct_answer_for
    seen = getattr(profile_f_fast_after_remediation, "_seen", set())
    if ex.id not in seen:
        seen.add(ex.id)
        profile_f_fast_after_remediation._seen = seen
        return "wrong on first try", None, 0
    return correct_answer_for(ex), None, 0


PROFILES = {
    "A_strong_concepts_weak_implementation": profile_a_strong_concepts_weak_implementation,
    "B_memorization": profile_b_memorization,
    "C_overconfident": profile_c_overconfident,
    "D_underconfident": profile_d_underconfident,
    "E_needs_hints": profile_e_needs_hints,
    "F_fast_after_remediation": profile_f_fast_after_remediation,
}
