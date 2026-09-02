"""TurnView -> public JSON projection (design doc §2, §5, §6).

Pure functions. Zero engine logic: everything rendered here originates from the engine decision,
the persisted session, or the curriculum. Grading secrets (design §2.3 map) never leave this module.
"""
from __future__ import annotations

from datetime import datetime, timezone

from dsa_tutor.domain.models import DailyPlan, EngineAction, TutoringSession

ANSWER_FORMAT = {
    "mcq": "letter",
    "free_form": "text",
    "code_writing": "code",
    "code_tracing": "lines",
    "output_prediction": "lines",
    "complexity_question": "big_o",
    "graph_construction": "edges",
}

_MODE_LABELS = {
    "teach": "Study", "practice": "Practice check", "assess": "Assessment",
    "apply": "Application", "remediation": "Remediation",
    "prerequisite_revisit": "Prerequisite refresher", "repeat": "Repeat practice",
    "variation": "Variation practice", "increase_difficulty": "Harder challenge",
    "reduce_difficulty": "Smaller step", "advance": "Practice",
}


def _iso(dt) -> str | None:
    if dt is None:
        return None
    dt = _aware(dt)
    return dt.astimezone(timezone.utc).isoformat()


def _aware(dt):
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def end_reason_code(text: str | None) -> str | None:
    """Closed enum per design §7.4 (deterministic mapping over the stored free text)."""
    if not text:
        return None
    t = text.lower()
    if "interrupted" in t:
        return "interrupted"
    if "budget exhausted" in t:
        return "budget_exhausted"
    if "min remain" in t or "natural point" in t:
        return "short_window_stop"
    if "learner requested" in t or "learner stop" in t:
        return "learner_stop"
    if "mastered" in t or "curriculum complete" in t or "skills complete" in t:
        return "curriculum_complete"
    return "other"


def derive_mode(decision, unit, exercise) -> str:
    if decision is not None:
        action = decision.action
        if action in {EngineAction.REMEDIATION, EngineAction.PREREQUISITE_REVISIT,
                      EngineAction.REDUCE_DIFFICULTY, EngineAction.REPEAT,
                      EngineAction.VARIATION, EngineAction.INCREASE_DIFFICULTY}:
            return action.value
    return unit.unit_type.value if unit is not None else "practice"


def _remaining_minutes(session: TutoringSession) -> float | None:
    if session is None or session.status.value != "active" or session.started_at is None:
        return None
    elapsed = (datetime.now(timezone.utc) - _aware(session.started_at)).total_seconds() / 60.0
    return round(max(0.0, session.budget_minutes - elapsed), 2)


def project_daily(plan: DailyPlan | None) -> dict | None:
    if plan is None:
        return None
    return {"target_units": plan.target_units, "completed_units": plan.completed_units,
            "status": plan.status}


def project_session(session: TutoringSession | None, *, remaining_minutes: float | None = None,
                    daily: DailyPlan | None = None, units_completed: int | None = None) -> dict | None:
    if session is None:
        return None
    remaining = remaining_minutes if remaining_minutes is not None else _remaining_minutes(session)
    status = getattr(session.status, "value", session.status)
    pace = getattr(session.pace, "value", session.pace)
    out = {
        "id": session.id,
        "status": status,
        "pace": pace,
        "budget_minutes": session.budget_minutes,
        "remaining_minutes": remaining,
        "started_at": _iso(session.started_at),
        "ended_at": _iso(session.ended_at),
        "end_reason_code": end_reason_code(session.end_reason),
        "end_reason_detail": session.end_reason,
        "daily": project_daily(daily),
    }
    if units_completed is not None:
        out["units_completed"] = units_completed
    return out


def project_step(decision, *, plan_skills: set[str] | None = None) -> dict | None:
    if decision is None:
        return None
    planned = (decision.action == EngineAction.ADVANCE
               and plan_skills is not None
               and decision.skill_id in plan_skills)
    return {"action": decision.action.value, "why": list(decision.why),
            "sequence": "planned" if planned else "adaptive"}


def project_result(evaluation, *, duplicate: bool = False, assisted: bool | None = None) -> dict | None:
    if evaluation is None:
        return None
    provider = getattr(evaluation, "provider", "builtin")
    degraded = bool(getattr(evaluation, "degraded", False))
    if provider == "deterministic":
        answered_by = "engine-deterministic"
    elif degraded:
        answered_by = "builtin-fallback"
    elif provider == "openai":
        answered_by = "ai"
    else:
        answered_by = "builtin"
    return {
        "correct": evaluation.correct,
        "score": round(float(evaluation.score), 4) if evaluation.score is not None else None,
        "feedback": evaluation.feedback,
        "confidence_signal": evaluation.confidence_signal,
        "misconception": evaluation.identified_misconception,
        "answered_by": answered_by,
        "assisted": assisted,
        "duplicate": duplicate,
    }


def project_result_from_attempt(attempt, *, duplicate: bool = True) -> dict:
    """Replay source: rebuild the public result from the stored attempt (design §4.5)."""
    ev = attempt.evaluation or {}
    provider = ev.get("provider", "builtin")
    if provider == "deterministic":
        answered_by = "engine-deterministic"
    elif ev.get("degraded"):
        answered_by = "builtin-fallback"
    elif provider == "openai":
        answered_by = "ai"
    else:
        answered_by = "builtin"
    return {
        "correct": ev.get("correct"), "score": ev.get("score"),
        "feedback": ev.get("feedback", ""), "confidence_signal": ev.get("confidence_signal"),
        "misconception": ev.get("identified_misconception"), "answered_by": answered_by,
        "assisted": not attempt.independent_success, "duplicate": duplicate,
    }


