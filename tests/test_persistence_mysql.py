"""MySQL persistence/integration tests — run only when the configured DB is reachable.
Verifies spec 07 §3 Persistence: attempts/events persist, state survives restart,
resume works, transactions keep learner state coherent, and mastery evidence
(including its evidence_type) round-trips so progression continues after a restart.

All tests run against the dedicated TEST_LEARNER — the real application learner
('local_learner') and their progress are never touched."""
import pytest

from conftest import correct_answer_for, drive_to_exercise
from dsa_tutor.app.service import TutorService
from dsa_tutor.config import load_config
from dsa_tutor.domain import mastery
from dsa_tutor.domain.models import (
    EvidenceOutcome, EvidenceRecord, EvidenceType, MasteryDimension, Pace, utcnow,
)
from dsa_tutor.persistence.db import Database
from dsa_tutor.persistence.repositories import MySQLStorage
from dsa_tutor.persistence.seed import seed_curriculum

TEST_LEARNER = "pytest_learner"   # dedicated identity: tests never wipe real progress


def _mysql_available():
    try:
        config = load_config()
        ok, _ = Database(config.database).healthcheck()
        return config if ok else None
    except Exception:  # noqa: BLE001
        return None


CONFIG = _mysql_available()
pytestmark = pytest.mark.skipif(CONFIG is None,
                                reason="MySQL not reachable — set .env credentials to enable")


@pytest.fixture(scope="module")
def mysql_storage():
    database = Database(CONFIG.database)
    from pathlib import Path
    schema_file = Path(__file__).resolve().parent.parent / "dsa_tutor" / "persistence" / "schema.sql"
    database.install_schema(schema_file.read_text(encoding="utf-8"))
    seed_curriculum(database)
    return MySQLStorage(database)


def _wipe_learner(storage, learner_id):
    with storage.db.transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM assessment_evidence WHERE learner_id=%s", (learner_id,))
            cur.execute("DELETE FROM attempts WHERE learner_id=%s", (learner_id,))
            cur.execute("DELETE FROM session_events WHERE session_id IN "
                        "(SELECT id FROM sessions WHERE learner_id=%s)", (learner_id,))
            cur.execute("DELETE FROM sessions WHERE learner_id=%s", (learner_id,))
            cur.execute("DELETE FROM skill_assessments WHERE learner_id=%s", (learner_id,))
            cur.execute("DELETE FROM learner_state WHERE learner_id=%s", (learner_id,))
            cur.execute("DELETE FROM daily_plans WHERE learner_id=%s", (learner_id,))


@pytest.fixture()
def clean_service(mysql_storage):
    """A deterministic run for the TEST_LEARNER (real learner data untouched)."""
    service = TutorService(mysql_storage, load_config(), learner_name=TEST_LEARNER)
    _wipe_learner(mysql_storage, service.learner.id)
    return service


def restarted_service(learner_name=TEST_LEARNER):
    """Fresh Database + storage + service: the process-restart simulation. No in-memory
    caches (generated exercises, session handle) are shared with the prior instance."""
    database = Database(CONFIG.database)
    return TutorService(MySQLStorage(database), load_config(), learner_name=learner_name)


def test_health(mysql_storage):
    ok, detail = mysql_storage.healthcheck()
    assert ok, detail


def test_attempt_and_event_persistence(clean_service, mysql_storage):
    view, _ = drive_to_exercise(clean_service)
    clean_service.mark_theory_seen()
    view = clean_service.start_session(resume=True)
    clean_service.submit_response(correct_answer_for(view.exercise))
    learner_id = clean_service.learner.id
    attempts = mysql_attempts(mysql_storage, learner_id)
    assert len(attempts) == 1
    assert attempts[0]["evaluation_json"] is not None
    events = mysql_events(mysql_storage, clean_service.session.id)
    assert any(e["event_type"] == "ANSWER_EVALUATED" for e in events)
    assert any(e["event_type"] == "QUESTION_PRESENTED" for e in events)


def test_state_survives_restart_and_resume(clean_service):
    view, _ = drive_to_exercise(clean_service)
    current = view.exercise.id
    clean_service.stop_session("integration stop")
    service2 = TutorService(clean_service.storage, load_config(), learner_name=TEST_LEARNER)
    resumed = service2.start_session(resume=True)
    assert resumed.kind == "exercise"
    assert resumed.exercise.id == current


