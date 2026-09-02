"""Mastery tests — evidence-predicate derivation (review RC-09 as amended)."""
from datetime import timedelta

import pytest

from dsa_tutor.domain import mastery
from dsa_tutor.domain.models import (
    EvidenceOutcome, EvidenceRecord, EvidenceType, InteractionType,
    LearningUnit, MasteryDimension, MasteryState, UnitType, utcnow,
)


def rec(skill="bfs_implementation", dim=MasteryDimension.KNOWLEDGE,
        outcome=EvidenceOutcome.INDEPENDENT_SUCCESS, weight=1.0, age_days=0.0,
        etype=EvidenceType.RECOGNITION, assistance=0):
    return EvidenceRecord(attempt_id=None, skill_id=skill, dimension=dim, outcome=outcome,
                          weight=weight, evidence_type=etype, assistance_level=assistance,
                          created_at=utcnow() - timedelta(days=age_days))


def pytest_approx(value):
    from pytest import approx
    return approx(value)


def test_outcome_scores_fixed():
    assert mastery.OUTCOME_SCORES[EvidenceOutcome.INDEPENDENT_SUCCESS] == 1.0
    assert mastery.OUTCOME_SCORES[EvidenceOutcome.ASSISTED_SUCCESS] == 0.6
    assert mastery.OUTCOME_SCORES[EvidenceOutcome.PARTIAL_SUCCESS] == 0.4
    assert mastery.OUTCOME_SCORES[EvidenceOutcome.FAILED] == 0.0


def test_assistance_level_is_evidence():
    assert mastery.outcome_for_attempt(True, 1.0, assistance_level=0, solution_revealed=False) \
        is EvidenceOutcome.INDEPENDENT_SUCCESS
    assert mastery.outcome_for_attempt(True, 1.0, assistance_level=1, solution_revealed=False) \
        is EvidenceOutcome.INDEPENDENT_SUCCESS
    assert mastery.outcome_for_attempt(True, 1.0, assistance_level=2, solution_revealed=False) \
        is EvidenceOutcome.ASSISTED_SUCCESS
    assert mastery.outcome_for_attempt(True, 1.0, assistance_level=5, solution_revealed=False) \
        is EvidenceOutcome.ASSISTED_SUCCESS
    assert mastery.outcome_for_attempt(True, 1.0, assistance_level=0, solution_revealed=True) \
        is EvidenceOutcome.ASSISTED_SUCCESS


def test_recency_decay_two_week_half_life():
    now = utcnow()
    assert mastery.recency_weight(now, now) == 1.0
    assert abs(mastery.recency_weight(now - timedelta(days=14), now) - 0.5) < 1e-9


def test_dimension_score_is_analytics_only():
    records = [rec(outcome=EvidenceOutcome.INDEPENDENT_SUCCESS),
               rec(outcome=EvidenceOutcome.FAILED)]
    assert mastery.dimension_score(records, utcnow()) == pytest_approx(0.5)


REQUIRED = {EvidenceType.RECOGNITION}


def test_state_not_seen():
    assert mastery.derive_state([], REQUIRED, utcnow()) is MasteryState.NOT_SEEN


def test_state_introduced_on_first_success():
    now = utcnow()
    records = [rec(outcome=EvidenceOutcome.ASSISTED_SUCCESS, assistance=3)]
    assert mastery.derive_state(records, REQUIRED, now) is MasteryState.INTRODUCED


def test_state_developing_when_required_types_incomplete():
    now = utcnow()
    # two successes in RECOGNITION, but the required TRACE type was never demonstrated
    records = [rec(outcome=EvidenceOutcome.INDEPENDENT_SUCCESS),
               rec(outcome=EvidenceOutcome.INDEPENDENT_SUCCESS)]
    wide = {EvidenceType.RECOGNITION, EvidenceType.TRACE}
    assert mastery.derive_state(records, wide, now) is MasteryState.DEVELOPING


