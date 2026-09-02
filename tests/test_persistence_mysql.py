"""MySQL persistence/integration tests — run only when the configured DB is reachable.
Verifies spec 07 §3 Persistence: attempts/events persist, state survives restart,
resume works, transactions keep learner state coherent."""
import pytest

from conftest import correct_answer_for, drive_to_exercise
from dsa_tutor.app.service import TutorService
from dsa_tutor.config import load_config
from dsa_tutor.persistence.db import Database
from dsa_tutor.persistence.repositories import MySQLStorage
from dsa_tutor.persistence.seed import seed_curriculum


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


@pytest.fixture()
def clean_service(mysql_storage):
    service = TutorService(mysql_storage, load_config())
    # wipe this learner's progress data for a deterministic run
    with mysql_storage.db.transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM assessment_evidence WHERE learner_id=%s", (service.learner.id,))
            cur.execute("DELETE FROM attempts WHERE learner_id=%s", (service.learner.id,))
            cur.execute("DELETE FROM session_events WHERE session_id IN "
                        "(SELECT id FROM sessions WHERE learner_id=%s)", (service.learner.id,))
            cur.execute("DELETE FROM sessions WHERE learner_id=%s", (service.learner.id,))
            cur.execute("DELETE FROM skill_assessments WHERE learner_id=%s", (service.learner.id,))
            cur.execute("DELETE FROM learner_state WHERE learner_id=%s", (service.learner.id,))
            cur.execute("DELETE FROM daily_plans WHERE learner_id=%s", (service.learner.id,))
    return service


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
    service2 = TutorService(clean_service.storage, load_config())
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
