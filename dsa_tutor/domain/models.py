"""Domain models: the shared vocabulary of the whole system.

The domain layer owns these types; CLI, persistence and AI layers all depend on
them — never the other way around (dependency direction per architecture doc §4).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Optional


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Pace(str, Enum):
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"


class MasteryDimension(str, Enum):
    KNOWLEDGE = "knowledge"
    EXECUTION = "execution"
    REASONING = "reasoning"
    TRANSFER = "transfer"


class EvidenceOutcome(str, Enum):
    INDEPENDENT_SUCCESS = "independent_success"
    ASSISTED_SUCCESS = "assisted_success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class PrereqStrength(str, Enum):
    CORE = "core"
    SUPPORTING = "supporting"


class UnitType(str, Enum):
    TEACH = "teach"
    PRACTICE = "practice"
    ASSESS = "assess"
    APPLY = "apply"


class InteractionType(str, Enum):
    THEORY = "theory"
    MCQ = "mcq"
    FREE_FORM = "free_form"
    OUTPUT_PREDICTION = "output_prediction"
    GRAPH_CONSTRUCTION = "graph_construction"
    CODE_WRITING = "code_writing"
    CODE_TRACING = "code_tracing"
    COMPLEXITY_QUESTION = "complexity_question"
    CONFIDENCE_RATING = "confidence_rating"
    REFLECTION = "reflection"


class MasteryState(str, Enum):
    """Qualitative mastery states (review RC-09). Derived from evidence predicates —
    never from numeric scores. Order exists only for engine policy helpers."""
    NOT_SEEN = "NOT_SEEN"
    INTRODUCED = "INTRODUCED"
    DEVELOPING = "DEVELOPING"
    PRACTICED = "PRACTICED"
    PROFICIENT = "PROFICIENT"
    INDEPENDENT = "INDEPENDENT"


class EvidenceType(str, Enum):
    """Type of capability an activity demonstrates (review RC-23 amendment)."""
    RECOGNITION = "RECOGNITION"
    RECALL = "RECALL"
    EXPLANATION = "EXPLANATION"
    TRACE = "TRACE"
    CONSTRUCTION = "CONSTRUCTION"
    IMPLEMENTATION = "IMPLEMENTATION"
    APPLICATION = "APPLICATION"
    TRANSFER = "TRANSFER"
    REFLECTION = "REFLECTION"

    @classmethod
    def for_interaction(cls, interaction_type: "InteractionType") -> "EvidenceType":
        return _INTERACTION_EVIDENCE[interaction_type]


class ActivityRole(str, Enum):
    """Explicit pedagogical role of a learning activity (review RC-06 amendment).
    'Problem' is a SCOPE marker, not a role — any role can be a problem."""
    RECOGNITION = "RECOGNITION"
    RECALL = "RECALL"
    EXPLANATION = "EXPLANATION"
    TRACE = "TRACE"
    CONSTRUCTION = "CONSTRUCTION"
    IMPLEMENTATION = "IMPLEMENTATION"
    APPLICATION = "APPLICATION"
    TRANSFER = "TRANSFER"
    REFLECTION = "REFLECTION"


class ActivityScope(str, Enum):
    MICRO = "micro"          # small step inside a unit
    PROBLEM = "problem"      # substantial application task


_INTERACTION_EVIDENCE = {
    InteractionType.MCQ: EvidenceType.RECOGNITION,
    InteractionType.FREE_FORM: EvidenceType.EXPLANATION,
    InteractionType.OUTPUT_PREDICTION: EvidenceType.TRACE,
    InteractionType.CODE_TRACING: EvidenceType.TRACE,
    InteractionType.GRAPH_CONSTRUCTION: EvidenceType.CONSTRUCTION,
    InteractionType.CODE_WRITING: EvidenceType.IMPLEMENTATION,
    InteractionType.COMPLEXITY_QUESTION: EvidenceType.EXPLANATION,
    InteractionType.REFLECTION: EvidenceType.REFLECTION,
    InteractionType.THEORY: EvidenceType.RECOGNITION,
    InteractionType.CONFIDENCE_RATING: EvidenceType.RECOGNITION,
}


class EngineAction(str, Enum):
    ADVANCE = "advance"
    REPEAT = "repeat"
    VARIATION = "variation"
    REMEDIATION = "remediation"
    PREREQUISITE_REVISIT = "prerequisite_revisit"
    REDUCE_DIFFICULTY = "reduce_difficulty"
    INCREASE_DIFFICULTY = "increase_difficulty"
    END_SESSION = "end_session"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class EventType(str, Enum):
    SESSION_STARTED = "SESSION_STARTED"
    THEORY_VIEWED = "THEORY_VIEWED"
    QUESTION_PRESENTED = "QUESTION_PRESENTED"
    ANSWER_SUBMITTED = "ANSWER_SUBMITTED"
    ANSWER_EVALUATED = "ANSWER_EVALUATED"
    HINT_REQUESTED = "HINT_REQUESTED"
    HINT_DELIVERED = "HINT_DELIVERED"
    REMEDIATION_STARTED = "REMEDIATION_STARTED"
    REMEDIATION_COMPLETED = "REMEDIATION_COMPLETED"
    PROBLEM_COMPLETED = "PROBLEM_COMPLETED"
    PROBLEM_FAILED = "PROBLEM_FAILED"
    CONFIDENCE_REPORTED = "CONFIDENCE_REPORTED"
    SESSION_ENDED = "SESSION_ENDED"


# Interaction types that the engine grades deterministically (spec 04 §7 cost controls)
DETERMINISTIC_TYPES = {
    InteractionType.MCQ,
    InteractionType.OUTPUT_PREDICTION,
    InteractionType.CODE_TRACING,
    InteractionType.CODE_WRITING,
    InteractionType.GRAPH_CONSTRUCTION,
    InteractionType.COMPLEXITY_QUESTION,
}

# Interaction types that primarily evidence each mastery dimension.
DIMENSION_AFFINITY: dict[InteractionType, dict[MasteryDimension, float]] = {
    InteractionType.MCQ: {MasteryDimension.KNOWLEDGE: 1.0, MasteryDimension.REASONING: 0.4,
                          MasteryDimension.EXECUTION: 0.15, MasteryDimension.TRANSFER: 0.35},
    InteractionType.FREE_FORM: {MasteryDimension.KNOWLEDGE: 1.0, MasteryDimension.REASONING: 1.0,
                                MasteryDimension.EXECUTION: 0.1, MasteryDimension.TRANSFER: 0.6},
    InteractionType.OUTPUT_PREDICTION: {MasteryDimension.EXECUTION: 0.8, MasteryDimension.REASONING: 0.7,
                                        MasteryDimension.KNOWLEDGE: 0.4, MasteryDimension.TRANSFER: 0.4},
    InteractionType.CODE_TRACING: {MasteryDimension.EXECUTION: 1.0, MasteryDimension.REASONING: 0.7,
                                   MasteryDimension.KNOWLEDGE: 0.3, MasteryDimension.TRANSFER: 0.4},
    InteractionType.CODE_WRITING: {MasteryDimension.EXECUTION: 1.0, MasteryDimension.TRANSFER: 0.6,
                                   MasteryDimension.REASONING: 0.35, MasteryDimension.KNOWLEDGE: 0.2},
    InteractionType.GRAPH_CONSTRUCTION: {MasteryDimension.KNOWLEDGE: 0.7, MasteryDimension.EXECUTION: 0.6,
                                         MasteryDimension.TRANSFER: 0.5, MasteryDimension.REASONING: 0.3},
    InteractionType.COMPLEXITY_QUESTION: {MasteryDimension.REASONING: 1.0, MasteryDimension.KNOWLEDGE: 0.6,
                                          MasteryDimension.EXECUTION: 0.1, MasteryDimension.TRANSFER: 0.4},
    InteractionType.REFLECTION: {MasteryDimension.KNOWLEDGE: 0.2, MasteryDimension.REASONING: 0.2,
                                 MasteryDimension.EXECUTION: 0.0, MasteryDimension.TRANSFER: 0.1},
}


@dataclass
class Learner:
    id: Optional[int]
    name: str
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class Topic:
    id: str
    title: str
    ordering: int


@dataclass
class Skill:
    id: str                    # language-independent slug, e.g. "visited_state"
    title: str
    topic_id: str
    ordering: int
    section: str
    module: str = "Module A - Graph Mental Model"   # learner-facing module (review RC-07)
    description: str = ""                           # capability description (RC-08)
    # evidence types that MUST be demonstrated for PRACTICED/PROFICIENT (RC-09 amendment)
    evidence_requirements: frozenset[EvidenceType] = frozenset({EvidenceType.RECOGNITION})
    # Review hardening item 7: the four difficulty dimensions are DESCRIPTIVE metadata
    # and intervention/variation signals. They are NOT converted into a numeric
    # mastery/readiness equation, and no ordinal state-to-difficulty arithmetic exists.
    # complexity: dict dim→1..5 (descriptors of challenge, review RC-13 amendment)
    complexity: dict[MasteryDimension, int] = field(default_factory=dict)
    is_boundary: bool = False  # top of the V0 boundary; engine never advances past it
    is_optional: bool = False  # e.g. explicit-stack DFS: served only as an extension
    required_dimensions: frozenset[MasteryDimension] = frozenset({MasteryDimension.KNOWLEDGE})

    def validate(self) -> list[str]:
        errors = []
        for dim, level in self.complexity.items():
            if not 1 <= level <= 5:
                errors.append(f"skill {self.id}: complexity {dim.name}={level} outside 1..5")
        if not self.required_dimensions:
            errors.append(f"skill {self.id}: no required dimensions")
        return errors


@dataclass
class SkillPrerequisite:
    skill_id: str
    prerequisite_skill_id: str
    strength: PrereqStrength = PrereqStrength.CORE


@dataclass
class LearningUnit:
    id: str
    skill_id: str
    title: str
    goal: str
    unit_type: UnitType
    ordering: int
    theory: Optional[str] = None   # teach units carry theory text
    required_dimensions: frozenset[MasteryDimension] = frozenset()


@dataclass
class Exercise:
    """Learning Activity (review RC-06). Legacy class name `Exercise` is retained for
    implementation compatibility; documentation uses "Learning Activity".
    `role` is the pedagogical type,
    `scope` marks substantial activities (problems). Not every problem is code."""
    id: str
    unit_id: str
    skill_id: str
    interaction_type: InteractionType
    prompt: str
    payload: dict[str, Any]
    ordering: int = 0
    role: ActivityRole = ActivityRole.RECOGNITION
    scope: ActivityScope = ActivityScope.MICRO
    required_capabilities: frozenset[EvidenceType] = frozenset()   # readiness gate (RC-13)
    difficulty: dict[str, int] = field(default_factory=dict)  # conceptual/implementation/reasoning/transfer 1..5
    language: Optional[str] = None    # V0 exercises may be python; skills stay language-independent
    hint_ladder: list[dict[str, str]] = field(default_factory=list)  # [{kind, text}]
    max_hints: int = 4
    requires_ai: bool = False
    source: str = "curated"           # curated | ai
    prompt_version: Optional[str] = None

    def validate(self, valid_skill_ids: set[str]) -> list[str]:
        errors = []
        if self.skill_id not in valid_skill_ids:
            errors.append(f"exercise {self.id}: unknown skill {self.skill_id}")
        for axis, level in self.difficulty.items():
            if not 1 <= level <= 5:
                errors.append(f"exercise {self.id}: difficulty {axis}={level} outside 1..5")
        return errors


@dataclass
class Attempt:
    id: Optional[int]
    session_id: int
    learner_id: int
    exercise_id: str
    skill_id: str
    response: str
    is_correct: Optional[bool]
    score: float                       # 0..1
    evaluation: dict[str, Any]         # full structured evaluation payload (AI or deterministic)
    hints_used: int = 0
    max_assistance_level: int = 0     # L0 none ... L6 complete solution (review RC-11)
    independent_success: bool = False
    completed: bool = False
    solution_revealed: bool = False
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    prompt_version: Optional[str] = None
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class EvidenceRecord:
    attempt_id: Optional[int]
    skill_id: str
    dimension: MasteryDimension
    outcome: EvidenceOutcome
    weight: float
    evidence_type: EvidenceType = EvidenceType.RECOGNITION
    assistance_level: int = 0
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class SkillAssessment:
    learner_id: int
    skill_id: str
    knowledge: float = 0.0
    execution: float = 0.0
    reasoning: float = 0.0
    transfer: float = 0.0
    evidence_count: int = 0
    independent_successes: int = 0
    confidence_avg: Optional[float] = None
    updated_at: datetime = field(default_factory=utcnow)

    def dim(self, dimension: MasteryDimension) -> float:
        return getattr(self, dimension.value)

    def set_dim(self, dimension: MasteryDimension, value: float) -> None:
        setattr(self, dimension.value, round(min(1.0, max(0.0, value)), 4))


@dataclass
class TutoringSession:
    id: Optional[int]
    learner_id: int
    pace: Pace
    status: SessionStatus = SessionStatus.ACTIVE
    started_at: datetime = field(default_factory=utcnow)
    ended_at: Optional[datetime] = None
    budget_minutes: int = 25
    end_reason: Optional[str] = None
    last_unit_id: Optional[str] = None


@dataclass
class SessionEvent:
    id: Optional[int]
    session_id: int
    seq: int
    event_type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class LearnerState:
    learner_id: int
    current_skill_id: Optional[str] = None
    current_unit_id: Optional[str] = None
    current_exercise_id: Optional[str] = None
    pending_action: Optional[str] = None          # EngineAction value or None
    completed_unit_ids: list[str] = field(default_factory=list)
    unit_attempt_counts: dict[str, int] = field(default_factory=dict)   # exercise_id -> attempts
    exercise_failures: dict[str, int] = field(default_factory=dict)     # exercise_id -> consecutive failures
    hints_used_current: int = 0
    difficultylevel_shift: int = 0                # -1 reduced, 0 normal, +1 raised
    sessions_completed: int = 0
    updated_at: datetime = field(default_factory=utcnow)

    def total_attempts_for(self, exercise_id: str) -> int:
        return self.unit_attempt_counts.get(exercise_id, 0)

    def consecutive_failures_for(self, exercise_id: str) -> int:
        return self.exercise_failures.get(exercise_id, 0)


@dataclass
class DailyPlan:
    id: Optional[int]
    learner_id: int
    plan_date: date
    target_units: int
    completed_units: int = 0
    status: str = "active"
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class EngineDecision:
    """The single deterministic output of the learning engine. Carries its own explainability."""
    action: EngineAction
    skill_id: Optional[str] = None
    unit_id: Optional[str] = None
    exercise_id: Optional[str] = None
    why: list[str] = field(default_factory=list)   # human-readable reasons (spec 03 §10)

    @property
    def explanation(self) -> str:
        return " | ".join(self.why) if self.why else self.action.value