def test_state_practiced_then_proficient_via_independence():
    now = utcnow()
    records = [rec(etype=EvidenceType.RECOGNITION),
               rec(etype=EvidenceType.TRACE, assistance=2,
                   outcome=EvidenceOutcome.ASSISTED_SUCCESS)]
    # every required type has a success, but TRACE only with assistance -> PRACTICED
    assert mastery.derive_state(records, {EvidenceType.RECOGNITION, EvidenceType.TRACE}, now) \
        is MasteryState.PRACTICED
    records.append(rec(etype=EvidenceType.TRACE))
    # now every required type demonstrated independently -> PROFICIENT
    assert mastery.derive_state(records, {EvidenceType.RECOGNITION, EvidenceType.TRACE}, now) \
        is MasteryState.PROFICIENT


def test_state_proficient_requires_two_independent_in_required_types():
    now = utcnow()
    records = [rec(etype=EvidenceType.RECOGNITION),
               rec(etype=EvidenceType.TRACE, assistance=2,
                   outcome=EvidenceOutcome.ASSISTED_SUCCESS)]
    # only RECOGNITION is independent -> not PROFICIENT
    assert mastery.derive_state(records, {EvidenceType.RECOGNITION, EvidenceType.TRACE}, now) \
        is MasteryState.PRACTICED
    records.append(rec(etype=EvidenceType.TRACE))
    assert mastery.derive_state(records, {EvidenceType.RECOGNITION, EvidenceType.TRACE}, now) \
        is MasteryState.PROFICIENT


def test_state_requires_recent_evidence_non_monotonic():
    now = utcnow()
    fresh = [rec(etype=EvidenceType.RECOGNITION), rec(etype=EvidenceType.RECOGNITION)]
    assert mastery.derive_state(fresh, REQUIRED, now) is MasteryState.PROFICIENT
    stale = [rec(etype=EvidenceType.RECOGNITION, age_days=40),
             rec(etype=EvidenceType.RECOGNITION, age_days=40)]
    # old successes no longer support PROFICIENT (regression scenario, review amendment 8)
    assert mastery.derive_state(stale, REQUIRED, now) in {MasteryState.DEVELOPING,
                                                          MasteryState.PRACTICED}


def test_state_independent_requires_application_evidence():
    now = utcnow()
    records = [rec(etype=EvidenceType.RECOGNITION), rec(etype=EvidenceType.RECOGNITION),
               rec(etype=EvidenceType.APPLICATION)]
    state = mastery.derive_state(records, REQUIRED, now)
    assert state is MasteryState.INDEPENDENT


def test_skill_mastery_requires_required_evidence_types_demonstrated():
    """Hardening item 1: mastery decisions use evidence_requirements, never legacy
    numeric thresholds — IMPLEMENTATION evidence alone cannot master an
    IMPLEMENTATION-requiring skill without the recency/consistency predicates."""
    now = utcnow()
    records = [rec(etype=EvidenceType.IMPLEMENTATION), rec(etype=EvidenceType.IMPLEMENTATION)]
    assert mastery.derive_state(records, {EvidenceType.IMPLEMENTATION}, now) \
        is mastery.MasteryState.PROFICIENT


def test_evidence_for_attempt_carries_type_and_dimensions():
    unit = LearningUnit(id="u", skill_id="s", title="t", goal="g", unit_type=UnitType.PRACTICE,
                        ordering=1)
    records = mastery.evidence_for_attempt(unit, InteractionType.CODE_WRITING,
                                           EvidenceOutcome.INDEPENDENT_SUCCESS)
    types = {r.evidence_type for r in records}
    assert EvidenceType.IMPLEMENTATION in types
    dims = {r.dimension for r in records}
    assert MasteryDimension.EXECUTION in dims
    exec_record = [r for r in records if r.dimension == MasteryDimension.EXECUTION][0]
    assert exec_record.weight == pytest_approx(1.3)
