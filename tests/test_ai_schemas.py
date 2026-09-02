"""AI contract validation + guardrails (spec 07 §3 AI)."""
import pytest

from dsa_tutor.ai.schemas import (
    EvaluationResult, SchemaValidationError, validate_evaluation_payload,
    validate_hint_payload,
)

VALID_SKILLS = {"visited_state", "queue_mechanism", "bfs_implementation"}


def test_valid_payload_passes():
    data = {"correct": False, "score": 0.4, "understood_concept": True,
            "identified_misconception": "confuses visited with processed",
            "missing_skill": "visited_state", "recommended_action": "micro_question",
            "hint_level": 1, "feedback": "ok", "confidence_signal": "overconfident"}
    out = validate_evaluation_payload(data, VALID_SKILLS)
    assert out["missing_skill"] == "visited_state"


def test_unknown_skill_rejected():
    with pytest.raises(SchemaValidationError) as exc:
        validate_evaluation_payload({"score": 0.5, "recommended_action": "retry",
                                     "missing_skill": "dijkstra_shortest_path"}, VALID_SKILLS)
    assert "not a V0 skill" in str(exc.value)


def test_bad_action_rejected():
    with pytest.raises(SchemaValidationError) as exc:
        validate_evaluation_payload({"score": 0.5, "recommended_action": "mark_mastered"},
                                    VALID_SKILLS)
    assert "not allowed" in str(exc.value)


def test_score_bounds_enforced():
    with pytest.raises(SchemaValidationError):
        validate_evaluation_payload({"score": 1.5, "recommended_action": "retry"}, VALID_SKILLS)
    with pytest.raises(SchemaValidationError):
        validate_evaluation_payload({"score": -0.1, "recommended_action": "retry"}, VALID_SKILLS)


def test_hint_payload_rejects_solution_reveal():
    with pytest.raises(SchemaValidationError) as exc:
        validate_hint_payload({"hint_level": 2, "hint_kind": "light_hint",
                               "hint_text": "use deque", "is_solution": True})
    assert "never reveal" in str(exc.value)


def test_hint_payload_bad_kind_rejected():
    with pytest.raises(SchemaValidationError):
        validate_hint_payload({"hint_level": 2, "hint_kind": "full_solution",
                               "hint_text": "..."})


def test_evaluation_result_defaults_safe():
    result = EvaluationResult(correct=None, score=0.0, understood_concept=None,
                              identified_misconception=None, missing_skill=None,
                              recommended_action="retry", hint_level=None, feedback="")
    assert result.to_dict()["degraded"] is False
    assert result.to_dict()["provider"] == "builtin"


def test_explain_result_validation():
    from dsa_tutor.ai.schemas import ExplainResult
    ok = ExplainResult(text="hello", provider="builtin", ai_confidence=1.0)
    assert ok.validate() == []
    empty = ExplainResult(text="   ", ai_confidence=1.0)
    assert any("empty" in e for e in empty.validate())
    bad = ExplainResult(text="hello", ai_confidence=1.5)
    assert any("0..1" in e for e in bad.validate())
