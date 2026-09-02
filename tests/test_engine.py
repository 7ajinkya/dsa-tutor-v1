"""Deterministic engine decisions (spec 07 §3 Learning + Session)."""
from datetime import timedelta

from dsa_tutor.domain.engine import EngineSnapshot, LearningEngine
from dsa_tutor.domain.models import (
    EngineAction, EvidenceOutcome, EvidenceRecord, EvidenceType, LearnerState,
    MasteryDimension, Pace, TutoringSession, utcnow,
)


def snap(curriculum, config, state, evidence=None, assessments=None, remaining=20.0):
    """config here is the EngineConfig."""
    session = TutoringSession(id=1, learner_id=1, pace=Pace.NORMAL,
                              started_at=utcnow() - timedelta(
                                  minutes=config.pace_budget_minutes["normal"] - remaining),
                              budget_minutes=config.pace_budget_minutes["normal"])
    return EngineSnapshot(state=state, assessments=assessments or {}, evidence=evidence or {},
                          session=session, remaining_minutes=remaining)


def independent_evidence(skill_id, dim, n=2, etype=EvidenceType.RECOGNITION):
    return [EvidenceRecord(attempt_id=None, skill_id=skill_id, dimension=dim,
                           evidence_type=etype,
                           outcome=EvidenceOutcome.INDEPENDENT_SUCCESS, weight=1.0,
                           created_at=utcnow() - timedelta(minutes=i))
            for i in range(n)]


def test_fresh_learner_starts_at_graph_definition(curriculum, config):
    engine = LearningEngine(curriculum, config.engine)
    decision = engine.select_next(snap(curriculum, config.engine, LearnerState(learner_id=1)))
    assert decision.skill_id == "graph_definition"
    assert decision.action == EngineAction.ADVANCE
    assert decision.exercise_id is not None
    assert decision.why  # explainability always present


def test_mastered_skills_are_skipped_in_order(curriculum, config):
    engine = LearningEngine(curriculum, config.engine)
    state = LearnerState(learner_id=1)
    evidence = {}
    for sid in ["graph_definition", "vertices_edges", "adjacency", "directed_vs_undirected",
                "weighted_vs_unweighted"]:
        for etype in curriculum.skill(sid).evidence_requirements:
            evidence.setdefault(sid, []).extend(independent_evidence(sid, etype, n=2, etype=etype))
    decision = engine.select_next(snap(curriculum, config.engine, state, evidence))
    assert decision.skill_id == "degree"


def test_weak_core_prereq_triggers_revisit_not_abandonment(curriculum, config):
    engine = LearningEngine(curriculum, config.engine)
    state = LearnerState(learner_id=1)
    order = curriculum.learning_order()
    evidence = {}
    for sid in order[:order.index("traversal_state")]:
        for etype in curriculum.skill(sid).evidence_requirements:
            evidence.setdefault(sid, []).extend(independent_evidence(sid, etype, n=2, etype=etype))
    decision = engine.select_next(snap(curriculum, config.engine, state, evidence))
    assert decision.action == EngineAction.ADVANCE
    assert decision.skill_id == "traversal_state"


def test_budget_exhaustion_ends_session(curriculum, config):
    engine = LearningEngine(curriculum, config.engine)
    decision = engine.select_next(snap(curriculum, config.engine, LearnerState(learner_id=1),
                                       remaining=0.0))
    assert decision.action == EngineAction.END_SESSION
    assert "budget" in " ".join(decision.why).lower()


def test_short_budget_prefers_natural_stop(curriculum, config):
    engine = LearningEngine(curriculum, config.engine)
    decision = engine.select_next(snap(curriculum, config.engine, LearnerState(learner_id=1),
                                       remaining=3.0))
    assert any("short window" in w for w in decision.why)


