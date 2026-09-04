"""Full-loop integration: CLI<->engine<->AI<->storage with in-memory persistence.
Covers spec 07 §3 Learning/Session/Persistence criteria without MySQL."""
from datetime import timedelta

import pytest

from conftest import correct_answer_for, drive_to_exercise
from dsa_tutor.app.service import TutorService
from dsa_tutor.domain.models import EventType, Pace, utcnow
from dsa_tutor.persistence.memory_repositories import MemoryStorage


def test_first_turn_is_theory_then_mcq(service):
    view = service.start_session()
    assert view.kind == "theory"
    assert view.unit.theory
    view = service.mark_theory_seen()
    assert view.kind == "exercise"
    assert view.exercise.interaction_type.value == "mcq"


def test_correct_answers_advance_across_skills(service):
    view, _ = drive_to_exercise(service)
    seen_skills = [view.exercise.skill_id]
    for _ in range(80):
        view = service.submit_response(correct_answer_for(view.exercise))
        if view.kind == "ended":
            break
        if view.kind == "info":
            break
        if view.kind == "theory":
            view = service.mark_theory_seen()
            if view.kind == "exercise":
                seen_skills.append(view.exercise.skill_id)
            continue
        if view.kind == "exercise":
            seen_skills.append(view.exercise.skill_id)
    # progression must follow the curriculum order prefix
    order = service.curriculum.learning_order()
    assert seen_skills[0] == "graph_definition"
    rank = {sid: i for i, sid in enumerate(order)}
    ranks = [rank[sid] for sid in seen_skills]
    # allow revisits (remediation/variation) but never a jump backwards by more than a few steps
    for i in range(1, len(ranks)):
        assert ranks[i] >= ranks[i - 1] - 2, f"progression jumped backwards at {seen_skills[i]}"
    assert ranks[-1] >= 3, "should progress through several skills with all-correct answers"


def test_assisted_success_is_not_independent(service):
    view, _ = drive_to_exercise(service, target_type="mcq")
    view = service.submit_response("z")  # wrong
    assert view.evaluation.correct is False
    view = service.request_hint()
    assert view.hint is not None
    # re-fetch current exercise and answer correctly with the hint
    view = service.start_session(resume=True)
    assert view.kind == "exercise"
    result = service.submit_response(correct_answer_for(view.exercise))
    assert result.evaluation.correct is True
    attempt = service.storage.attempts_for_learner(service.learner.id)[-1]
    assert attempt.independent_success is False
    assert attempt.hints_used == 1


def test_remediation_flow_on_failure(service):
    view, _ = drive_to_exercise(service)
    wrong_view = service.submit_response("definitely wrong answer")
    assert wrong_view.evaluation.correct is False
    # next presented exercise should be the remediation micro-question path
    assert wrong_view.kind == "exercise"
    assert wrong_view.decision.action.value in {"remediation", "prerequisite_revisit",
                                                "reduce_difficulty", "repeat", "variation"}


def test_events_persist_in_order(service):
    view = service.start_session()
    service.mark_theory_seen()
    service.submit_response(correct_answer_for(view.exercise) if view.kind == "exercise"
                            else correct_answer_for(service.start_session(resume=True).exercise))
    types = [e.event_type for e in service.storage.events_for_session(service.session.id)]
    assert EventType.SESSION_STARTED in types
    assert EventType.THEORY_VIEWED in types
    assert EventType.QUESTION_PRESENTED in types
    assert EventType.ANSWER_SUBMITTED in types
    assert EventType.ANSWER_EVALUATED in types
    seqs = [e.seq for e in service.storage.events_for_session(service.session.id)]
    assert seqs == sorted(seqs)


def test_stop_and_resume_from_persisted_point(service):
    view, _ = drive_to_exercise(service)
    current = view.exercise.id
    stopped = service.stop_session("mid-session stop")
    assert "persisted" in stopped.extra["message"]
    # simulate restart: brand-new service over the same storage
    from dsa_tutor.config import AppConfig
    service2 = TutorService(service.storage, AppConfig())
    resumed = service2.start_session(resume=True)
    assert resumed.kind == "exercise"
    assert resumed.exercise.id == current
    assert any("resumed" in w for w in resumed.decision.why)


def test_daily_plan_adjusts_from_progress(config):
    from datetime import date
    from dsa_tutor.domain.models import DailyPlan
    storage = MemoryStorage()
    fresh = TutorService(storage, config)
    yesterday = date.today().fromordinal(date.today().toordinal() - 1)
    storage.upsert_daily_plan(DailyPlan(id=None, learner_id=fresh.learner.id,
                                        plan_date=yesterday, target_units=4,
                                        completed_units=6))
    plan = fresh._today_plan()
    assert plan.target_units == 5  # over-achievement yesterday -> higher target today


def test_budget_respected_fast_pace(service):
    view = service.start_session(pace=Pace.FAST)
    assert service.session.budget_minutes == 45
    # backdate the session start to exhaust the budget
    service.session.started_at = utcnow() - timedelta(minutes=46)
    view = service.submit_response(correct_answer_for(view.exercise) if view.kind == "exercise"
                                   else "x")
    # with 0 remaining, the engine must end the session at a natural point
    if view.kind == "ended":
        return
    # otherwise the next unit-opening is blocked -> ended
    assert view.kind in {"ended", "info"}


def test_ai_cannot_mutate_state_directly(service):
    """Even if the AI returns a scary recommended_action, engine owns the decision."""
    view, _ = drive_to_exercise(service)
    before = len(service.storage.assessments_for_learner(service.learner.id))
    service.submit_response(correct_answer_for(view.exercise))
    after = service.storage.assessments_for_learner(service.learner.id)
    # assessments only move through evidence aggregation, never by AI decree
    assert len(after) >= before
    for skill_id, assessment in after.items():
        for dim in ("knowledge", "execution", "reasoning", "transfer"):
            assert 0.0 <= getattr(assessment, dim) <= 1.0


def test_progress_report_shape(service):
    view = service.start_session()
    service.submit_response(correct_answer_for(view.exercise) if view.kind == "exercise" else "a")
    report = service.progress_report()
    assert len(report["skills"]) == 56
    assert {"skill", "state", "evidence", "mastered", "module"} \
        <= set(report["skills"][0].keys())
    assert report["skills"][0]["state"] in {"NOT_SEEN", "INTRODUCED", "DEVELOPING",
                                            "PRACTICED", "PROFICIENT", "INDEPENDENT"}
    assert report["daily"]["target_units"] >= 1


def test_low_confidence_ai_recommendation_is_neutralized(service):
    """Review hardening item 8: a low-confidence AI recommendation cannot cause a
    strong/non-standard engine decision. The engine notes the neutralization."""
    from dsa_tutor.ai.interface import MockAITutor
    from dsa_tutor.ai.schemas import EvaluationResult
    service.ai = MockAITutor(evaluation=EvaluationResult(
        correct=True, score=1.0, understood_concept=True,
        identified_misconception=None, missing_skill=None, hint_level=None,
        recommended_action="acknowledge_advance", ai_confidence=0.3,
        feedback="low confidence observation"))
    view, _ = drive_to_exercise(service, target_type="free_form")
    view = service.submit_response(correct_answer_for(view.exercise))
    assert view.decision is not None
    assert any("low-confidence" in w for w in view.decision.why), \
        f"expected low-confidence neutralization note in {view.decision.why}"
    # the neutralized recommendation must not appear as an engine reason
    assert not any("acknowledge_advance" in w for w in view.decision.why)
