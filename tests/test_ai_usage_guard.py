"""Daily usage-guard tests: budget tracking, day reset, provider pre-check, hybrid fallback."""
import json
import urllib.error

import pytest

from dsa_tutor.ai.openai_provider import AIProviderError, OpenAICompatibleTutor
from dsa_tutor.ai.usage_guard import UsageGuard
from dsa_tutor.config import AIConfig
from dsa_tutor.ai.builtin_provider import BuiltinAITutor
from dsa_tutor.ai.factory import HybridAITutor


@pytest.fixture()
def guard_path(tmp_path):
    return str(tmp_path / "ai_usage.json")


def test_guard_counts_and_persists_across_instances(guard_path):
    g1 = UsageGuard(limit=5, path=guard_path)
    g1.record()
    g1.record(2)
    assert g1.status()["used"] == 3
    g2 = UsageGuard(limit=5, path=guard_path)  # fresh instance, same file
    assert g2.status()["used"] == 3
    assert g2.status()["remaining"] == 2


def test_guard_blocks_at_limit(guard_path):
    g = UsageGuard(limit=2, path=guard_path)
    g.record(2)
    assert g.exhausted() is True
    assert "daily external AI limit reached (2/2" in g.exhausted_message


def test_guard_resets_on_new_day(guard_path):
    g = UsageGuard(limit=2, path=guard_path)
    g.record(2)
    # simulate yesterday's file on disk (fresh process = fresh read)
    state = json.loads(open(guard_path).read())
    state["date"] = "2000-01-01"
    open(guard_path, "w").write(json.dumps(state))
    g2 = UsageGuard(limit=2, path=guard_path)
    assert g2.exhausted() is False
    assert g2.status()["used"] == 0


def test_guard_zero_limit_is_unlimited(guard_path):
    g = UsageGuard(limit=0, path=guard_path)
    g.record(999)
    assert g.exhausted() is False


def test_provider_refuses_before_hitting_api_when_exhausted(guard_path, monkeypatch, curriculum):
    UsageGuard(limit=1, path=guard_path).record(1)  # budget already spent
    config = AIConfig(provider="openai", model="m", api_key="***",
                      base_url="http://fake/v1", daily_request_limit=1, usage_file=guard_path)
    provider = OpenAICompatibleTutor(config)

    def explode(*a, **k):  # any HTTP attempt is a test failure
        raise AssertionError("HTTP must not be called when the daily budget is spent")

    monkeypatch.setattr("dsa_tutor.ai.openai_provider.urllib.request.urlopen", explode)
    ex = curriculum.exercises["e001_graph_definition"]
    with pytest.raises(AIProviderError) as exc:
        provider.evaluate(ex, "a", {"valid_skill_ids": list(curriculum.skills)})
    assert "daily external AI limit reached" in str(exc.value)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def test_provider_records_every_attempt_and_recovers(guard_path, monkeypatch, curriculum):
    config = AIConfig(provider="openai", model="m", api_key="***",
                      base_url="http://fake/v1", max_retries=1,
                      daily_request_limit=10, usage_file=guard_path)
    provider = OpenAICompatibleTutor(config)
    state = {"calls": 0}

    def fake_urlopen(request, timeout=None):
        state["calls"] += 1
        if state["calls"] == 1:
            raise urllib.error.HTTPError(request.full_url, 429, "slow down", {}, None)
        return FakeResponse({"choices": [{"message": {"content": json.dumps({
            "correct": True, "score": 1.0, "recommended_action": "acknowledge_advance"})}}]})

    monkeypatch.setattr("dsa_tutor.ai.openai_provider.urllib.request.urlopen", fake_urlopen)
    ex = curriculum.exercises["e001_graph_definition"]
    result = provider.evaluate(ex, "a", {"valid_skill_ids": list(curriculum.skills)})
    assert result.correct is True
    assert state["calls"] == 2                      # 1 failed attempt + 1 success
    assert UsageGuard(limit=10, path=guard_path).status()["used"] == 2  # both attempts counted


def test_hybrid_falls_back_when_guard_exhausted(guard_path, curriculum):
    UsageGuard(limit=3, path=guard_path).record(3)
    config = AIConfig(provider="openai", model="m", api_key="***",
                      base_url="http://fake/v1", daily_request_limit=3, usage_file=guard_path)
    external = OpenAICompatibleTutor(config)
    hybrid = HybridAITutor(external, BuiltinAITutor())
    ex = curriculum.exercises["e001_graph_definition"]
    result = hybrid.evaluate(ex, "a", {"valid_skill_ids": list(curriculum.skills)})
    assert result.correct is True              # builtin answered
    assert result.degraded is True             # fallback visible
    assert "daily external AI limit" in str(hybrid.last_fallback_reason)
