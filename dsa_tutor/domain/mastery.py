"""Mastery derivation — evidence predicates, not numeric authority (review RC-09 as amended).

Qualitative states per skill, derived ONLY from explicit evidence predicates:

    NOT_SEEN      no evidence at all
    INTRODUCED    basic exposure/recognition demonstrated (>=1 success in any required type)
    DEVELOPING    some relevant evidence exists but required evidence is incomplete/inconsistent
    PRACTICED     core skill demonstrated in practice: every required evidence type has >=1 success
    PROFICIENT    required evidence demonstrated consistently with limited/no assistance
    INDEPENDENT   required evidence demonstrated independently in application/transfer

Rules of authority:
- Numeric metrics (dimension_score etc.) are retained ONLY for analytics/debugging.
- PROFICIENT/INDEPENDENT additionally require RECENT evidence: successes older than
  MASTERY_RECENCY_DAYS no longer support them (mastery is therefore NON-MONOTONIC:
  a previously proficient learner whose recent performance degrades transitions down).
- Assistance is evidence: attempts are tagged with the max assistance level used
  (L0 none ... L6 complete solution); only <= ASSISTANCE_LIMIT_FOR_INDEPENDENCE
  counts toward PROFICIENT/INDEPENDENT.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from enum import Enum

from .models import (
    DIMENSION_AFFINITY, EvidenceOutcome, EvidenceRecord, EvidenceType,
    InteractionType, LearningUnit, MasteryDimension, MasteryState, UnitType,
)

OUTCOME_SCORES: dict[EvidenceOutcome, float] = {
    EvidenceOutcome.INDEPENDENT_SUCCESS: 1.0,
    EvidenceOutcome.ASSISTED_SUCCESS: 0.6,
    EvidenceOutcome.PARTIAL_SUCCESS: 0.4,
    EvidenceOutcome.FAILED: 0.0,
}

RECENCY_HALF_LIFE_DAYS = 14.0
MIN_EVIDENCE_FOR_MASTERY = 2
DEPTH_BONUS_UNIT_TYPES = {UnitType.PRACTICE, UnitType.ASSESS, UnitType.APPLY}

# --- amendment RC-09: mastery transitions use these predicates, not numeric scores ---
PROFICIENT_RECENCY_DAYS = 30          # PROFICIENT/INDEPENDENT require recent successes
# Assistance policy (review hardening item 5): L0-L1 successes count as INDEPENDENT;
# L2-L6 are ASSISTED. assistance_level >= ASSISTANCE_LIMIT_FOR_INDEPENDENCE (=2)
# therefore means 'some assistance was used'.
ASSISTANCE_LIMIT_FOR_INDEPENDENCE = 2
PRACTICE_MIN_INDEPENDENT = 1          # PRACTICED needs >=1 independent success
PROFICIENT_MIN_INDEPENDENT = 2        # PROFICIENT needs >=2 independent successes in required types


def recency_weight(when: datetime, now: datetime) -> float:
    age_days = max(0.0, (now - when).total_seconds() / 86400.0)
    return 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)


def outcome_for_attempt(is_correct: bool | None, score: float, assistance_level: int,
                        solution_revealed: bool) -> EvidenceOutcome:
    """Assistance level is evidence (review RC-11): L0-L1 independent, L2-L4 assisted,
    L5-L6 strongly assisted (partial/complete solution can never be independent)."""
    if not is_correct:
        return EvidenceOutcome.FAILED if (score or 0.0) < 0.4 else EvidenceOutcome.PARTIAL_SUCCESS
    if solution_revealed or assistance_level >= 5:
        return EvidenceOutcome.ASSISTED_SUCCESS
    if assistance_level >= 2:
        return EvidenceOutcome.ASSISTED_SUCCESS
    return EvidenceOutcome.INDEPENDENT_SUCCESS


def evidence_type_for(exercise_type: InteractionType) -> EvidenceType:
    return EvidenceType.for_interaction(exercise_type)


def evidence_for_attempt(unit: LearningUnit | None, exercise_type: InteractionType,
                         outcome: EvidenceOutcome) -> list[EvidenceRecord]:
    """One graded attempt becomes evidence: one type record + per-dimension records,
    all carrying the SAME evidence_type so per-type latest-outcome logic stays coherent."""
    depth = 1.3 if (unit is not None and unit.unit_type in DEPTH_BONUS_UNIT_TYPES) else 1.0
    etype = evidence_type_for(exercise_type)
    records = [EvidenceRecord(
        attempt_id=None, skill_id="", dimension=MasteryDimension.KNOWLEDGE,
        evidence_type=etype,
        outcome=outcome, weight=round(depth, 4),
    )]
    for dim, affinity in DIMENSION_AFFINITY.get(exercise_type, {}).items():
        if affinity <= 0:
            continue
        records.append(EvidenceRecord(
            attempt_id=None, skill_id="", dimension=dim,
            evidence_type=etype,
            outcome=outcome, weight=round(affinity * depth, 4),
        ))
    return records


def dimension_score(records: list[EvidenceRecord], now: datetime) -> float:
    """ANALYTICS ONLY — never the authority for mastery transitions."""
    num = 0.0
    den = 0.0
    for r in records:
        w = r.weight * recency_weight(r.created_at, now)
        num += w * OUTCOME_SCORES[r.outcome]
        den += w
    if den <= 0:
        return 0.0
    return num / den


# ---------------------------------------------------------------- states ----
def _type_latest_outcome(records: list[EvidenceRecord], etype: EvidenceType) -> EvidenceOutcome | None:
    """Latest outcome for an evidence type. 'Latest attempt wins' makes mastery
    NON-MONOTONIC: a fresh failure undermines an older success of the same type.
    Insertion order is chronological (evidence is appended as attempts happen)."""
    latest_outcome = None
    for r in records:
        if r.evidence_type is etype:
            latest_outcome = r.outcome
    return latest_outcome


def _type_success(records: list[EvidenceRecord], etype: EvidenceType,
                  independent_only: bool, now: datetime) -> bool:
    latest_outcome = _type_latest_outcome(records, etype)
    if latest_outcome is None:
        return False
    if independent_only:
        if latest_outcome is not EvidenceOutcome.INDEPENDENT_SUCCESS:
            return False
        # recency: independent demonstrations expire
        latest_at = max((r.created_at for r in records if r.evidence_type is etype
                         and r.outcome is EvidenceOutcome.INDEPENDENT_SUCCESS), default=None)
        return latest_at is not None and latest_at >= now - timedelta(days=PROFICIENT_RECENCY_DAYS)
    return latest_outcome in {EvidenceOutcome.INDEPENDENT_SUCCESS, EvidenceOutcome.ASSISTED_SUCCESS}


def derive_state(records: list[EvidenceRecord], required_types: set[EvidenceType],
                 now: datetime) -> MasteryState:
    """THE authority for mastery. Pure evidence predicates — no numeric thresholds.
    Non-monotonic by design: the LATEST outcome per evidence type decides (amendment 8)."""
    required = set(required_types) or {EvidenceType.RECOGNITION}
    if not records:
        return MasteryState.NOT_SEEN
    successes = [r for r in records
                 if r.outcome in {EvidenceOutcome.INDEPENDENT_SUCCESS,
                                  EvidenceOutcome.ASSISTED_SUCCESS}]
    if not successes:
        return MasteryState.INTRODUCED if any(
            r.evidence_type in required for r in records) else MasteryState.NOT_SEEN

    all_required_success = all(_type_success(records, t, independent_only=False, now=now)
                               for t in required)
    core_independent_count = sum(
        1 for t in required if _type_success(records, t, independent_only=True, now=now))
    total_independent = sum(
        1 for r in records
        if r.outcome is EvidenceOutcome.INDEPENDENT_SUCCESS
        and r.created_at >= now - timedelta(days=PROFICIENT_RECENCY_DAYS))

    if len(successes) == 1:
        # exactly one demonstrated success so far -> basic exposure (INTRODUCED)
        return MasteryState.INTRODUCED

    if not all_required_success:
        # latest outcomes show incomplete/inconsistent required evidence (amendment 8:
        # a fresh failure DROPS the state -> refresh practice is scheduled naturally)
        return MasteryState.DEVELOPING

    if (core_independent_count >= len(required) and total_independent >= PROFICIENT_MIN_INDEPENDENT):
        has_application = _type_success(records, EvidenceType.APPLICATION,
                                        independent_only=True, now=now) or \
            _type_success(records, EvidenceType.TRANSFER,
                          independent_only=True, now=now)
        if has_application:
            return MasteryState.INDEPENDENT
        return MasteryState.PROFICIENT
    if all_required_success and core_independent_count >= PRACTICE_MIN_INDEPENDENT:
        return MasteryState.PRACTICED
    return MasteryState.DEVELOPING


def is_state_at_least(state: MasteryState, floor: MasteryState) -> bool:
    """Ordered helper for ENGINE POLICY only (not for state derivation)."""
    order = [MasteryState.NOT_SEEN, MasteryState.INTRODUCED, MasteryState.DEVELOPING,
             MasteryState.PRACTICED, MasteryState.PROFICIENT, MasteryState.INDEPENDENT]
    return order.index(state) >= order.index(floor)
