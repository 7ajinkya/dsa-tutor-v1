"""MySQL repositories — production persistence (spec 05).

All writes that belong to one interaction happen inside a single transaction at the
service layer; these repositories provide the statement-level operations.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from ..domain.models import (
    Attempt, DailyPlan, EvidenceRecord, Learner, LearnerState, Pace,
    SessionEvent, SessionStatus, SkillAssessment, TutoringSession, utcnow,
)
from .db import Database


def _dt(value: datetime | None) -> str | None:
    """Aware UTC -> naive UTC for storage (MySQL DATETIME holds UTC at the boundary)."""
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc)
    return value.replace(tzinfo=None)


def _utc(value: datetime | None) -> datetime | None:
    """Naive UTC from DB -> aware UTC for the domain."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def _json(value) -> str:
    return json.dumps(value, default=str)


class MySQLStorage:
    def __init__(self, database: Database):
        self.db = database
        self.generated_exercises: dict[str, object] = {}

    def healthcheck(self) -> tuple[bool, str]:
        return self.db.healthcheck()

    # ------------------------------------------------ learners
    def get_or_create_learner(self, name: str) -> Learner:
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, name, created_at FROM users WHERE name=%s", (name,))
                row = cur.fetchone()
                if row:
                    return Learner(id=row["id"], name=row["name"], created_at=row["created_at"])
                cur.execute("INSERT INTO users (name, created_at) VALUES (%s, %s)", (name, utcnow()))
                new_id = cur.lastrowid
        return Learner(id=new_id, name=name)

    # ------------------------------------------------ sessions & events
    def create_session(self, session: TutoringSession) -> int:
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO sessions (learner_id, pace, status, started_at, ended_at, "
                    "budget_minutes, end_reason, last_unit_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (session.learner_id, Pace(session.pace).value,
                     SessionStatus(session.status).value,
                     session.started_at, _dt(session.ended_at), session.budget_minutes,
                     session.end_reason, session.last_unit_id))
                session_id = cur.lastrowid
        session.id = session_id
        return session_id

    def update_session(self, session: TutoringSession) -> None:
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE sessions SET status=%s, ended_at=%s, end_reason=%s, last_unit_id=%s "
                    "WHERE id=%s",
                    (SessionStatus(session.status).value, _dt(session.ended_at),
                     session.end_reason, session.last_unit_id, session.id))

    def get_session(self, session_id: int) -> TutoringSession | None:
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM sessions WHERE id=%s", (session_id,))
                row = cur.fetchone()
        return self._row_to_session(row) if row else None

    def latest_active_session(self, learner_id: int) -> TutoringSession | None:
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM sessions WHERE learner_id=%s AND status IN ('active','paused') "
                    "ORDER BY started_at DESC LIMIT 1", (learner_id,))
                row = cur.fetchone()
        return self._row_to_session(row) if row else None

    def latest_session(self, learner_id: int) -> TutoringSession | None:
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM sessions WHERE learner_id=%s ORDER BY started_at DESC LIMIT 1",
                    (learner_id,))
                row = cur.fetchone()
        return self._row_to_session(row) if row else None

    @staticmethod
    def _row_to_session(row: dict) -> TutoringSession:
        return TutoringSession(
            id=row["id"], learner_id=row["learner_id"], pace=Pace(row["pace"]),
            status=SessionStatus(row["status"]), started_at=_utc(row["started_at"]),
            ended_at=_utc(row["ended_at"]), budget_minutes=row["budget_minutes"],
            end_reason=row["end_reason"], last_unit_id=row["last_unit_id"])

    def append_event(self, event: SessionEvent) -> None:
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO session_events (session_id, seq, event_type, payload, created_at) "
                    "VALUES (%s,%s,%s,%s,%s)",
                    (event.session_id, event.seq, event.event_type.value,
                     _json(event.payload), event.created_at))
                event.id = cur.lastrowid

    def events_for_session(self, session_id: int) -> list[SessionEvent]:
        from ..domain.models import EventType
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM session_events WHERE session_id=%s ORDER BY seq", (session_id,))
                rows = cur.fetchall()
        return [SessionEvent(id=r["id"], session_id=r["session_id"], seq=r["seq"],
                             event_type=EventType(r["event_type"]),
                             payload=json.loads(r["payload"]), created_at=_utc(r["created_at"]))
                for r in rows]

    # ------------------------------------------------ attempts & evidence
    def save_attempt(self, attempt: Attempt) -> int:
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO attempts (session_id, learner_id, exercise_id, skill_id, response, "
                    "is_correct, score, evaluation, hints_used, independent_success, completed, "
                    "solution_revealed, ai_provider, ai_model, prompt_version, created_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (attempt.session_id, attempt.learner_id, attempt.exercise_id, attempt.skill_id,
                     attempt.response, attempt.is_correct, attempt.score, _json(attempt.evaluation),
                     attempt.hints_used, attempt.independent_success, attempt.completed,
                     attempt.solution_revealed, attempt.ai_provider, attempt.ai_model,
                     attempt.prompt_version, attempt.created_at))
                return cur.lastrowid

    def attempts_for_learner(self, learner_id: int) -> list[Attempt]:
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM attempts WHERE learner_id=%s ORDER BY created_at", (learner_id,))
                rows = cur.fetchall()
        attempts = []
        for r in rows:
            attempts.append(Attempt(
                id=r["id"], session_id=r["session_id"], learner_id=r["learner_id"],
                exercise_id=r["exercise_id"], skill_id=r["skill_id"], response=r["response"],
                is_correct=r["is_correct"], score=r["score"],
                evaluation=json.loads(r["evaluation"]), hints_used=r["hints_used"],
                independent_success=r["independent_success"], completed=r["completed"],
                solution_revealed=r["solution_revealed"], ai_provider=r["ai_provider"],
                ai_model=r["ai_model"], prompt_version=r["prompt_version"],
                created_at=_utc(r["created_at"])))
        return attempts

    def save_evidence(self, records: list[EvidenceRecord], learner_id: int) -> None:
        if not records:
            return
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                for r in records:
                    cur.execute(
                        "INSERT INTO assessment_evidence (learner_id, skill_id, attempt_id, "
                        "dimension, outcome, weight, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                        (learner_id, r.skill_id, r.attempt_id, r.dimension.value,
                         r.outcome.value, r.weight, r.created_at))

    def evidence_for_learner(self, learner_id: int) -> list[EvidenceRecord]:
        from ..domain.models import EvidenceOutcome, MasteryDimension
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT skill_id, dimension, outcome, weight, created_at, attempt_id "
                    "FROM assessment_evidence WHERE learner_id=%s ORDER BY created_at", (learner_id,))
                rows = cur.fetchall()
        return [EvidenceRecord(attempt_id=r["attempt_id"], skill_id=r["skill_id"],
                               dimension=MasteryDimension(r["dimension"]),
                               outcome=EvidenceOutcome(r["outcome"]),
                               weight=r["weight"], created_at=_utc(r["created_at"])) for r in rows]

    def upsert_assessment(self, assessment: SkillAssessment) -> None:
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO skill_assessments (learner_id, skill_id, knowledge, execution, "
                    "reasoning, transfer, evidence_count, independent_successes, confidence_avg, updated_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE knowledge=VALUES(knowledge), execution=VALUES(execution), "
                    "reasoning=VALUES(reasoning), transfer=VALUES(transfer), "
                    "evidence_count=VALUES(evidence_count), "
                    "independent_successes=VALUES(independent_successes), "
                    "confidence_avg=VALUES(confidence_avg), updated_at=VALUES(updated_at)",
                    (assessment.learner_id, assessment.skill_id, assessment.knowledge,
                     assessment.execution, assessment.reasoning, assessment.transfer,
                     assessment.evidence_count, assessment.independent_successes,
                     assessment.confidence_avg, utcnow()))

    def assessments_for_learner(self, learner_id: int) -> dict[str, SkillAssessment]:
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM skill_assessments WHERE learner_id=%s", (learner_id,))
                rows = cur.fetchall()
        return {r["skill_id"]: SkillAssessment(
            learner_id=r["learner_id"], skill_id=r["skill_id"], knowledge=r["knowledge"],
            execution=r["execution"], reasoning=r["reasoning"], transfer=r["transfer"],
            evidence_count=r["evidence_count"], independent_successes=r["independent_successes"],
            confidence_avg=r["confidence_avg"], updated_at=_utc(r["updated_at"])) for r in rows}

    # ------------------------------------------------ state & daily plan
    def save_state(self, state: LearnerState) -> None:
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO learner_state (learner_id, current_skill_id, current_unit_id, "
                    "current_exercise_id, pending_action, completed_units, unit_attempt_counts, "
                    "exercise_failures, hints_used_current, difficulty_shift, sessions_completed, updated_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE current_skill_id=VALUES(current_skill_id), "
                    "current_unit_id=VALUES(current_unit_id), "
                    "current_exercise_id=VALUES(current_exercise_id), "
                    "pending_action=VALUES(pending_action), completed_units=VALUES(completed_units), "
                    "unit_attempt_counts=VALUES(unit_attempt_counts), "
                    "exercise_failures=VALUES(exercise_failures), "
                    "hints_used_current=VALUES(hints_used_current), "
                    "difficulty_shift=VALUES(difficulty_shift), "
                    "sessions_completed=VALUES(sessions_completed), updated_at=VALUES(updated_at)",
                    (state.learner_id, state.current_skill_id, state.current_unit_id,
                     state.current_exercise_id, state.pending_action, _json(state.completed_unit_ids),
                     _json(state.unit_attempt_counts), _json(state.exercise_failures),
                     state.hints_used_current, state.difficultylevel_shift,
                     state.sessions_completed, utcnow()))

    def load_state(self, learner_id: int) -> LearnerState | None:
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM learner_state WHERE learner_id=%s", (learner_id,))
                row = cur.fetchone()
        if not row:
            return None
        return LearnerState(
            learner_id=row["learner_id"], current_skill_id=row["current_skill_id"],
            current_unit_id=row["current_unit_id"], current_exercise_id=row["current_exercise_id"],
            pending_action=row["pending_action"],
            completed_unit_ids=json.loads(row["completed_units"]),
            unit_attempt_counts=json.loads(row["unit_attempt_counts"]),
            exercise_failures=json.loads(row["exercise_failures"]),
            hints_used_current=row["hints_used_current"],
            difficultylevel_shift=row["difficulty_shift"],
            sessions_completed=row["sessions_completed"], updated_at=_utc(row["updated_at"]))

    def upsert_daily_plan(self, plan: DailyPlan) -> None:
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO daily_plans (learner_id, plan_date, target_units, completed_units, "
                    "status, updated_at) VALUES (%s,%s,%s,%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE target_units=VALUES(target_units), "
                    "completed_units=VALUES(completed_units), status=VALUES(status), "
                    "updated_at=VALUES(updated_at)",
                    (plan.learner_id, plan.plan_date, plan.target_units, plan.completed_units,
                     plan.status, utcnow()))

    def daily_plan(self, learner_id: int, plan_date: date) -> DailyPlan | None:
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM daily_plans WHERE learner_id=%s AND plan_date=%s",
                            (learner_id, plan_date))
                row = cur.fetchone()
        if not row:
            return None
        return DailyPlan(id=row["id"], learner_id=row["learner_id"], plan_date=row["plan_date"],
                         target_units=row["target_units"], completed_units=row["completed_units"],
                         status=row["status"], updated_at=_utc(row["updated_at"]))

    # ------------------------------------------------ atomic interaction record
    def record_interaction(self, attempt: Attempt, evidence: list[EvidenceRecord],
                           assessment: SkillAssessment, state: LearnerState,
                           events: list[SessionEvent]) -> int:
        """One coherent transaction: attempt -> evaluation -> evidence -> assessment ->
        state -> events. A failure anywhere rolls the whole interaction back (spec 06 §7)."""
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO attempts (session_id, learner_id, exercise_id, skill_id, response, "
                    "is_correct, score, evaluation, hints_used, max_assistance_level, "
                    "independent_success, completed, "
                    "solution_revealed, ai_provider, ai_model, prompt_version, created_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (attempt.session_id, attempt.learner_id, attempt.exercise_id, attempt.skill_id,
                     attempt.response, attempt.is_correct, attempt.score, _json(attempt.evaluation),
                     attempt.hints_used, attempt.max_assistance_level,
                     attempt.independent_success, attempt.completed,
                     attempt.solution_revealed, attempt.ai_provider, attempt.ai_model,
                     attempt.prompt_version, attempt.created_at))
                attempt_id = cur.lastrowid
                for r in evidence:
                    r.attempt_id = attempt_id
                    cur.execute(
                        "INSERT INTO assessment_evidence (learner_id, skill_id, attempt_id, "
                        "dimension, evidence_type, assistance_level, outcome, weight, created_at) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (attempt.learner_id, r.skill_id, attempt_id, r.dimension.value,
                         r.evidence_type.value, r.assistance_level,
                         r.outcome.value, r.weight, r.created_at))
                cur.execute(
                    "INSERT INTO skill_assessments (learner_id, skill_id, knowledge, execution, "
                    "reasoning, transfer, evidence_count, independent_successes, confidence_avg, updated_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE knowledge=VALUES(knowledge), execution=VALUES(execution), "
                    "reasoning=VALUES(reasoning), transfer=VALUES(transfer), "
                    "evidence_count=VALUES(evidence_count), "
                    "independent_successes=VALUES(independent_successes), "
                    "confidence_avg=VALUES(confidence_avg), updated_at=VALUES(updated_at)",
                    (assessment.learner_id, assessment.skill_id, assessment.knowledge,
                     assessment.execution, assessment.reasoning, assessment.transfer,
                     assessment.evidence_count, assessment.independent_successes,
                     assessment.confidence_avg, utcnow()))
                cur.execute(
                    "INSERT INTO learner_state (learner_id, current_skill_id, current_unit_id, "
                    "current_exercise_id, pending_action, completed_units, unit_attempt_counts, "
                    "exercise_failures, hints_used_current, difficulty_shift, sessions_completed, updated_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE current_skill_id=VALUES(current_skill_id), "
                    "current_unit_id=VALUES(current_unit_id), "
                    "current_exercise_id=VALUES(current_exercise_id), "
                    "pending_action=VALUES(pending_action), completed_units=VALUES(completed_units), "
                    "unit_attempt_counts=VALUES(unit_attempt_counts), "
                    "exercise_failures=VALUES(exercise_failures), "
                    "hints_used_current=VALUES(hints_used_current), "
                    "difficulty_shift=VALUES(difficulty_shift), "
                    "sessions_completed=VALUES(sessions_completed), updated_at=VALUES(updated_at)",
                    (state.learner_id, state.current_skill_id, state.current_unit_id,
                     state.current_exercise_id, state.pending_action, _json(state.completed_unit_ids),
                     _json(state.unit_attempt_counts), _json(state.exercise_failures),
                     state.hints_used_current, state.difficultylevel_shift,
                     state.sessions_completed, utcnow()))
                for event in events:
                    cur.execute(
                        "INSERT INTO session_events (session_id, seq, event_type, payload, created_at) "
                        "VALUES (%s,%s,%s,%s,%s)",
                        (event.session_id, event.seq, event.event_type.value,
                         _json(event.payload), event.created_at))
        return attempt_id

    def ensure_exercise(self, exercise) -> None:
        """Persist a generated (AI-source) exercise so attempts satisfy the FK."""
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT IGNORE INTO exercises (id, unit_id, skill_id, ordering, interaction_type, prompt, "
                    "payload, difficulty, language, hint_ladder, max_hints, requires_ai, source, "
                    "prompt_version, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (exercise.id, exercise.unit_id, exercise.skill_id, exercise.ordering,
                     exercise.interaction_type.value, exercise.prompt,
                     _json(exercise.payload), _json(exercise.difficulty), exercise.language,
                     _json(exercise.hint_ladder), exercise.max_hints, exercise.requires_ai,
                     "ai", exercise.prompt_version, utcnow()))
        self.generated_exercises[exercise.id] = exercise

    def get_exercise(self, exercise_id: str):
        return self.generated_exercises.get(exercise_id)

    # ------------------------------------------------ AI interaction / hint logs
    def log_ai_interaction(self, learner_id: int, session_id: int | None, operation: str,
                           provider: str, model: str | None, prompt_version: str | None,
                           request: dict | None, response: dict | None,
                           validation_ok: bool, latency_ms: int | None,
                           keep_raw: bool = False) -> None:
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO ai_interactions (learner_id, session_id, operation, provider, "
                    "model, prompt_version, request_json, response_json, validation_ok, latency_ms, created_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (learner_id, session_id, operation, provider, model, prompt_version,
                     _json(request) if (keep_raw and request) else None,
                     _json(response) if (keep_raw and response) else None,
                     validation_ok, latency_ms, utcnow()))

    def record_hint_event(self, learner_id: int, session_id: int | None, attempt_id: int | None,
                          exercise_id: str, level: int, kind: str, text: str,
                          provider: str) -> None:
        with self.db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO hint_events (attempt_id, learner_id, session_id, exercise_id, "
                    "level, kind, text, provider, delivered_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (attempt_id, learner_id, session_id, exercise_id, level, kind,
                     text[:2000], provider, utcnow()))
