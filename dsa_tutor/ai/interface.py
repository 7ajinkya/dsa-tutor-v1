"""Explicit AI Tutor interface (review RC-04 as amended).

Five operations, each with its own schema, validation, allowed values, error handling,
logging (service layer), mocking, and fixed test cases:

    evaluate(...)                       semantic grading of one response
    detect_misconception(...)           misconception-only observation
    generate_hint(...)                  next hint in the ladder
    explain(...)                        targeted contextual explanation
    generate_controlled_remediation(...)  bounded remediation item for one skill

Every result optionally carries `ai_confidence`: the MODEL's confidence in its own
interpretation (0..1). It is NOT learner correctness probability. Low-confidence
observations never trigger aggressive engine decisions by themselves.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .schemas import EvaluationResult, ExplainResult, HintResult, GeneratedExercise
from ..domain.models import Exercise


class AITutor(ABC):
    name = "abstract"
    model = None
    calls = 0

    @abstractmethod
    def evaluate(self, exercise: Exercise, response: str, context: dict) -> EvaluationResult: ...

    @abstractmethod
    def detect_misconception(self, exercise: Exercise, response: str, context: dict) -> EvaluationResult:
        """Misconception-only observation: same schema, grading fields may be null."""

    @abstractmethod
    def generate_hint(self, exercise: Exercise, response: str, hints_used: int,
                      context: dict) -> HintResult: ...

    @abstractmethod
    def explain(self, theory: str | None, connect_back: str) -> ExplainResult: ...

    @abstractmethod
    def generate_controlled_remediation(self, skill_id: str, context: dict) -> GeneratedExercise: ...

    # convenience alias kept for existing callers
    def hint(self, exercise: Exercise, response: str, hints_used: int, context: dict) -> HintResult:
        return self.generate_hint(exercise, response, hints_used, context)

    def generate_micro_question(self, skill_id: str, context: dict) -> GeneratedExercise:
        return self.generate_controlled_remediation(skill_id, context)


class MockAITutor(AITutor):
    """Scripted AI for Learning Engine tests — never touches network or models."""

    name = "mock"

    def __init__(self, evaluation: EvaluationResult | None = None,
                 hint: HintResult | None = None):
        self._evaluation = evaluation
        self._hint = hint or HintResult(level=1, kind="socratic_question",
                                        text="What have you tried so far?")

    def evaluate(self, exercise, response, context):
        self.calls += 1
        if self._evaluation is not None:
            return self._evaluation
        return EvaluationResult(correct=True, score=1.0, understood_concept=True,
                                identified_misconception=None, missing_skill=None,
                                recommended_action="acknowledge_advance", hint_level=None,
                                feedback="mock", ai_confidence=1.0)

    def detect_misconception(self, exercise, response, context):
        return self.evaluate(exercise, response, context)

    def generate_hint(self, exercise, response, hints_used, context):
        self.calls += 1
        return self._hint

    def explain(self, theory, connect_back):
        self.calls += 1
        return ExplainResult(text=f"{theory or ''} {connect_back}".strip(),
                             provider=self.name, ai_confidence=1.0)

    def generate_controlled_remediation(self, skill_id, context):
        self.calls += 1
        from .schemas import GeneratedExercise
        return GeneratedExercise(skill_id=skill_id, interaction_type="mcq",
                                 prompt=f"Mock remediation check for {skill_id}.",
                                 payload={"choices": [{"id": "a", "text": "yes"},
                                                      {"id": "b", "text": "no"}],
                                          "answer_id": "a", "explanation": "mock"},
                                 difficulty={"conceptual": 1, "implementation": 1,
                                             "reasoning": 1, "transfer": 1})
