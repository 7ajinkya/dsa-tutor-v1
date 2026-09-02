"""Simulation runner + regression scenarios (review RC-21, amendment 8).

Run:  python -m simulation.run
Writes per-profile progression traces to exports/sim_<profile>.md and asserts
engine sanity: prerequisites never skipped, remediation where expected, and
NON-MONOTONIC mastery for the regression learner (proficient -> poor performance
must drop the state and schedule refresh practice).
"""
from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conftest import correct_answer_for  # noqa: E402
from dsa_tutor.ai.schemas import HintResult  # noqa: E402
from dsa_tutor.app.service import TutorService  # noqa: E402
from dsa_tutor.config import AIConfig, AppConfig  # noqa: E402
from dsa_tutor.domain import mastery  # noqa: E402
from dsa_tutor.domain.engine import EngineSnapshot, LearningEngine  # noqa: E402
from dsa_tutor.domain.models import (  # noqa: E402
    EvidenceOutcome, EvidenceRecord, EvidenceType, LearnerState,
    MasteryDimension, utcnow,
)
from dsa_tutor.persistence.memory_repositories import MemoryStorage  # noqa: E402

from simulation.learner_profiles import PROFILES, run_profile  # noqa: E402


def hermetic_config():
    return AppConfig(ai=AIConfig(provider="builtin"))


def seed_proficient(service, skill_id):
    """Regression learner G: previously demonstrated PROFICIENT-level evidence (recent)."""
    skill = service.curriculum.skill(skill_id)
    when = utcnow() - timedelta(days=5)
    for etype in skill.evidence_requirements:
        for _ in range(2):
            service.storage.save_evidence([EvidenceRecord(
                attempt_id=None, skill_id=skill_id,
                dimension=MasteryDimension.KNOWLEDGE, evidence_type=etype,
                outcome=EvidenceOutcome.INDEPENDENT_SUCCESS, weight=1.0,
                created_at=when)], service.learner.id)


def regression_learner_g():
    """Was PROFICIENT, now performs poorly ON THAT SKILL: mastery must transition DOWN
    (non-monotonic), and the engine must schedule refresh practice (amendment 8)."""
    service = TutorService(MemoryStorage(), hermetic_config())
    seed_proficient(service, "graph_definition")
    engine = LearningEngine(service.curriculum, service.config.engine)
    evidence = {"graph_definition": list(
        [r for r in service.storage.evidence_for_learner(service.learner.id)
         if r.skill_id == "graph_definition"])}
    state_before = mastery.derive_state(
        evidence["graph_definition"],
        set(service.curriculum.skill("graph_definition").evidence_requirements), utcnow())
    assert state_before is mastery.MasteryState.PROFICIENT, \
        f"seeded evidence should be PROFICIENT, got {state_before.value}"

    exercise = next(e for e in service.curriculum.exercises.values()
                    if e.skill_id == "graph_definition" and e.interaction_type.value == "mcq")
    # the previously-proficient learner now fails the same check
    decision = engine.decide_after_attempt(
        EngineSnapshot(state=LearnerState(learner_id=service.learner.id), assessments={},
                       evidence=evidence, session=None, remaining_minutes=20.0),
        exercise, score=0.0, is_correct=False, hints_used=0, solution_revealed=False)
    evidence["graph_definition"].append(EvidenceRecord(
        attempt_id=None, skill_id="graph_definition", dimension=MasteryDimension.KNOWLEDGE,
        evidence_type=EvidenceType.RECOGNITION, outcome=EvidenceOutcome.FAILED,
        weight=1.0, created_at=utcnow()))
    state_after = mastery.derive_state(
        evidence["graph_definition"],
        set(service.curriculum.skill("graph_definition").evidence_requirements), utcnow())
    assert state_after is mastery.MasteryState.DEVELOPING, \
        f"fresh poor performance must drop mastery (got {state_after.value})"
    # engine schedules refresh practice on the degraded skill
    refreshed = engine.select_next(EngineSnapshot(
        state=LearnerState(learner_id=service.learner.id), assessments={},
        evidence=evidence, session=None, remaining_minutes=20.0))
    assert refreshed.skill_id == "graph_definition", \
        "refresh practice must be scheduled on the degraded skill"
    return state_before, state_after


def main():
    out_dir = Path("exports")
    out_dir.mkdir(exist_ok=True)
    report = []
    for name, behavior in PROFILES.items():
        service, trace = run_profile(behavior)
        lines = [f"# Simulation trace: {name}", ""]
        for ex_id, skill, action, correct in trace:
            lines.append(f"- {ex_id} ({skill}) decision={action} correct={correct}")
        (out_dir / f"sim_{name}.md").write_text("\n".join(lines), encoding="utf-8")
        report.append((name, len(trace)))
        print(f"{name}: {len(trace)} interactions traced -> exports/sim_{name}.md")

    for name, _ in report:
        trace_lines = (out_dir / f"sim_{name}.md").read_text(encoding="utf-8")
        assert "graph_definition" in trace_lines

    before, after = regression_learner_g()
    print(f"regression learner G: {before.value} -> {after.value} (non-monotonic mastery OK)")
    (out_dir / "sim_G_regression.md").write_text(
        f"# Regression learner G\n\nBefore poor performance: {before.value}\n"
        f"After poor performance: {after.value}\n\n"
        "Policy: mastery is derived from recent evidence predicates and is deliberately\n"
        "NON-MONOTONIC. Historical raw evidence is preserved; current readiness drops and\n"
        "refresh practice is scheduled by normal engine selection.\n", encoding="utf-8")
    print("regression scenario written -> exports/sim_G_regression.md")


if __name__ == "__main__":
    main()
