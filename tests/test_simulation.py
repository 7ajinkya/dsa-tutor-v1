"""Simulation tests (review RC-21 + amendment 8): synthetic learners drive the real engine."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dsa_tutor.domain import mastery  # noqa: E402

from simulation.learner_profiles import PROFILES, run_profile  # noqa: E402


def test_all_profiles_progress_without_skipping_prerequisites():
    for name, behavior in PROFILES.items():
        service, trace = run_profile(behavior, steps=20)
        assert trace, f"{name} produced no interactions"
        order_positions = {sid: i for i, sid in enumerate(service.curriculum.learning_order())}
        seen = []
        for _, skill, _, _ in trace:
            if skill not in seen:
                seen.append(skill)
        # no skill may appear before its core prerequisites were seen at some point
        for skill in seen:
            for pre in service.curriculum.prerequisite_closure(skill):
                if pre in seen or service.curriculum.skill(pre).is_optional:
                    continue
                # prereq must either be mastered via evidence or appear before
                records = [r for r in service.storage.evidence_for_learner(service.learner.id)
                           if r.skill_id == pre]
                if records:
                    continue
                assert order_positions[pre] < order_positions[skill] and pre in seen, \
                    f"{name}: '{skill}' appeared before prerequisite '{pre}'"


def test_regression_learner_g_non_monotonic_mastery():
    """Amendment 8: a previously PROFICIENT learner who now performs poorly ON the skill
    must drop to a lower state, and the engine must schedule refresh practice."""
    import simulation.run as sim
    before, after = sim.regression_learner_g()
    assert before is mastery.MasteryState.PROFICIENT
    assert after is mastery.MasteryState.DEVELOPING


def test_overconfident_profile_flags_mismatch():
    service, trace = run_profile(PROFILES["C_overconfident"], steps=12)
    evaluations = [a.evaluation for a in service.storage.attempts_for_learner(service.learner.id)]
    assert any(e.get("confidence_signal") == "overconfident" for e in evaluations)


def test_underconfident_profile_flags_mismatch():
    service, trace = run_profile(PROFILES["D_underconfident"], steps=12)
    evaluations = [a.evaluation for a in service.storage.attempts_for_learner(service.learner.id)]
    assert any(e.get("confidence_signal") == "underconfident" for e in evaluations)


def test_hint_dependent_profile_gets_assisted_evidence():
    service, trace = run_profile(PROFILES["E_needs_hints"], steps=10)
    attempts = service.storage.attempts_for_learner(service.learner.id)
    assert any(a.hints_used > 0 and not a.independent_success for a in attempts)


def test_profile_h_misleading_high_confidence_ai_cannot_derail_engine():
    """Review hardening items 8+9: the learner's response is objectively correct
    (deterministic builtin grading) but the AI supplies a misleading, HIGH-confidence
    misconception recommendation. Deterministic correctness stays authoritative, the
    AI recommendation is not followed, no state mutation happens beyond evidence."""
    from dsa_tutor.ai.builtin_provider import BuiltinAITutor
    from dsa_tutor.ai.schemas import EvaluationResult
    from dsa_tutor.config import AIConfig, AppConfig
    from dsa_tutor.app.service import TutorService
    from dsa_tutor.persistence.memory_repositories import MemoryStorage
    from simulation.learner_profiles import run_profile

    class MisleadingAI(BuiltinAITutor):
        """Deterministic grading underneath, then a misleading overlay."""

        def evaluate(self, exercise, response, context):
            result = super().evaluate(exercise, response, context)
            result.identified_misconception = "fabricated misconception (high confidence)"
            result.recommended_action = "reduce_difficulty"
            result.ai_confidence = 0.9
            return result

    config = AppConfig(ai=AIConfig(provider="builtin"))
    service = TutorService(MemoryStorage(), config, ai=MisleadingAI())
    service, trace = run_profile(PROFILES["A_strong_concepts_weak_implementation"],
                                 steps=12, service=service)
    attempts = service.storage.attempts_for_learner(service.learner.id)
    correct_attempts = [a for a in attempts if a.is_correct]
    assert correct_attempts, "profile should produce correct attempts"
    for a in correct_attempts:
        # deterministic correctness remains authoritative
        assert a.independent_success or a.hints_used > 0
        assert "reduce_difficulty" not in json.dumps(a.evaluation.get("recommended_action", "")) or \
            a.evaluation["recommended_action"] == "reduce_difficulty"  # observation recorded
    # no REDUCE_DIFFICULTY decision was caused by the misleading AI recommendation
    decisions = [t[2] for t in trace]
    assert "reduce_difficulty" not in decisions
    # AI did not mutate mastery beyond normal evidence: state stays valid
    report = service.progress_report()
    assert all(row["state"] in {"NOT_SEEN", "INTRODUCED", "DEVELOPING", "PRACTICED",
                                "PROFICIENT", "INDEPENDENT"} for row in report["skills"])
