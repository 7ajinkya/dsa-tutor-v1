"""OpenAI-compatible external LLM provider — backward-compatible path (spec 06 §5).

Works with any OpenAI-style /chat/completions endpoint (OpenAI, Azure OpenAI gateways,
local vLLM/Ollama OpenAI adapters, ...). Structured JSON output is validated by
ai.schemas; HTTP errors, malformed JSON and schema violations raise AIProviderError
so the hybrid layer can fall back to the builtin provider safely.

Stdlib-only HTTP (urllib) keeps the dependency footprint minimal; retries use
exponential backoff; per-session call caps are enforced here.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Any

from . import prompts
from .schemas import (
    EvaluationResult, GeneratedExercise, HintResult, SchemaValidationError,
    normalize_hint_level, validate_evaluation_payload, validate_hint_payload,
)
from ..domain.models import Exercise


class AIProviderError(Exception):
    pass


class OpenAICompatibleTutor:
    name = "openai"

    def __init__(self, config):
        self.config = config          # AIConfig
        self.calls = 0
        self.model = config.model
        from .usage_guard import UsageGuard
        self.usage = UsageGuard(limit=config.daily_request_limit, path=config.usage_file)

    # ---------------------------------------------------------- http core
    def _chat(self, system: str, user: str) -> str:
        if self.config.max_calls_per_session and self.calls >= self.config.max_calls_per_session:
            raise AIProviderError("per-session AI call limit reached")
        if self.usage.exhausted():
            raise AIProviderError(self.usage.exhausted_message)
        payload = {
            "model": self.config.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "response_format": {"type": "json_object"},
        }
        body = json.dumps(payload).encode("utf-8")
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            self.calls += 1
            self.usage.record()  # every outbound HTTP attempt counts against the daily budget
            request = urllib.request.Request(
                url, data=body, method="POST",
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {self.config.api_key}",
                         "User-Agent": "dsa-tutor/0.1 (local learning tool)"},
            )
            try:
                with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as exc:
                try:
                    body = exc.read().decode("utf-8", "replace")[:300]
                except Exception:  # noqa: BLE001
                    body = ""
                last_error = AIProviderError(f"HTTP {exc.code} from LLM API {body}")
                if exc.code == 429:
                    last_error = AIProviderError(
                        "external provider rate-limited (429) - daily or per-minute free-tier "
                        "limit hit; the offline tutor continues in the meantime")
                if exc.code not in {429, 500, 502, 503, 504}:
                    break
            except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
                last_error = AIProviderError(f"LLM API transport/parse error: {exc}")
            if attempt < self.config.max_retries:
                time.sleep(min(2 ** attempt, 8))
        raise last_error or AIProviderError("LLM API call failed")

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        text = text.strip()
        fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if fence:
            text = fence.group(1).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise AIProviderError("no JSON object found in model output")
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError as exc:
            raise AIProviderError(f"invalid JSON from model: {exc}") from None

    # ---------------------------------------------------------- tasks
    def evaluate(self, exercise: Exercise, response: str, context: dict) -> EvaluationResult:
        ctx = dict(context)
        ctx["exercise"] = self._exercise_brief(exercise)
        ctx["learner_response"] = response
        raw = self._chat(prompts.EVALUATION_SYSTEM, prompts.evaluation_user(ctx))
        data = self._extract_json(raw)
        # normalize common omissions from small local models (strict schema still applies after)
        if not data.get("recommended_action"):
            data["recommended_action"] = ("acknowledge_advance" if data.get("correct") is True
                                          else "retry")
        if data.get("score") is None and data.get("correct") is True:
            data["score"] = 1.0
        if data.get("score") is None and data.get("correct") is False:
            data["score"] = 0.0
        try:
            data = validate_evaluation_payload(data, set(context.get("valid_skill_ids", set())))
        except SchemaValidationError as exc:
            raise AIProviderError(f"schema violation: {exc}") from None
        return EvaluationResult(
            correct=data.get("correct"), score=float(data.get("score", 0.0)),
            understood_concept=data.get("understood_concept"),
            identified_misconception=data.get("identified_misconception"),
            missing_skill=data.get("missing_skill"),
            recommended_action=data.get("recommended_action", "retry"),
            hint_level=data.get("hint_level"),
            feedback=str(data.get("feedback", ""))[:1200],
            confidence_signal=data.get("confidence_signal"),
            ai_confidence=data.get("ai_confidence"),
            provider=self.name, model=self.config.model,
            prompt_version=prompts.PROMPT_VERSION, raw=data,
        )

    def detect_misconception(self, exercise: Exercise, response: str, context: dict) -> EvaluationResult:
        return self.evaluate(exercise, response, context)

    def generate_hint(self, exercise: Exercise, response: str, hints_used: int, context: dict) -> HintResult:
        ctx = dict(context)
        ctx["exercise"] = self._exercise_brief(exercise, include_solution=False)
        ctx["learner_response"] = response
        ctx["hints_already_used"] = hints_used
        ctx["next_hint_level"] = min(hints_used + 1, 5)
        raw = self._chat(prompts.HINT_SYSTEM, prompts.hint_user(ctx))
        data = self._extract_json(raw)
        try:
            data = validate_hint_payload(data)
        except SchemaValidationError as exc:
            raise AIProviderError(f"schema violation: {exc}") from None
        level = int(data.get("hint_level", ctx["next_hint_level"]))
        return HintResult(level=level, kind=data.get("hint_kind", "light_hint"),
                          text=str(data["hint_text"])[:1500], is_solution=False,
                          provider=self.name, model=self.config.model,
                          prompt_version=prompts.PROMPT_VERSION)

    hint = generate_hint  # legacy alias

    def generate_controlled_remediation(self, skill_id: str, context: dict) -> GeneratedExercise:
        ctx = {"skill_id": skill_id, "skill_title": context.get("skill_title", skill_id),
               "difficulty_bounds": context.get("difficulty_bounds", {}),
               "recent_missed_concepts": context.get("recent_missed_concepts", [])}
        raw = self._chat(prompts.GENERATE_SYSTEM, prompts.generate_user(ctx))
        data = self._extract_json(raw)
        generated = GeneratedExercise(
            skill_id=str(data.get("skill_id", skill_id)),
            interaction_type=str(data.get("interaction_type", "mcq")),
            prompt=str(data.get("prompt", "")),
            payload=data.get("payload") or {},
            difficulty=data.get("difficulty") or {},
            source="ai", provider=self.name, model=self.config.model,
            prompt_version=prompts.PROMPT_VERSION,
        )
        errors = generated.validate(set(context.get("valid_skill_ids", set())) | {skill_id})
        if errors:
            raise AIProviderError(f"generated exercise rejected: {'; '.join(errors)}")
        return generated

    generate_micro_question = generate_controlled_remediation  # legacy alias

    def explain(self, theory: str | None, connect_back: str) -> "ExplainResult":
        ctx = {"theory": theory or "", "current_task": connect_back}
        text = self._chat(prompts.EXPLAIN_SYSTEM, prompts.explain_user(ctx)).strip()[:2000]
        from .schemas import ExplainResult
        return ExplainResult(text=text, provider=self.name, model=self.config.model,
                             prompt_version=prompts.PROMPT_VERSION, ai_confidence=None)

    @staticmethod
    def _exercise_brief(exercise: Exercise, include_solution: bool = True) -> dict:
        brief = {
            "id": exercise.id, "skill_id": exercise.skill_id,
            "interaction_type": exercise.interaction_type.value,
            "prompt": exercise.prompt,
            "hint_ladder_used": [h["kind"] for h in exercise.hint_ladder],
        }
        payload = exercise.payload
        if exercise.interaction_type.value == "mcq":
            brief["choices"] = payload.get("choices", [])
            brief["answer_id"] = payload.get("answer_id")
            brief["explanation"] = payload.get("explanation")
        elif exercise.interaction_type.value in {"output_prediction", "code_tracing"}:
            brief["expected_output"] = payload.get("expected_output")
        elif exercise.interaction_type.value == "complexity_question":
            brief["acceptable_answers"] = payload.get("acceptable", [])
        elif exercise.interaction_type.value == "free_form":
            brief["reference_points"] = payload.get("reference_points", [])
            brief["min_points"] = payload.get("min_points")
        elif exercise.interaction_type.value == "code_writing" and include_solution:
            brief["tests"] = payload.get("tests", [])
            brief["reference_solution"] = payload.get("solution")
        return brief