def test_correct_attempt_on_mastered_skill_advances(curriculum, config):
    from conftest import mcq_for
    engine = LearningEngine(curriculum, config.engine)
    state = LearnerState(learner_id=1)
    exercise = mcq_for(curriculum, "graph_definition")
    evidence = {"graph_definition": independent_evidence(
        "graph_definition", MasteryDimension.KNOWLEDGE, n=2, etype=EvidenceType.RECOGNITION)}
    decision = engine.decide_after_attempt(snap(curriculum, config.engine, state, evidence),
                                           exercise, score=1.0, is_correct=True, hints_used=0,
                                           solution_revealed=False)
    assert decision.action == EngineAction.ADVANCE
    assert decision.skill_id == "vertices_edges"


def test_single_failure_triggers_remediation(curriculum, config):
    from conftest import mcq_for
    engine = LearningEngine(curriculum, config.engine)
    state = LearnerState(learner_id=1)
    exercise = mcq_for(curriculum, "graph_definition")
    decision = engine.decide_after_attempt(snap(curriculum, config.engine, state),
                                           exercise, score=0.0, is_correct=False, hints_used=0,
                                           solution_revealed=False)
    assert decision.action == EngineAction.REMEDIATION
    assert decision.exercise_id == exercise.id


def test_second_failure_with_linked_prereq_revisits_it(curriculum, config):
    from conftest import exercise_by
    engine = LearningEngine(curriculum, config.engine)
    state = LearnerState(learner_id=1)
    exercise = exercise_by(curriculum, "bfs_implementation", "code_writing")
    snapshot = snap(curriculum, config.engine, state)
    first = engine.decide_after_attempt(snapshot, exercise, score=0.0, is_correct=False,
                                        hints_used=0, solution_revealed=False,
                                        ai_missing_skill="queue_mechanism")
    assert first.action == EngineAction.REMEDIATION  # first failure -> smaller step
    second = engine.decide_after_attempt(snapshot, exercise, score=0.0, is_correct=False,
                                         hints_used=0, solution_revealed=False,
                                         ai_missing_skill="queue_mechanism")
    assert second.action == EngineAction.PREREQUISITE_REVISIT
    assert second.skill_id == "queue_mechanism"


def test_third_failure_intervenes_without_punishing_progress(curriculum, config):
    """Amendment RC-12: attempt 3 is an intervention threshold, not a failure limit."""
    from conftest import exercise_by
    engine = LearningEngine(curriculum, config.engine)
    state = LearnerState(learner_id=1)
    exercise = exercise_by(curriculum, "bfs_implementation", "code_writing")
    for _ in range(2):
        engine.decide_after_attempt(snap(curriculum, config.engine, state), exercise,
                                    score=0.0, is_correct=False, hints_used=0,
                                    solution_revealed=False)
    # improving trend -> keep going with a variation (no mechanical termination)
    improving = snap(curriculum, config.engine, state)
    improving.recent_scores = [0.0, 0.3]
    decision = engine.decide_after_attempt(improving, exercise, score=0.45, is_correct=False,
                                           hints_used=0, solution_revealed=False)
    assert decision.action in {EngineAction.VARIATION, EngineAction.REPEAT}
    assert any("progress" in w for w in decision.why)
    # no meaningful progress + weak evidence -> reduce difficulty
    decision2 = engine.decide_after_attempt(snap(curriculum, config.engine, state), exercise,
                                            score=0.0, is_correct=False, hints_used=0,
                                            solution_revealed=False)
    assert decision2.action in {EngineAction.REDUCE_DIFFICULTY, EngineAction.VARIATION,
                                EngineAction.REPEAT}


def test_assisted_success_does_not_advance_mastery(curriculum, config):
    from conftest import mcq_for
    engine = LearningEngine(curriculum, config.engine)
    state = LearnerState(learner_id=1)
    exercise = mcq_for(curriculum, "graph_definition")
    decision = engine.decide_after_attempt(snap(curriculum, config.engine, state), exercise,
                                           score=1.0, is_correct=True, hints_used=2,
                                           solution_revealed=False)
    assert decision.action in {EngineAction.REPEAT, EngineAction.VARIATION}
    assert "assisted" in " ".join(decision.why)


def test_pace_budgets_match_spec(config):
    assert config.engine.pace_budget_minutes["slow"] == 12       # 10-15 window
    assert config.engine.pace_budget_minutes["normal"] == 25
    assert config.engine.pace_budget_minutes["fast"] == 45
