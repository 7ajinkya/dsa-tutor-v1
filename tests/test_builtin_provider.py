"""Builtin (AutoClaw-authored) provider: grading quality + the fixed AI evaluation harness
(spec 04 §10: correct, partial, misconception, wrong-reasoning, overconfident,
underconfident, hint, solution-copying)."""
import pytest

from dsa_tutor.ai.builtin_provider import BuiltinAITutor
from dsa_tutor.domain.models import InteractionType


@pytest.fixture()
def ai():
    return BuiltinAITutor()


def _exercise(curriculum, eid):
    return curriculum.exercises[eid]


# ---------------------------------------------------------------- fixed harness
def test_harness_case_correct_mcq(ai, curriculum):
    ex = _exercise(curriculum, "e001_graph_definition")
    result = ai.evaluate(ex, "a", {})
    assert result.correct is True and result.score == 1.0
    assert result.recommended_action == "acknowledge_advance"


def test_harness_case_partial_free_form(ai, curriculum):
    ex = next(e for e in curriculum.exercises.values()
              if e.skill_id == "visited_state" and e.interaction_type == InteractionType.FREE_FORM)
    result = ai.evaluate(ex, "It loops because the algorithm re-enters the same vertex.", {})
    assert result.correct is False
    assert 0.0 < result.score < 0.8
    assert "miss" in result.feedback.lower()


def test_harness_case_misconception_detected(ai, curriculum):
    ex = _exercise(curriculum, "e001_graph_definition")
    result = ai.evaluate(ex, "a", {})
    assert result.correct
    # misconception scan fires on explanation-style responses
    ex2 = next(e for e in curriculum.exercises.values()
               if e.skill_id == "visited_state" and e.interaction_type == InteractionType.FREE_FORM)
    result2 = ai.evaluate(ex2, "You should mark vertices visited when they are dequeued, "
                               "that is why it loops.", {})
    assert result2.identified_misconception is not None
    assert result2.missing_skill == "bfs_visited_handling"


def test_harness_case_wrong_reasoning_bfs_vs_dfs_order(ai, curriculum):
    from conftest import exercise_by
    ex = exercise_by(curriculum, "bfs_manual_tracing", "output_prediction")  # expects A B C D E F
    result = ai.evaluate(ex, "A B D F C E", {})  # the DFS order on the same graph
    assert result.correct is False
    assert result.missing_skill == "traversal_order"
    assert result.score == pytest_approx(0.4)  # right vertex set, wrong order family


def test_harness_case_overconfidence_flagged(ai, curriculum):
    ex = _exercise(curriculum, "e001_graph_definition")
    result = ai.evaluate(ex, "d", {"confidence": 5})
    assert result.correct is False
    assert result.confidence_signal == "overconfident"


def test_harness_case_underconfidence_flagged(ai, curriculum):
    ex = _exercise(curriculum, "e001_graph_definition")
    result = ai.evaluate(ex, "a", {"confidence": 1})
    assert result.correct is True
    assert result.confidence_signal == "underconfident"


def test_harness_case_hint_ladder_escalates_without_leak(ai, curriculum):
    from conftest import exercise_by
    ex = exercise_by(curriculum, "bfs_implementation", "code_writing")
    texts = []
    kinds = []
    for used in range(4):
        hint = ai.hint(ex, "", used, {})
        texts.append(hint.text)
        kinds.append(hint.kind)
        assert hint.is_solution is False
    assert kinds == ["socratic_question", "micro_question", "light_hint", "targeted_explanation"]
    solution = ex.payload["solution"]
    body = "\n".join(line.strip() for line in solution.splitlines() if line.strip())
    for text in texts:
        assert "queue = deque([start])" not in text
        for code_line in [ln for ln in body.splitlines() if ln.startswith("        ")]:
            assert code_line not in text


def test_harness_case_solution_copying_flagged(ai, curriculum):
    from conftest import exercise_by
    ex = exercise_by(curriculum, "bfs_implementation", "code_writing")
    result = ai.evaluate(ex, ex.payload["solution"], {})
    assert result.correct is False
    assert "solution" in result.feedback.lower()
    assert result.missing_skill is not None


def test_harness_case_code_writing_partial_credit(ai, curriculum):
    from conftest import exercise_by
    ex = exercise_by(curriculum, "bfs_implementation", "code_writing")
    partial = ex.payload["solution"].replace("        order.append(node)\n", "") \
        .replace("    order = []\n", "")
    # missing order collection -> wrong outputs but runs
    result = ai.evaluate(ex, partial, {})
    assert result.correct is False
    assert result.score < 1.0


def test_graph_construction_grading(ai, curriculum):
    ex = next(e for e in curriculum.exercises.values()
              if e.interaction_type == InteractionType.GRAPH_CONSTRUCTION)
    ok = ai.evaluate(ex, "A-B, A-C, A-D", {})
    assert ok.correct is True
    extra = ai.evaluate(ex, "A-B, A-C, A-D, B-C", {})
    assert extra.correct is False
    assert "degree" in extra.feedback.lower()


def test_complexity_grading(ai, curriculum):
    from conftest import exercise_by
    ex = exercise_by(curriculum, "bfs_time_complexity", "complexity_question")
    assert ai.evaluate(ex, "O(V+E)", {}).correct is True
    assert ai.evaluate(ex, "o(v + e)", {}).correct is True
    assert ai.evaluate(ex, "O(N+M)", {}).correct is True
    half = ai.evaluate(ex, "O(V)", {})
    assert half.correct is False and half.score == pytest_approx(0.4)


def pytest_approx(value):
    from pytest import approx
    return approx(value)


def test_micro_question_generation_is_curriculum_bounded(ai, curriculum):
    generated = ai.generate_micro_question("visited_state", {"skill_title": "Visited state"})
    assert generated.skill_id == "visited_state"
    assert generated.validate(set(curriculum.skills)) == []
    fallback = ai.generate_micro_question("degree", {"skill_title": "Degree"})
    assert fallback.validate(set(curriculum.skills)) == []


def test_explain_combines_theory_and_connect_back(ai, curriculum):
    result = ai.explain("Theory body.", "Connect this to your task.")
    assert "Theory body." in result.text and "Connect this" in result.text
    assert result.provider == "builtin"
    assert result.validate() == []
