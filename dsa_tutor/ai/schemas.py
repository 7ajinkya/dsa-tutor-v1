"""AI <-> engine contracts. Everything the AI returns must pass validation here.

Guardrail (spec 04 §4): AI results are *observations*, never state mutations. There is
no field through which the AI could set mastery, skip prerequisites, or change curriculum.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

RECOMMENDED_ACTIONS = {
    "acknowledge_advance", "micro_question", "prerequisite_check", "light_hint_needed",
    "targeted_explanation", "reduce_difficulty", "retry", "reflection",
}
CONFIDENCE_SIGNALS = {"overconfident", "underconfident", "calibrated"}
HINT_KINDS = {"socratic_question", "micro_question", "light_hint", "targeted_explanation",
              "partial_solution"}
ALLOWED_GENERATED_TYPES = {"mcq", "free_form", "output_prediction", "code_tracing",
                           "complexity_question"}


class SchemaValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass
class EvaluationResult:
    correct: Optional[bool]
    score: float
    understood_concept: Optional[bool]
    identified_misconception: Optional[str]
    missing_skill: Optional[str]
    recommended_action: str
    hint_level: Optional[int]
    feedback: str
    confidence_signal: Optional[str] = None
    # Amendment 8: model SELF-REPORTED confidence in its own interpretation —
    # a heuristic safety signal, NOT a calibrated probability of anything.
    # Low values simply prevent the observation from driving strong engine decisions.
    ai_confidence: Optional[float] = None
    provider: str = "builtin"
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    degraded: bool = False
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "correct": self.correct, "score": round(self.score, 4),
            "understood_concept": self.understood_concept,
            "identified_misconception": self.identified_misconception,
            "missing_skill": self.missing_skill,
            "recommended_action": self.recommended_action,
            "hint_level": self.hint_level, "feedback": self.feedback,
            "confidence_signal": self.confidence_signal,
            "ai_confidence": self.ai_confidence,
            "provider": self.provider, "model": self.model,
            "prompt_version": self.prompt_version, "degraded": self.degraded,
        }


@dataclass
class ExplainResult:
    """Structured result for the explain() operation (review hardening item 4)."""
    text: str
    provider: str = "builtin"
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    ai_confidence: Optional[float] = None

    def validate(self) -> list[str]:
        errors = []
        if not self.text or not self.text.strip():
            errors.append("explain text must not be empty")
        if self.ai_confidence is not None and not 0.0 <= self.ai_confidence <= 1.0:
            errors.append("ai_confidence must be within 0..1")
        return errors


@dataclass
class HintResult:
    level: int                      # 1..4, maps to spec 04 §5 ladder
    kind: str                       # socratic_question | micro_question | light_hint | targeted_explanation
    text: str
    is_solution: bool = False       # must stay False; solutions go through explicit reveal only
    provider: str = "builtin"
    model: Optional[str] = None
    prompt_version: Optional[str] = None


@dataclass
class GeneratedExercise:
    skill_id: str
    interaction_type: str
    prompt: str
    payload: dict[str, Any]
    difficulty: dict[str, int]
    source: str = "ai"
    provider: str = "builtin"
    model: Optional[str] = None
    prompt_version: Optional[str] = None

    def validate(self, valid_skill_ids: set[str]) -> list[str]:
        errors = []
        if self.skill_id not in valid_skill_ids:
            errors.append(f"generated exercise targets unknown skill '{self.skill_id}'")
        if self.interaction_type not in ALLOWED_GENERATED_TYPES:
            errors.append(f"generated exercise type '{self.interaction_type}' not allowed")
        if not self.prompt or len(self.prompt.strip()) < 10:
            errors.append("generated exercise prompt too short")
        for axis, level in self.difficulty.items():
            if axis not in {"conceptual", "implementation", "reasoning", "transfer"} or not 1 <= level <= 5:
                errors.append(f"generated difficulty axis invalid: {axis}={level}")
        return errors


def _validate_common(data: dict, errors: list[str]) -> None:
    if "score" not in data:
        errors.append("missing 'score'")
    else:
        try:
            value = float(data["score"])
            if not 0.0 <= value <= 1.0:
                errors.append("'score' must be within 0..1")
        except (TypeError, ValueError):
            errors.append("'score' must be a number")
    if "recommended_action" in data and data["recommended_action"] not in RECOMMENDED_ACTIONS:
        errors.append(f"'recommended_action' '{data['recommended_action']}' not allowed")
    if data.get("confidence_signal") is not None and \
            data["confidence_signal"] not in CONFIDENCE_SIGNALS:
        errors.append(f"'confidence_signal' '{data['confidence_signal']}' not allowed")
    if data.get("hint_level") is not None:
        try:
            level = int(data["hint_level"])
            if not 1 <= level <= 5:
                errors.append("'hint_level' must be 1..5")
        except (TypeError, ValueError):
            errors.append("'hint_level' must be an integer 1..5")
    if "ai_confidence" in data and data["ai_confidence"] is not None:
        try:
            value = float(data["ai_confidence"])
            if not 0.0 <= value <= 1.0:
                errors.append("'ai_confidence' must be within 0..1")
        except (TypeError, ValueError):
            errors.append("'ai_confidence' must be a number")
    if "correct" in data and data["correct"] is not None and not isinstance(data["correct"], bool):
        errors.append("'correct' must be a boolean or null")


def validate_evaluation_payload(data: dict, valid_skill_ids: set[str]) -> dict:
    """Validate a raw AI payload; raise SchemaValidationError with every problem found."""
    errors: list[str] = []
    if not isinstance(data, dict):
        raise SchemaValidationError(["evaluation payload must be a JSON object"])
    _validate_common(data, errors)
    missing_skill = data.get("missing_skill")
    if missing_skill is not None and missing_skill not in valid_skill_ids:
        errors.append(f"'missing_skill' '{missing_skill}' is not a V0 skill id")
    if errors:
        raise SchemaValidationError(errors)
    return data


def validate_hint_payload(data: dict) -> dict:
    errors: list[str] = []
    if not isinstance(data, dict):
        raise SchemaValidationError(["hint payload must be a JSON object"])
    if not data.get("hint_text") or not isinstance(data.get("hint_text"), str):
        errors.append("missing 'hint_text'")
    kind = data.get("hint_kind", "light_hint")
    if kind not in HINT_KINDS:
        errors.append(f"'hint_kind' '{kind}' not allowed")
    level = data.get("hint_level")
    try:
        if not 1 <= int(level) <= 5:
            errors.append("'hint_level' must be 1..5")
    except (TypeError, ValueError):
        errors.append("'hint_level' must be an integer 1..5")
    if data.get("is_solution") is True:
        errors.append("AI hints may never reveal the solution (is_solution=true rejected)")
    if errors:
        raise SchemaValidationError(errors)
    return data


def normalize_hint_level(kind: str) -> int:
    return {"socratic_question": 1, "micro_question": 2, "light_hint": 3,
            "targeted_explanation": 4, "partial_solution": 5}.get(kind, 3)