def project_result_from_attempt(attempt, *, duplicate: bool = True) -> dict:
    """Replay source: rebuild the public result from the stored attempt (design §4.5)."""
    ev = attempt.evaluation or {}
    provider = ev.get("provider", "builtin")
    if provider == "deterministic":
        answered_by = "engine-deterministic"
    elif ev.get("degraded"):
        answered_by = "builtin-fallback"
    elif provider == "openai":
        answered_by = "ai"
    else:
        answered_by = "builtin"
    return {
        "correct": ev.get("correct"), "score": ev.get("score"),
        "feedback": ev.get("feedback", ""), "confidence_signal": ev.get("confidence_signal"),
        "misconception": ev.get("identified_misconception"), "answered_by": answered_by,
        "assisted": not attempt.independent_success, "duplicate": duplicate,
    }


def project_hint(hint) -> dict | None:
    if hint is None:
        return None
    return {"level": hint.level, "kind": hint.kind, "text": hint.text}


def project_activity(exercise, *, generated: bool, decision, unit, position, curriculum) -> dict:
    itype = exercise.interaction_type.value
    payload = exercise.payload or {}
    skill = curriculum.skill(exercise.skill_id)
    mode = derive_mode(decision, unit, exercise)
    label = _MODE_LABELS.get(mode, "Practice")
    purpose = f"{label} on '{skill.title}'"
    if exercise.scope.value == "problem":
        purpose += " — application problem"
    out = {
        "id": exercise.id,
        "type": itype,
        "mode": mode,
        "purpose": purpose,
        "prompt": exercise.prompt,
        "answer_format": ANSWER_FORMAT[itype],
        "position": {"index": position[0], "of": position[1]} if position else None,
        "unit": {"id": unit.id, "title": unit.title, "goal": unit.goal} if unit else None,
        "skill": {"id": skill.id, "title": skill.title},
        "choices": None, "code": None, "starter": None, "function_name": None,
        "nodes": None, "kind": None,
        "generated": generated,
        "hints": {"allowed": True, "max_level": exercise.max_hints},
        "available_actions": ["answer", "hint", "explain", "progress", "solution", "stop"],
    }
    # per-type whitelist (design §2.3) — grader-only payload keys stay server-side
    if itype == "mcq":
        out["choices"] = [{"id": c.get("id"), "text": c.get("text")}
                          for c in payload.get("choices", [])]
    elif itype in {"code_tracing", "output_prediction"}:
        out["code"] = payload.get("code")
    elif itype == "code_writing":
        out["function_name"] = payload.get("function_name")
        out["starter"] = payload.get("starter")
    elif itype == "graph_construction":
        out["nodes"] = payload.get("nodes")
    elif itype == "complexity_question":
        out["kind"] = payload.get("kind")
    return out


def project_theory(view, curriculum) -> dict | None:
    unit = view.unit
    if unit is None:
        return None
    return {"unit": {"id": unit.id, "title": unit.title, "goal": unit.goal},
            "text": unit.theory,
            "checks_upcoming": len(curriculum.exercises_for_unit(unit.id))}


def project_turn(view, *, service, duplicate: bool = False, assisted: bool | None = None) -> dict:
    """Universal turn envelope (design §5.1). Session targeting/plan preview are read-only."""
    session_obj = service.session or service.storage.latest_session(service.learner.id)
    plan_skills: set[str] | None = None
    try:
        plan_skills = {item["skill"] for item in service.session_plan()["items"]}
    except Exception:
        plan_skills = None
    turn = {
        "type": {"theory": "theory", "exercise": "activity", "ended": "ended",
                 "info": "notice"}.get(view.kind, view.kind),
        "session": project_session(session_obj, remaining_minutes=view.remaining_minutes,
                                   daily=view.daily,
                                   units_completed=view.extra.get("units_completed")),
        "step": project_step(view.decision, plan_skills=plan_skills),
        "notice": None, "activity": None, "theory": None, "result": None, "hint": None,
    }
    message = view.extra.get("message") if isinstance(view.extra, dict) else None
    if view.kind == "info":
        turn["notice"] = {"kind": "info", "text": message or ""}
    elif view.kind == "ended":
        turn["notice"] = {"kind": "ended", "text": message or ""}
    elif view.extra.get("revealed") if isinstance(view.extra, dict) else False:
        turn["notice"] = {"kind": "solution_revealed", "text": message or ""}
    if view.kind == "exercise" and view.exercise is not None:
        unit = view.unit if view.unit is not None else \
            service.curriculum.units.get(view.exercise.unit_id)
        position = view.extra.get("unit_position") if isinstance(view.extra, dict) else None
        turn["activity"] = project_activity(view.exercise, generated=view.generated,
                                            decision=view.decision, unit=unit, position=position,
                                            curriculum=service.curriculum)
    if view.evaluation is not None:
        turn["result"] = project_result(view.evaluation, duplicate=duplicate, assisted=assisted)
    if view.hint is not None:
        turn["hint"] = project_hint(view.hint)
    if view.kind == "theory":
        turn["theory"] = project_theory(view, service.curriculum)
    if view.confidence_request:
        turn["confidence_request"] = {"skill_id": view.confidence_request}
    return turn
