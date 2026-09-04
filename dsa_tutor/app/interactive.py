"""Interactive CLI loop (spec Phase 4). Renders; it never decides."""
from __future__ import annotations

from ..domain.models import InteractionType, Pace

BANNER = r"""
=== DSA Tutor V0 — Graphs, BFS, DFS (adaptive, local) ===
commands during an exercise:  hint | why | explain | progress | solution | stop
answers: type your answer (MCQ: letter a/b/c/d; code: finish with a line 'END')
"""


def _fmt_dim(value: float) -> str:
    bar = "#" * int(round(value * 10))
    return f"{value:.2f} [{bar:<10}]"


def render_progress(report: dict) -> str:
    lines = ["", "Mastery states (derived from evidence — no percentages):", ""]
    lines.append(f"{'skill':<26}{'state':<12}{'evidence':>8}  master")
    current_section = None
    for row in report["skills"]:
        if row["section"] != current_section:
            current_section = row["section"]
            lines.append(f"-- {current_section} --")
        flag = "OK" if row["mastered"] else ("boundary" if row["boundary"] else ".")
        lines.append(f"{row['skill']:<26}{row['state']:<12}{row['evidence']:>8}  {flag}")
    daily = report["daily"]
    lines.append("")
    lines.append(f"Daily target: {daily['completed_units']}/{daily['target_units']} units "
                 f"({daily['status']})")
    return "\n".join(lines)


def _read_code() -> str:
    print("Enter your code. Finish with a single line containing only END:")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def _prompt_answer(exercise) -> str:
    if exercise.interaction_type == InteractionType.MCQ:
        return input("Your answer (a/b/c/d): ").strip()
    if exercise.interaction_type == InteractionType.CODE_WRITING:
        return _read_code()
    if exercise.interaction_type == InteractionType.COMPLEXITY_QUESTION:
        return input("Your big-O answer: ").strip()
    if exercise.interaction_type in {InteractionType.OUTPUT_PREDICTION, InteractionType.CODE_TRACING}:
        return input("Expected output (one line, or comma-separated lines): ").strip()
    return input("Your answer (free text): ").strip()


def _show_exercise(view) -> None:
    ex = view.exercise
    tag = " [AI-generated]" if view.generated else ""
    pos = view.extra.get("unit_position") if isinstance(view.extra, dict) else None
    pos_label = f" — exercise {pos[0]} of {pos[1]} in this unit" if pos else ""
    print()
    print(f"--- {ex.skill_id} :: {ex.interaction_type.value}{tag}{pos_label} ---")
    if view.decision and view.decision.why:
        print(f"({view.decision.why[-1]})")   # compact, human reason; full chain via 'why'
    print()
    print(ex.prompt)
    if ex.interaction_type == InteractionType.MCQ:
        for choice in ex.payload.get("choices", []):
            print(f"  [{choice['id']}] {choice['text']}")


def run_session(service, pace: Pace, resume: bool) -> None:
    print(BANNER)
    try:
        _run_loop(service, pace, resume)
    except (EOFError, KeyboardInterrupt):
        print()
        view = service.stop_session("interrupted (EOF/Ctrl+C) — state persisted")
        print(view.extra.get("message", ""))


def render_plan(plan: dict) -> str:
    """Session roadmap: what will be studied and how many questions are coming."""
    lines = ["", "=== SESSION PLAN "
             f"(~{plan['remaining_minutes']:.0f} min left of {plan['pace_budget']} min budget) ==="]
    if not plan["items"]:
        lines.append("Nothing left planned — all targeted units are done for today. "
                     "Use 'stop' to end at a natural point.")
        return "\n".join(lines)
    for i, item in enumerate(plan["items"], 1):
        kind = "study + " if item["theory"] else ""
        lines.append(f"  {i}. {kind}{item['title']} ({item['questions']} question"
                     f"{'s' if item['questions'] != 1 else ''})")
    lines.append(f"Total: {plan['theory_blocks']} study section(s), "
                 f"{plan['questions']} question(s) across {plan['units']} unit(s)")
    lines.append(f"Overall progress: {plan['mastered']}/{plan['total_skills']} skills mastered")
    lines.append("(Questions come AFTER each study section — theory first, always.)")
    return "\n".join(lines)