def test_transaction_rollback_keeps_state_coherent(mysql_storage, clean_service):
    import pymysql
    view, _ = drive_to_exercise(clean_service)
    learner_id = clean_service.learner.id
    before_attempts = len(mysql_attempts(mysql_storage, learner_id))
    # force a failure inside the interaction record: corrupt skill_id breaks the FK
    try:
        from dsa_tutor.domain.models import Attempt, LearnerState, SkillAssessment, utcnow
        bad_attempt = Attempt(id=None, session_id=clean_service.session.id, learner_id=learner_id,
                              exercise_id="e001_graph_definition", skill_id="not_a_skill",
                              response="x", is_correct=True, score=1.0, evaluation={})
        assessment = SkillAssessment(learner_id=learner_id, skill_id="not_a_skill")
        state = LearnerState(learner_id=learner_id)
        mysql_storage.record_interaction(bad_attempt, [], assessment, state, [])
        raise AssertionError("expected FK violation")
    except Exception:  # noqa: BLE001 - expected
        pass
    after_attempts = len(mysql_attempts(mysql_storage, learner_id))
    assert after_attempts == before_attempts, "rollback must leave no partial attempt row"


def mysql_attempts(storage, learner_id):
    with storage.db.transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, evaluation FROM attempts WHERE learner_id=%s", (learner_id,))
            rows = cur.fetchall()
    return [{"id": r["id"], "evaluation_json": r["evaluation"]} for r in rows]


def mysql_events(storage, session_id):
    with storage.db.transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT event_type FROM session_events WHERE session_id=%s", (session_id,))
            return [{"event_type": r["event_type"]} for r in cur.fetchall()]


# ------------------------------------------------------------------ restart persistence
FRESH_LEARNER = "pytest_fresh_learner"


def test_fresh_learner_initialization(mysql_storage):
    """Test 1: a brand-new learner can be initialized and starts at the first skill."""
    service = TutorService(mysql_storage, load_config(), learner_name=FRESH_LEARNER)
    _wipe_learner(mysql_storage, service.learner.id)
    assert service.learner.id is not None
    assert service.storage.load_state(service.learner.id) is None
    report = service.progress_report()
    assert all(row["state"] == "NOT_SEEN" for row in report["skills"])
    view = service.start_session(pace=Pace.NORMAL)
    assert view.kind == "theory"          # a fresh learner is taught, not tested
    assert view.unit.skill_id == "graph_definition"


def test_state_attempts_evidence_survive_restart(clean_service):
    """Tests 2/3/4: one learner interaction persists coherently and is fully restored
    by a fresh service instance (process-restart simulation)."""
    view, _ = drive_to_exercise(clean_service)
    exercise_id = view.exercise.id
    clean_service.submit_response(correct_answer_for(view.exercise), idempotency_key="restart-k1")
    session_id = clean_service.session.id
    learner_id = clean_service.learner.id

    fresh = restarted_service()          # new Database + storage + service: a restart

    # --- learner state
    state = fresh.storage.load_state(learner_id)
    assert state is not None
    assert f"theory:{view.exercise.unit_id}" in state.completed_unit_ids
    assert state.unit_attempt_counts.get(exercise_id) == 1
    assert state.current_exercise_id     # the flow advanced to a next activity

    # --- attempt history (incl. idempotency identity)
    attempts = fresh.storage.attempts_for_learner(learner_id)
    assert len(attempts) == 1
    assert attempts[0].exercise_id == exercise_id
    assert attempts[0].is_correct is True
    assert attempts[0].evaluation.get("provider")
    assert attempts[0].idempotency_key == "restart-k1"
    replay = fresh.storage.find_attempt_by_idempotency_key(learner_id, session_id, "restart-k1")
    assert replay is not None and replay.id == attempts[0].id

    # --- evidence drives mastery: type + outcome must survive the restart
    records = fresh.storage.evidence_for_learner(learner_id)
    assert records, "evidence lost across restart"
    assert {r.evidence_type for r in records} == {EvidenceType.RECOGNITION}
    assert {r.outcome for r in records} == {EvidenceOutcome.INDEPENDENT_SUCCESS}
    skill = fresh.curriculum.skill("graph_definition")
    derived = mastery.derive_state(records, set(skill.evidence_requirements), utcnow())
    assert derived in {mastery.MasteryState.PRACTICED, mastery.MasteryState.PROFICIENT,
                       mastery.MasteryState.INDEPENDENT}


