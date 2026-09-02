"""Slice 1B: the thin HTTP adapter (design doc docs/V1_SLICE_1_API_BOUNDARY_DESIGN.md v1.2).

Transport + projection only. Every route delegates to TutorService; every response is the
universal turn envelope from §5.1; every error uses the §4.0 envelope. No pedagogical
decisions are made here (invariant 1/2), and grading secrets never leave the server (invariant 7).
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone

from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dsa_tutor.api.errors import ApiError, register_exception_handlers
from dsa_tutor.api.projection import (project_result_from_attempt, project_session,
                                      project_turn)
from dsa_tutor.api.targeting import ensure_session_target, ensure_snapshot_target
from dsa_tutor.config import PROJECT_ROOT, load_config
from dsa_tutor.domain.models import Pace

DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


class StartRequest(BaseModel):
    pace: str = "normal"


class AnswerRequest(BaseModel):
    answer: str


class StopRequest(BaseModel):
    reason: str | None = None


class ConfidenceRequest(BaseModel):
    skill_id: str
    rating: int


def _build_service_from_config(config):
    """MySQL path for the running application (design §10) — same gates as the CLI."""
    from dsa_tutor.logging_conf import setup_logging
    from dsa_tutor.persistence.db import Database
    from dsa_tutor.persistence.repositories import MySQLStorage
    setup_logging(config.log_level, str(PROJECT_ROOT / config.log_dir))
    database = Database(config.database)
    ok, detail = database.healthcheck()
    if not ok:
        raise SystemExit(f"MySQL unavailable: {detail} \u2014 run 'python -m dsa_tutor setup-db' "
                         "after configuring .env, or start the API with --offline for a non-persistent demo.")
    report = database.schema_report()
    if not report["complete"]:
        raise SystemExit(f"MySQL schema incomplete: {report['missing_tables'] + report['missing_columns']} "
                         "\u2014 run 'python -m dsa_tutor setup-db'.")
    return __import__("dsa_tutor.app.service", fromlist=["TutorService"]).TutorService(
        MySQLStorage(database), config)


def create_app(service=None, config=None, cors_origins: list[str] | None = None) -> FastAPI:
    config = config or load_config()
    if service is None:
        service = _build_service_from_config(config)
    if cors_origins is None:
        raw = os.getenv("API_CORS_ORIGINS", ",".join(DEFAULT_CORS_ORIGINS))
        cors_origins = [o.strip() for o in raw.split(",") if o.strip()]

    app = FastAPI(title="DSA Tutor API", version="1.0.0",
                  docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,       # explicit dev origins only — no wildcard (design §9.2)
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.state.service = service
    app.state.config = config
    app.state.cors_origins = cors_origins

    # ------------------------------------------------------------- home / learner
    @app.get("/api/v1/home")
    def home():
        """Read-only composition (design §4.11): daily + plan preview + progress + resume."""
        today = date.today()
        plan_row = service.storage.daily_plan(service.learner.id, today)
        daily = {"target_units": plan_row.target_units if plan_row else config.engine.daily_target_units,
                 "completed_units": plan_row.completed_units if plan_row else 0,
                 "status": plan_row.status if plan_row else "active"}
        plan = service.session_plan()
        latest = service.storage.latest_active_session(service.learner.id)
        resume = {"available": latest is not None,
                  "session_id": latest.id if latest else None,
                  "pace": latest.pace.value if latest else None}
        return {"daily": daily, "plan": plan,
                "progress_summary": {"mastered": plan["mastered"], "total_skills": plan["total_skills"]},
                "resume": resume}

    @app.get("/api/v1/learner/progress")
    def learner_progress():
        """Qualitative mastery states per skill (design §4.10) — no numeric percentages."""
        return service.progress_report()

    # ------------------------------------------------------------- sessions
    @app.post("/api/v1/sessions", status_code=201)
    def start_session(body: StartRequest | None = None):
        pace_value = (body.pace if body else "normal") or "normal"
        if pace_value not in {p.value for p in Pace}:
            raise ApiError(400, "INVALID_PACE",
                           f"pace must be one of slow|normal|fast, got '{pace_value}'.")
        latest = service.storage.latest_active_session(service.learner.id)
        if latest is not None:
            raise ApiError(409, "SESSION_ALREADY_ACTIVE",
                           f"Session {latest.id} is {latest.status.value}. Resume it or stop it first.",
                           session_id=latest.id,
                           resume=f"/api/v1/sessions/{latest.id}/resume")
        view = service.start_session(pace=Pace(pace_value))
        return {"turn": project_turn(view, service=service),
                "session": project_session(service.session, remaining_minutes=view.remaining_minutes,
                                           daily=view.daily)}

    @app.get("/api/v1/sessions/{session_id}")
    def get_session(session_id: int):
        """Read-only snapshot (design §4.2): zero writes, served by session_snapshot()."""
        ensure_snapshot_target(service, session_id)
        view = service.session_snapshot()
        return {"session": project_session(service.session, remaining_minutes=view.remaining_minutes,
                                           daily=view.daily),
                "turn": project_turn(view, service=service),
                "plan": service.session_plan()}

    @app.post("/api/v1/sessions/{session_id}/resume")
    def resume_session(session_id: int):
        """Retry-safe resume (design §4.3, review R4): paused -> active once; already-active -> no-op."""
        session = service.storage.get_session(session_id)
        if session is None:
            raise ApiError(404, "SESSION_NOT_FOUND", f"No session with id {session_id}.")
        status = session.status.value
        if status == "active":
            latest = service.storage.latest_active_session(service.learner.id)
            if latest is None or latest.id != session_id:
                raise ApiError(409, "SESSION_MISMATCH",
                               f"Session {session_id} is not the latest active/paused session.")
            view = service.session_snapshot()  # read-only no-op: zero writes
            return {"turn": project_turn(view, service=service),
                    "session": project_session(service.session, remaining_minutes=view.remaining_minutes,
                                               daily=view.daily),
                    "resumed": False}
        if status in {"completed", "abandoned"}:
            raise ApiError(409, "SESSION_NOT_ACTIVE",
                           f"Session {session_id} is {status} and cannot be resumed.")
        latest = service.storage.latest_active_session(service.learner.id)
        if latest is not None and latest.id != session_id:
            if latest.status.value == "active":
                raise ApiError(409, "ANOTHER_SESSION_ACTIVE",
                               f"Session {latest.id} is active; stop it before resuming session {session_id}.")
            raise ApiError(409, "SESSION_MISMATCH",
                           f"Session {latest.id} is the latest paused session; resume targets it.")
        view = service.start_session(resume=True)
        if service.session is None or service.session.id != session_id:
            raise ApiError(409, "SESSION_MISMATCH",
                           f"Resume produced session {getattr(service.session, 'id', None)}, not {session_id}.")
        return {"turn": project_turn(view, service=service),
                "session": project_session(service.session, remaining_minutes=view.remaining_minutes,
                                           daily=view.daily),
                "resumed": True}

    @app.post("/api/v1/sessions/{session_id}/stop")
    def stop_session(session_id: int, body: StopRequest | None = None):
        """Retry-safe stop (design §4.4, review R5): active -> paused once; already paused -> no-op."""
        session = service.storage.get_session(session_id)
        if session is None:
            raise ApiError(404, "SESSION_NOT_FOUND", f"No session with id {session_id}.")
        status = session.status.value
        if status == "paused":
            return {"session": project_session(session),
                    "notice": {"kind": "already_paused", "text": "Session is already paused."}}
        if status in {"completed", "abandoned"}:
            raise ApiError(409, "SESSION_NOT_ACTIVE",
                           f"Session {session_id} is {status}.")
        ensure_session_target(service, session_id, require_active=True)
        reason = (body.reason if body else None) or "learner requested stop"
        view = service.stop_session(reason[:200])
        row = service.storage.get_session(session_id)
        return {"session": project_session(row),
                "turn": project_turn(view, service=service) if view.kind == "ended" else None,
                "notice": {"kind": "stopped", "text": view.extra.get("message", "")}}

    # ------------------------------------------------------------- theory + activities
    @app.post("/api/v1/sessions/{session_id}/theory-seen")
    def theory_seen(session_id: int):
        """Retry-safe theory completion (design §4.12, review R1)."""
        ensure_session_target(service, session_id, require_active=True)
        state = service.storage.load_state(service.learner.id)
        if state is None or state.current_unit_id is None:
            raise ApiError(409, "SESSION_NOT_ACTIVE", "No current unit to mark theory for.")
        seen = f"theory:{state.current_unit_id}" in state.completed_unit_ids
        if seen:
            view = service.session_snapshot()  # idempotent no-op: authoritative current turn
            return {"turn": project_turn(view, service=service), "retried_no_op": True}
        unit = service.curriculum.units.get(state.current_unit_id)
        if unit is None or not unit.theory:
            # nothing to mark: the current unit carries no theory turn (review v1.2)
            snapshot = service.session_snapshot()
            raise ApiError(409, "STALE_ACTIVITY",
                           "The current unit has no pending theory turn.",
                           turn=project_turn(snapshot, service=service))
        view = service.mark_theory_seen()
        return {"turn": project_turn(view, service=service)}

    @app.post("/api/v1/sessions/{session_id}/activities/{activity_id}/answer")
    def answer(session_id: int, activity_id: str, body: AnswerRequest,
               idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        """Answer + idempotent replay (design §4.5, review v1.2 C1)."""
        ensure_session_target(service, session_id, require_active=True)
        if not idempotency_key:
            raise ApiError(400, "MISSING_IDEMPOTENCY_KEY",
                           "Header 'Idempotency-Key' is required for answer submissions.")
        # 2. idempotency-key lookup FIRST (design §4.5 order) — replays even if the activity advanced
        attempt = service.storage.find_attempt_by_idempotency_key(
            service.learner.id, session_id, idempotency_key)
        if attempt is not None:
            snapshot = service.session_snapshot()  # read-only: authoritative current turn
            return {"turn": project_turn(snapshot, service=service),
                    "result": project_result_from_attempt(attempt, duplicate=True)}
        # 3. stale-activity check SECOND (unseen keys only)
        state = service.storage.load_state(service.learner.id)
        if state is None or state.current_exercise_id != activity_id:
            snapshot = service.session_snapshot()
            raise ApiError(409, "STALE_ACTIVITY",
                           "This activity is no longer current; the authoritative turn is included.",
                           turn=project_turn(snapshot, service=service))
        # 4. process
        view = service.submit_response(body.answer, idempotency_key=idempotency_key)
        attempts = [a for a in service.storage.attempts_for_learner(service.learner.id)
                    if a.session_id == session_id]
        assisted = (not attempts[-1].independent_success) if attempts else None
        turn = project_turn(view, service=service, assisted=assisted)
        return {"turn": turn, "result": turn["result"]}

    @app.post("/api/v1/sessions/{session_id}/activities/{activity_id}/hint")
    def hint(session_id: int, activity_id: str):
        """Next rung of the assistance ladder (design §4.6)."""
        ensure_session_target(service, session_id, require_active=True)
        state = service.storage.load_state(service.learner.id)
        if state is None or state.current_exercise_id != activity_id:
            snapshot = service.session_snapshot()
            raise ApiError(409, "STALE_ACTIVITY",
                           "This activity is no longer current; the authoritative turn is included.",
                           turn=project_turn(snapshot, service=service))
        view = service.request_hint()
        if view.kind == "info":
            message = view.extra.get("message", "")
            if message.startswith("Assistance ladder exhausted"):
                raise ApiError(409, "LADDER_EXHAUSTED", message)
            raise ApiError(409, "SESSION_NOT_ACTIVE", message)
        return {"turn": project_turn(view, service=service)}

    @app.post("/api/v1/sessions/{session_id}/activities/{activity_id}/reveal-solution")
    def reveal_solution(session_id: int, activity_id: str):
        """Complete reveal, L6 (design §4.7) — the attempt can never count as independent."""
        ensure_session_target(service, session_id, require_active=True)
        state = service.storage.load_state(service.learner.id)
        if state is None or state.current_exercise_id != activity_id:
            snapshot = service.session_snapshot()
            raise ApiError(409, "STALE_ACTIVITY",
                           "This activity is no longer current; the authoritative turn is included.",
                           turn=project_turn(snapshot, service=service))
        view = service.reveal_solution()
        if view.kind == "info" and "No stored solution" in view.extra.get("message", ""):
            raise ApiError(404, "NO_SOLUTION", view.extra.get("message", ""))
        snapshot = service.session_snapshot()
        return {"solution": view.extra.get("message", ""),
                "turn": project_turn(snapshot, service=service)}

    @app.post("/api/v1/sessions/{session_id}/activities/{activity_id}/explain")
    def explain(session_id: int, activity_id: str):
        """Targeted AI explanation connected to the current task (design §4.8)."""
        ensure_session_target(service, session_id, require_active=True)
        state = service.storage.load_state(service.learner.id)
        if state is None or state.current_exercise_id != activity_id:
            snapshot = service.session_snapshot()
            raise ApiError(409, "STALE_ACTIVITY",
                           "This activity is no longer current; the authoritative turn is included.",
                           turn=project_turn(snapshot, service=service))
        view = service.explain_current()
        message = view.extra.get("message", "") if view.extra else ""
        return {"explanation": message}

    # ------------------------------------------------------------- confidence
    @app.post("/api/v1/sessions/{session_id}/confidence")
    def confidence(session_id: int, body: ConfidenceRequest):
        """Confidence rating (design §4.9) — session targeting + skill validation (review v1.2)."""
        ensure_session_target(service, session_id, require_active=True)
        if body.skill_id not in service.curriculum.skills:
            raise ApiError(400, "UNKNOWN_SKILL", f"Unknown skill '{body.skill_id}'.")
        if not 1 <= body.rating <= 5:
            raise ApiError(400, "INVALID_CONFIDENCE", "Confidence rating must be 1..5.")
        view = service.report_confidence(body.skill_id, body.rating)
        return {"recorded": True, "skill_id": body.skill_id}

    return app