def _run_loop(service, pace: Pace, resume: bool) -> None:
    view = service.start_session(pace=pace, resume=resume)
    if view.kind == "info":
        print(view.extra.get("message", ""))
        return
    if view.kind == "ended":
        print(view.extra.get("message", ""))
        return
    if view.daily is not None:
        print(f"Daily target: {view.daily.completed_units}/{view.daily.target_units} units"
              + (f" | ~{view.remaining_minutes:.0f} min budget" if view.remaining_minutes else ""))
        print(render_plan(service.session_plan()))

    while True:
        if view.confidence_request:
            try:
                raw = input(f"Confidence in '{view.confidence_request}' (1-5, Enter to skip): ").strip()
                if raw:
                    service.report_confidence(view.confidence_request, int(raw))
            except (ValueError, EOFError):
                pass
            view.confidence_request = None
        if view.kind == "theory":
            unit = view.unit
            print()
            print(f"=== STUDY: {unit.title} ===")
            print()
            print(unit.theory)
            print()
            n_qs = len(service.curriculum.exercises_for_unit(unit.id))
            input(f"[Enter] when you have read this — then {n_qs} quick check"
                  f"{'s' if n_qs != 1 else ''} on it...")
            view = service.mark_theory_seen()
        elif view.kind == "exercise":
            if view.hint is not None:
                print(f"\nHint (level {view.hint.level}, {view.hint.kind}):")
                print(f"  {view.hint.text}")
            _show_exercise(view)
            raw = _prompt_answer(view.exercise)
            cmd = raw.strip().lower()
            if cmd == "hint":
                view = service.request_hint()
                if view.kind == "info":
                    print(view.extra.get("message", ""))
                    view = _refresh_exercise_view(service)
                continue
            if cmd == "solution":
                view = service.reveal_solution()
                print(view.extra.get("message", ""))
                view = _refresh_exercise_view(service)
                continue
            if cmd == "why":
                state_view = _refresh_exercise_view(service)
                if state_view.decision:
                    print("Why this step: " + state_view.decision.explanation)
                continue
            if cmd == "explain":
                info = service.explain_current()
                print(info.extra.get("message", ""))
                continue
            if cmd == "progress":
                print(render_progress(service.progress_report()))
                continue
            if cmd in {"stop", "quit", "exit"}:
                view = service.stop_session()
                print(view.extra.get("message", ""))
                return
            view = service.submit_response(raw)
        elif view.kind == "ended":
            print()
            print(view.extra.get("message", ""))
            if "units_completed" in view.extra:
                print(f"Units completed this session: {view.extra['units_completed']}")
            return
        elif view.kind == "info":
            print(view.extra.get("message", ""))
            view = _refresh_exercise_view(service)
        else:  # pragma: no cover
            print(f"unexpected turn kind: {view.kind}")
            return

        if view.evaluation is not None:
            ev = view.evaluation
            mark = "correct" if ev.correct else "incorrect"
            print(f"\n[{mark} · score {ev.score:.2f}"
                  + (f" · {ev.confidence_signal}" if ev.confidence_signal else "") + "]")
            print(ev.feedback)
            if ev.identified_misconception:
                print(f"(misconception: {ev.identified_misconception})")
            if view.extra.get("ai_degraded"):
                reason = str(view.extra["ai_degraded"])
                if "daily external AI limit" in reason:
                    print(f"(daily external AI budget spent — the built-in tutor answered. "
                          f"External AI resumes after the daily reset. [{reason.split('. ')[0]}])")
                else:
                    print("(external AI unavailable — builtin tutor answered instead)")


def _refresh_exercise_view(service):
    """After hint/solution/info detours, rebuild the current exercise view."""
    view = service.start_session(resume=True)
    if view.kind in {"info", "ended"}:
        from ..app.service import TurnView
        return TurnView(kind="info", extra={"message": "Session ended."})
    return view