def test_progression_continues_from_restored_position(clean_service):
    """Test 5: after a restart the engine continues from the learner's actual position
    (next skill), not from the first skill/activity."""
    view, _ = drive_to_exercise(clean_service)
    clean_service.submit_response(correct_answer_for(view.exercise))   # completes the skill

    fresh = restarted_service()
    resumed = fresh.start_session(resume=True)
    # the learner is now positioned in the FOLLOWING skill's teach unit — exactly where
    # the live engine left them; certainly not re-served graph_definition's first check
    assert resumed.kind in {"theory", "exercise"}
    if resumed.kind == "theory":
        assert resumed.unit.skill_id != "graph_definition"
    else:
        assert resumed.exercise.skill_id != "graph_definition"


def test_pending_theory_survives_restart(clean_service):
    """Test 6: closing the application while a theory turn is pending must not skip the
    study text on resume."""
    view = clean_service.start_session(pace=Pace.NORMAL)
    assert view.kind == "theory"
    pending_unit = view.unit.id
    clean_service.stop_session("closed while studying")

    fresh = restarted_service()
    resumed = fresh.start_session(resume=True)
    assert resumed.kind == "theory", "restart must not silently skip pending theory"
    assert resumed.unit.id == pending_unit
    exercise_view = fresh.mark_theory_seen()
    assert exercise_view.kind == "exercise"
    assert exercise_view.exercise.unit_id == pending_unit


def test_generated_exercise_survives_restart(clean_service):
    """A pause on an AI-generated remediation activity must resume onto the same
    activity after a restart (it is restored from the exercises table)."""
    view, _ = drive_to_exercise(clean_service)
    clean_service.submit_response("z")    # wrong on purpose -> struggle ladder -> remediation
    current = clean_service._state().current_exercise_id
    assert current.startswith("rem_"), "expected a generated remediation activity"
    clean_service.stop_session("paused on remediation")

    fresh = restarted_service()
    resumed = fresh.start_session(resume=True)
    assert resumed.kind == "exercise"
    assert resumed.exercise.id == current
    assert resumed.exercise.interaction_type.value in {"mcq", "free_form"}


def test_evidence_type_roundtrip_all_types(mysql_storage, clean_service):
    """Repository-level regression: evidence_type and assistance_level round-trip.
    Before the fix every restored record degraded to RECOGNITION/L0, collapsing
    mastery for every skill requiring TRACE/EXPLANATION/IMPLEMENTATION/etc."""
    learner_id = clean_service.learner.id
    now = utcnow()
    stored = [
        EvidenceRecord(attempt_id=None, skill_id="degree", dimension=MasteryDimension.KNOWLEDGE,
                       evidence_type=EvidenceType.CONSTRUCTION,
                       outcome=EvidenceOutcome.INDEPENDENT_SUCCESS, weight=1.3,
                       created_at=now),
        EvidenceRecord(attempt_id=None, skill_id="visited_state", dimension=MasteryDimension.REASONING,
                       evidence_type=EvidenceType.EXPLANATION,
                       outcome=EvidenceOutcome.ASSISTED_SUCCESS, weight=1.0,
                       assistance_level=2, created_at=now),
        EvidenceRecord(attempt_id=None, skill_id="bfs_manual_tracing", dimension=MasteryDimension.EXECUTION,
                       evidence_type=EvidenceType.TRACE,
                       outcome=EvidenceOutcome.FAILED, weight=0.8, created_at=now),
    ]
    mysql_storage.save_evidence(stored, learner_id)
    fresh = restarted_service().storage
    restored = {(r.skill_id, r.evidence_type, r.outcome, r.assistance_level)
                for r in fresh.evidence_for_learner(learner_id)}
    assert (("degree", EvidenceType.CONSTRUCTION, EvidenceOutcome.INDEPENDENT_SUCCESS, 0)
            in restored)
    assert (("visited_state", EvidenceType.EXPLANATION, EvidenceOutcome.ASSISTED_SUCCESS, 2)
            in restored)
    assert (("bfs_manual_tracing", EvidenceType.TRACE, EvidenceOutcome.FAILED, 0)
            in restored)
