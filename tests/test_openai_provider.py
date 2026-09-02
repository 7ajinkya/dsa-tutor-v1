"""External OpenAI-compatible provider with mocked HTTP (no network in tests)."""
import json
import urllib.error
from pathlib import Path

import pytest

from dsa_tutor.ai.openai_provider import AIProviderError, OpenAICompatibleTutor
from dsa_tutor.config import AIConfig


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def make_provider(monkeypatch, content: str, fail_first: int = 0, tmp_path=None):
    config = AIConfig(provider="openai", model="test-model", api_key="test-key",
                      base_url="http://fake/v1", max_retries=2,
                      daily_request_limit=10000,
                      usage_file=str((tmp_path or Path(".")) / "usage.json"))
    provider = OpenAICompatibleTutor(config)
    state = {"calls": 0}

    def fake_urlopen(request, timeout=None):
        state["calls"] += 1
        if state["calls"] <= fail_first:
            raise urllib.error.HTTPError(request.full_url, 503, "boom", {}, None)
        return FakeResponse({"choices": [{"message": {"content": content}}]})

    monkeypatch.setattr("dsa_tutor.ai.openai_provider.urllib.request.urlopen", fake_urlopen)
    return provider


EVAL_JSON = json.dumps({
    "correct": False, "score": 0.3, "understood_concept": False,
    "identified_misconception": "queue/stack mixup", "missing_skill": "queue_mechanism",
    "recommended_action": "micro_question", "hint_level": 2,
    "feedback": "Think about which end of the queue leaves first.",
})


def test_evaluate_parses_valid_json(monkeypatch, curriculum, tmp_path):
    provider = make_provider(monkeypatch, EVAL_JSON, tmp_path=tmp_path)
    ex = curriculum.exercises["e001_graph_definition"]
    result = provider.evaluate(ex, "d", {"valid_skill_ids": list(curriculum.skills)})
    assert result.correct is False
    assert result.missing_skill == "queue_mechanism"
    assert result.provider == "openai"
    assert result.model == "test-model"


def test_evaluate_handles_fenced_json(monkeypatch, curriculum, tmp_path):
    provider = make_provider(monkeypatch, "```json\n" + EVAL_JSON + "\n```", tmp_path=tmp_path)
    ex = curriculum.exercises["e001_graph_definition"]
    result = provider.evaluate(ex, "d", {"valid_skill_ids": list(curriculum.skills)})
    assert result.score == 0.3


def test_schema_violation_raises(monkeypatch, curriculum, tmp_path):
    bad = json.dumps({"correct": True, "score": 0.9, "recommended_action": "mark_mastered",
                      "missing_skill": "topological_sort"})
    provider = make_provider(monkeypatch, bad, tmp_path=tmp_path)
    ex = curriculum.exercises["e001_graph_definition"]
    with pytest.raises(AIProviderError):
        provider.evaluate(ex, "a", {"valid_skill_ids": list(curriculum.skills)})


def test_retry_then_success(monkeypatch, curriculum, tmp_path):
    provider = make_provider(monkeypatch, EVAL_JSON, fail_first=1, tmp_path=tmp_path)
    ex = curriculum.exercises["e001_graph_definition"]
    result = provider.evaluate(ex, "d", {"valid_skill_ids": list(curriculum.skills)})
    assert result.correct is False  # succeeded on retry


def test_persistent_failure_raises(monkeypatch, curriculum, tmp_path):
    provider = make_provider(monkeypatch, EVAL_JSON, fail_first=10, tmp_path=tmp_path)
    ex = curriculum.exercises["e001_graph_definition"]
    with pytest.raises(AIProviderError):
        provider.evaluate(ex, "d", {"valid_skill_ids": list(curriculum.skills)})


def test_hint_rejects_solution_reveal(monkeypatch, curriculum, tmp_path):
    bad_hint = json.dumps({"hint_level": 3, "hint_kind": "light_hint",
                           "hint_text": "here is the full code: ...", "is_solution": True})
    provider = make_provider(monkeypatch, bad_hint, tmp_path=tmp_path)
    ex = curriculum.exercises["e001_graph_definition"]
    with pytest.raises(AIProviderError):
        provider.hint(ex, "", 0, {"valid_skill_ids": list(curriculum.skills)})


def test_hybrid_falls_back_to_builtin(monkeypatch, curriculum, tmp_path):
    from dsa_tutor.ai.builtin_provider import BuiltinAITutor
    from dsa_tutor.ai.factory import HybridAITutor
    provider = make_provider(monkeypatch, "not json at all {{{", fail_first=10, tmp_path=tmp_path)
    hybrid = HybridAITutor(provider, BuiltinAITutor())
    ex = curriculum.exercises["e001_graph_definition"]
    result = hybrid.evaluate(ex, "a", {"valid_skill_ids": list(curriculum.skills)})
    assert result.correct is True          # builtin graded it
    assert result.degraded is True         # fallback is visible
    assert hybrid.last_fallback_reason is not None
