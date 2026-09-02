import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from dsa_tutor.app.service import TutorService, build_curriculum
from dsa_tutor.config import AppConfig
from dsa_tutor.persistence.memory_repositories import MemoryStorage


@pytest.fixture(scope="session")
def curriculum():
    return build_curriculum()


@pytest.fixture()
def config():
    """Hermetic test config: builtin AI provider regardless of the user's .env,
    so tests never make real LLM/network calls (spec 06 §11: AI must be mockable)."""
    from dsa_tutor.config import AIConfig
    cfg = AppConfig()
    return AppConfig(ai=AIConfig(provider="builtin"))


@pytest.fixture()
def service(config):
    """Fresh in-memory service per test (no MySQL, no external AI)."""
    storage = MemoryStorage()
    return TutorService(storage, config)


def correct_answer_for(exercise):
    """Deterministically derive a fully-correct response for any curated exercise."""
    p = exercise.payload
    t = exercise.interaction_type.value
    if t == "mcq":
        return p["answer_id"]
    if t in {"output_prediction", "code_tracing"}:
        return p["expected_output"].replace("\n", " | ")
    if t == "complexity_question":
        return p["acceptable"][0]
    if t == "code_writing":
        return p["solution"]
    if t == "graph_construction":
        return ", ".join(f"{u}-{v}" for u, v in p["expected_edges"])
    if t == "free_form":
        parts = []
        for point in p.get("reference_points", []):
            parts.extend(point.get("keywords", [])[:1])
        return "This is right because " + ", ".join(parts) + "."
    return "answer"


def mcq_for(curriculum, skill_id):
    return next(e for e in curriculum.exercises.values()
                if e.skill_id == skill_id and e.interaction_type.value == "mcq")


def exercise_by(curriculum, skill_id, itype):
    return next(e for e in curriculum.exercises.values()
                if e.skill_id == skill_id and e.interaction_type.value == itype)


def drive_to_exercise(service, target_type=None):
    """Advance the session until an exercise of the wanted type is current (or None)."""
    view = service.start_session()
    for _ in range(60):
        if view.kind == "info":
            return view, None
        if view.kind == "ended":
            return view, None
        if view.kind == "theory":
            view = service.mark_theory_seen()
            continue
        if view.kind == "exercise":
            if target_type is None or view.exercise.interaction_type.value == target_type:
                return view, view.exercise
            view = service.submit_response(correct_answer_for(view.exercise))
            continue
    raise AssertionError("could not reach an exercise; loop guard tripped")
