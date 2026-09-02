"""Provider selection: builtin (default) | openai (backward compat) | hybrid (ext first, safe fallback)."""
from __future__ import annotations

from .builtin_provider import BuiltinAITutor
from .interface import AITutor
from .schemas import EvaluationResult, HintResult
from ..domain.models import Exercise


class HybridAITutor(AITutor):
    """External LLM first; on ANY failure or schema violation fall back to builtin.

    The degraded flag on results makes the fallback visible in attempts/logs.
    """
    name = "hybrid"

    def __init__(self, external: AITutor, builtin: AITutor):
        self.external = external
        self.builtin = builtin
        self.model = external.model
        self.last_fallback_reason: str | None = None

    @property
    def calls(self) -> int:
        return self.external.calls + self.builtin.calls

    def _fallback(self, exc: Exception) -> None:
        self.last_fallback_reason = f"{type(exc).__name__}: {exc}"

    def evaluate(self, exercise: Exercise, response: str, context: dict) -> EvaluationResult:
        try:
            return self.external.evaluate(exercise, response, context)
        except Exception as exc:  # noqa: BLE001 - any external failure must degrade safely
            self._fallback(exc)
            result = self.builtin.evaluate(exercise, response, context)
            result.degraded = True
            return result

    def detect_misconception(self, exercise: Exercise, response: str, context: dict) -> EvaluationResult:
        try:
            return self.external.detect_misconception(exercise, response, context)
        except Exception as exc:  # noqa: BLE001
            self._fallback(exc)
            result = self.builtin.detect_misconception(exercise, response, context)
            result.degraded = True
            return result

    def generate_hint(self, exercise: Exercise, response: str, hints_used: int, context: dict) -> HintResult:
        try:
            return self.external.generate_hint(exercise, response, hints_used, context)
        except Exception as exc:  # noqa: BLE001
            self._fallback(exc)
            return self.builtin.generate_hint(exercise, response, hints_used, context)

    hint = generate_hint  # legacy alias

    def generate_controlled_remediation(self, skill_id: str, context: dict):
        try:
            return self.external.generate_controlled_remediation(skill_id, context)
        except Exception as exc:  # noqa: BLE001
            self._fallback(exc)
            return self.builtin.generate_controlled_remediation(skill_id, context)

    generate_micro_question = generate_controlled_remediation  # legacy alias

    def explain(self, theory: str | None, connect_back: str) -> str:
        try:
            return self.external.explain(theory, connect_back)
        except Exception:  # noqa: BLE001
            return self.builtin.explain(theory, connect_back)


def get_ai_tutor(config):
    """Factory. builtin -> offline AutoClaw engine; openai -> external only;
    hybrid -> external with builtin safety net."""
    if config.ai.provider == "openai":
        from .openai_provider import OpenAICompatibleTutor
        return OpenAICompatibleTutor(config.ai)
    if config.ai.provider == "hybrid":
        from .openai_provider import OpenAICompatibleTutor
        return HybridAITutor(OpenAICompatibleTutor(config.ai), BuiltinAITutor())
    return BuiltinAITutor()
