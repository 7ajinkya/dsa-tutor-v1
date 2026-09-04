"""Curriculum acceptance criteria (spec 07 §3 Curriculum)."""
import pytest

from dsa_tutor.content.curriculum_v0 import EXERCISES, PREREQS, SKILLS, UNITS


def test_38_skills_encoded_with_modules():
    assert len(SKILLS) == 53, f"expected 41 V0 skills + 2 L2 + 3 L3 + 4 L4 + 3 L5 skills, got {len(SKILLS)}"
    modules = {s.module for s in SKILLS}
    assert len(modules) == 6 and any(m.startswith("Module A") for m in modules)


def test_curriculum_validates(curriculum):
    assert curriculum.validate() == []


def test_prerequisites_explicit_and_acyclic(curriculum):
    assert len(curriculum.prerequisites) == len(PREREQS)
    order = curriculum.learning_order()  # raises on cycle
    assert sorted(order) == sorted(curriculum.skills.keys())


def test_boundary_skill_exists_and_terminates(curriculum):
    boundary = [s for s in curriculum.skills.values() if s.is_boundary]
    assert len(boundary) == 1 and boundary[0].id == "v0_readiness"
    # nothing may lie beyond the boundary
    assert not [p for p in curriculum.prerequisites
                if p.prerequisite_skill_id == "v0_readiness"]


def test_advanced_topics_absent():
    forbidden = ["dijkstra", "topological", "mst", "dsu", "scc", "bridges",
                 "articulation", "kruskal", "prim", "bellman"]
    text = " ".join(s.id + " " + s.title for s in SKILLS).lower()
    for token in forbidden:
        assert token not in text, f"advanced topic '{token}' leaked into V0"


def test_every_skill_has_unit_and_exercise(curriculum):
    for skill in curriculum.skills.values():
        units = curriculum.units_for_skill(skill.id)
        assert units, f"{skill.id} has no units"
        assert any(curriculum.exercises_for_unit(u.id) for u in units), \
            f"{skill.id} has no exercises"


def test_four_axis_difficulty_present():
    for skill in SKILLS:
        assert set(skill.complexity.keys()) == {"knowledge", "execution", "reasoning", "transfer"}
        assert all(1 <= v <= 5 for v in skill.complexity.values())


def test_exercises_python_language_attribute():
    python_exercises = [e for e in EXERCISES if e.language is not None]
    assert python_exercises, "expected at least the code-writing exercises to be python"
    assert all(e.language == "python" for e in python_exercises)


def test_teach_theory_includes_example_and_pitfall(curriculum):
    """The 'actual study' layer: every teach unit's theory must carry a worked
    example and a classic pitfall, not just a bare definition."""
    for unit in curriculum.units.values():
        if unit.theory and unit.unit_type.value == "teach":
            assert "Example:" in unit.theory, f"unit {unit.id} theory lacks a worked example"
            assert "Watch out:" in unit.theory, f"unit {unit.id} theory lacks a pitfall note"


def test_session_plan_lists_upcoming_units(service):
    service.start_session()
    plan = service.session_plan()
    assert plan["items"], "a fresh learner must have planned units"
    assert plan["questions"] >= plan["units"]  # each unit carries at least one question
    assert plan["items"][0]["theory"] is True   # study section comes first
    assert plan["total_skills"] == 53


def test_evidence_requirements_are_feasible(curriculum):
    """Hardening item 2: every required evidence type must be demonstrable through
    an actual authored activity of the skill (no impossible skills)."""
    from dsa_tutor.domain.models import EvidenceType
    for skill in curriculum.skills.values():
        supported = {EvidenceType(e.role.value)
                     for u in curriculum.units_for_skill(skill.id)
                     for e in curriculum.exercises_for_unit(u.id)}
        missing = {t.value for t in skill.evidence_requirements} - {t.value for t in supported}
        assert not missing, f"skill {skill.id}: unsupported required evidence {missing}"


def test_problem_activities_declare_valid_capabilities(curriculum):
    """Hardening item 2: problem-scope activities must declare capabilities and all
    capabilities must be valid evidence types."""
    from dsa_tutor.domain.models import ActivityScope, EvidenceType
    valid = {t.value for t in EvidenceType}
    problems = [e for e in curriculum.exercises.values() if e.scope is ActivityScope.PROBLEM]
    assert problems, "expected at least one problem-scope activity"
    for e in problems:
        assert e.required_capabilities, f"problem {e.id} declares no capabilities"
        for cap in e.required_capabilities:
            assert cap.value in valid, f"problem {e.id} has invalid capability {cap}"
