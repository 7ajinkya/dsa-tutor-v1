"""Application/use-case layer: coordinates CLI <-> learning engine <-> AI <-> storage.

Owns transaction boundaries (one coherent interaction record), cost controls (MCQs
graded deterministically without any AI call), and event emission. Learning decisions
are never made here — they come from the engine; semantic judgments come from the AI.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from ..ai.factory import get_ai_tutor
from ..ai.schemas import EvaluationResult, HintResult
from ..content.curriculum_v0 import EXERCISES, PREREQS, SKILLS, TOPICS, UNITS
from ..domain import mastery
from ..domain.curriculum import Curriculum
from ..domain.engine import EngineSnapshot, LearningEngine
from ..domain.models import (
    Attempt, DailyPlan, EngineAction, EngineDecision, EventType, EvidenceOutcome,
    EvidenceType, Exercise, InteractionType, LearnerState, Pace, SessionEvent,
    SessionStatus, SkillAssessment, TutoringSession, utcnow,
)

LEARNER_NAME = "local_learner"


@dataclass
class TurnView:
    """Everything the CLI needs to render one turn."""
    kind: str                                  # theory | exercise | confidence | ended | info
    decision: EngineDecision | None = None
    unit: Any = None
    exercise: Exercise | None = None
    generated: bool = False
    evaluation: EvaluationResult | None = None
    hint: HintResult | None = None
    confidence_request: Optional[str] = None   # skill_id to rate now
    remaining_minutes: float | None = None
    daily: DailyPlan | None = None
    extra: dict = field(default_factory=dict)


class TutorService:
    def __init__(self, storage, config, curriculum: Curriculum | None = None, ai=None,
                 learner_name: str = LEARNER_NAME):
        self.storage = storage
        self.config = config
        self.curriculum = curriculum or build_curriculum()
        self.ai = ai or get_ai_tutor(config)
        self.engine = LearningEngine(self.curriculum, config.engine)
        # learner identity is the persistent users row keyed by name: a fresh process
        # resolves the same learner and their state, sessions, attempts and evidence
        self.learner = self.storage.get_or_create_learner(learner_name)
        self.session: TutoringSession | None = None
        self._gen_counter = 0
        self._confidences: dict[str, int] = {}
        self._confidence_asked: set[str] = set()
        self._event_seq = 0
        self._units_at_start = 0

    # ------------------------------------------------------------ helpers
    def _snapshot(self, state: LearnerState) -> EngineSnapshot:
        assessments = self.storage.assessments_for_learner(self.learner.id)
        evidence: dict[str, list] = {}
        for record in self.storage.evidence_for_learner(self.learner.id):
            evidence.setdefault(record.skill_id, []).append(record)
        recent_scores = None
        if state.current_skill_id:
            recent_scores = [a.score for a in self.storage.attempts_for_learner(self.learner.id)
                             if a.skill_id == state.current_skill_id][-3:]
        return EngineSnapshot(state=state, assessments=assessments, evidence=evidence,
                              session=self.session, remaining_minutes=self._remaining_minutes(),
                              recent_scores=recent_scores)

    def _remaining_minutes(self) -> float | None:
        if self.session is None or self.session.status != "active":
            return None
        elapsed = (utcnow() - self.session.started_at).total_seconds() / 60.0
        return max(0.0, self.session.budget_minutes - elapsed)

    def _state(self) -> LearnerState:
        state = self.storage.load_state(self.learner.id)
        return state or LearnerState(learner_id=self.learner.id)

    def _event(self, event_type: EventType, payload: dict) -> SessionEvent:
        self._event_seq += 1
        return SessionEvent(id=None, session_id=self.session.id, seq=self._event_seq,
                            event_type=event_type, payload=payload)

    def _resolve_exercise(self, exercise_id: str) -> tuple[Exercise | None, bool]:
        stored = self.storage.get_exercise(exercise_id)
        if stored is not None:
            return stored, True
        if exercise_id in self.curriculum.exercises:
            return self.curriculum.exercise(exercise_id), False
        return None, False

    # ------------------------------------------------------------ daily plan
    def _today_plan(self) -> DailyPlan:
        today = date.today()
        plan = self.storage.daily_plan(self.learner.id, today)
        if plan is None:
            target = self.config.engine.daily_target_units
            yesterday = self.storage.daily_plan(self.learner.id, today.fromordinal(today.toordinal() - 1))
            if yesterday is not None and yesterday.completed_units > 0:
                rate = yesterday.completed_units / max(1, yesterday.target_units)
                if rate >= 1.2:
                    target = min(8, target + 1)
                elif rate < 0.6:
                    target = max(2, target - 1)
            plan = DailyPlan(id=None, learner_id=self.learner.id, plan_date=today,
                             target_units=target, completed_units=0)
            self.storage.upsert_daily_plan(plan)
        return plan

    # ------------------------------------------------------------ session lifecycle
    def start_session(self, pace: Pace = Pace.NORMAL, resume: bool = False) -> TurnView:
        errors = self.config.validate()
        if errors:
            raise RuntimeError("configuration invalid: " + "; ".join(errors))
        plan = self._today_plan()
        if resume:
            existing = self.storage.latest_active_session(self.learner.id)
            if existing is None:
                return TurnView(kind="info", extra={"message": "No paused or active session to resume."})
            self.session = existing
            self.session.status = SessionStatus.ACTIVE
            self.storage.update_session(self.session)
            self._event_seq = len(self.storage.events_for_session(self.session.id))
            state = self._state()
            self.storage.append_event(self._event(EventType.SESSION_STARTED, {"note": "session resumed"}))
            if state.current_exercise_id:
                exercise, generated = self._resolve_exercise(state.current_exercise_id)
                if exercise is not None:
                    decision = EngineDecision(EngineAction.REPEAT, skill_id=state.current_skill_id,
                                              unit_id=state.current_unit_id,
                                              exercise_id=exercise.id,
                                              why=["resumed from persisted stopping point"])
                    # route through the standard presentation gate: a pause taken on a
                    # theory turn must resume with the theory, not skip straight to the check
                    return self._present_from_decision(decision, state, plan)
            return self._present_from_decision(self.engine.select_next(self._snapshot(state)), state, plan)

        self.session = TutoringSession(
            id=None, learner_id=self.learner.id, pace=pace,
            budget_minutes=self.config.engine.pace_budget_minutes[pace.value])
        self.storage.create_session(self.session)
        self._event_seq = 0
        state0 = self._state()
        self._units_at_start = len([u for u in state0.completed_unit_ids if not u.startswith("theory:")])
        self.storage.append_event(self._event(EventType.SESSION_STARTED, {
            "pace": pace.value, "budget_minutes": self.session.budget_minutes}))
        state = self._state()
        return self._present_from_decision(self.engine.select_next(self._snapshot(state)), state, plan)

    def stop_session(self, reason: str = "learner requested stop") -> TurnView:
        if self.session is None:
            return TurnView(kind="info", extra={"message": "No active session."})
        state = self._state()
        self.session.status = SessionStatus.PAUSED
        self.session.ended_at = utcnow()
        self.session.end_reason = reason
        self.storage.update_session(self.session)
        self.storage.save_state(state)
        self.storage.append_event(self._event(EventType.SESSION_ENDED, {
            "reason": reason, "status": "paused", "resume_point": {
                "skill": state.current_skill_id, "unit": state.current_unit_id,
                "exercise": state.current_exercise_id}}))
        self.session = None
        return TurnView(kind="ended", extra={"message": f"Session paused — state persisted ({reason})."})

    def finish_session_if_due(self, decision: EngineDecision) -> bool:
        if decision.action == EngineAction.END_SESSION:
            return True
        return False

    # ------------------------------------------------------------ presentation
    def _present_from_decision(self, decision: EngineDecision, state: LearnerState,
                               plan: DailyPlan) -> TurnView:
        if decision.action == EngineAction.END_SESSION:
            return self._end_naturally(decision)
        exercise, generated = self._resolve_exercise(decision.exercise_id)
        if exercise is None:
            return self._end_naturally(EngineDecision(
                EngineAction.END_SESSION, why=["nothing presentable found; ending safely"]))
        state.current_skill_id = decision.skill_id or exercise.skill_id
        state.current_unit_id = decision.unit_id or exercise.unit_id
        state.current_exercise_id = exercise.id
        state.pending_action = decision.action.value
        unit = self.curriculum.units.get(exercise.unit_id)
        if exercise.interaction_type == InteractionType.THEORY or self._theory_pending(state, exercise):
            self.storage.save_state(state)
            self.storage.append_event(self._event(EventType.THEORY_VIEWED,
                                                  {"unit": unit.id if unit else None}))
            return TurnView(kind="theory", decision=decision, unit=unit, exercise=exercise,
                            generated=generated, remaining_minutes=self._remaining_minutes(),
                            daily=plan)
        self.storage.save_state(state)
        return self._exercise_view(decision, exercise, generated, state, plan, unit=unit)

    @staticmethod
    def _unit_theory_seen(state: LearnerState, unit_id: str) -> bool:
        return f"theory:{unit_id}" in state.completed_unit_ids

    def _theory_pending(self, state: LearnerState, exercise: Exercise) -> bool:
        """A teach unit's study text is pending when its first check was selected but the
        learner has not acknowledged the theory yet (single gate for every presentation path)."""
        unit = self.curriculum.units.get(exercise.unit_id)
        return bool(
            unit is not None and unit.theory and not self._unit_theory_seen(state, unit.id)
            and unit.unit_type.value == "teach" and exercise.ordering <= 1)

    def _exercise_view(self, decision: EngineDecision, exercise: Exercise, generated: bool,
                       state: LearnerState, plan: DailyPlan, unit=None) -> TurnView:
        self.storage.append_event(self._event(EventType.QUESTION_PRESENTED, {
            "exercise": exercise.id, "type": exercise.interaction_type.value,
            "skill": exercise.skill_id, "action": decision.action.value}))
        self.storage.save_state(state)
        if unit is None:
            unit = self.curriculum.units.get(exercise.unit_id)
        confidence_request = None
        skill = self.curriculum.skills.get(exercise.skill_id)
        if skill and max(skill.complexity.values()) >= 3 and skill.id not in self._confidence_asked:
            confidence_request = skill.id
        extra = {}
        unit_exercises = self.curriculum.exercises_for_unit(exercise.unit_id)
        idx = next((i for i, e in enumerate(unit_exercises, 1) if e.id == exercise.id), None)
        if idx:
            extra["unit_position"] = (idx, len(unit_exercises))
        return TurnView(kind="exercise", decision=decision, unit=unit, exercise=exercise,
                        generated=generated, remaining_minutes=self._remaining_minutes(),
                        daily=plan, confidence_request=confidence_request, extra=extra)

    def _end_naturally(self, decision: EngineDecision) -> TurnView:
        state = self._state()
        state.sessions_completed += 1
        state.pending_action = EngineAction.END_SESSION.value
        self.session.status = SessionStatus.COMPLETED
        self.session.ended_at = utcnow()
        self.session.end_reason = "; ".join(decision.why)[:300]
        plan = self._today_plan()
        units_this_session = self._units_completed_this_session()
        plan.completed_units += units_this_session
        if plan.completed_units >= plan.target_units:
            plan.status = "completed"
        self.storage.update_session(self.session)
        self.storage.save_state(state)
        self.storage.upsert_daily_plan(plan)
        self.storage.append_event(self._event(EventType.SESSION_ENDED, {
            "reason": decision.explanation, "status": "completed",
            "units_completed": units_this_session}))
        self.session = None
        return TurnView(kind="ended", decision=decision,
                        extra={"message": "Session complete — " + decision.explanation,
                               "units_completed": units_this_session})

    def _units_completed_this_session(self) -> int:
        state = self.storage.load_state(self.learner.id)
        if state is None:
            return 0
        completed = [u for u in state.completed_unit_ids if not u.startswith("theory:")]
        return max(0, len(completed) - self._units_at_start)

    # ------------------------------------------------------------ interaction
    def mark_theory_seen(self) -> TurnView:
        state = self._state()
        if state.current_unit_id:
            state.completed_unit_ids.append(f"theory:{state.current_unit_id}")
            self.storage.save_state(state)
        # move to the unit's first exercise
        decision = EngineDecision(EngineAction.ADVANCE, skill_id=state.current_skill_id,
                                  unit_id=state.current_unit_id, why=["theory viewed -> start checks"])
        unit_exercises = [e for e in self.curriculum.exercises_for_unit(state.current_unit_id)]
        if not unit_exercises and state.current_unit_id:
            return self._present_from_decision(self.engine.select_next(self._snapshot(state)),
                                               state, self._today_plan())
        exercise = sorted(unit_exercises, key=lambda e: e.ordering)[0]
        decision.exercise_id = exercise.id
        return self._present_from_decision(decision, state, self._today_plan())

    def _log_ai(self, operation: str, evaluation_or_result, latency_ms: int,
                request: dict | None = None) -> None:
        """Persist a structured AI interaction (raw bodies only if enabled)."""
        try:
            result_dict = evaluation_or_result.to_dict() if hasattr(evaluation_or_result, "to_dict") \
                else {"text": str(evaluation_or_result)[:500]}
            self.storage.log_ai_interaction(
                learner_id=self.learner.id, session_id=self.session.id if self.session else None,
                operation=operation, provider=result_dict.get("provider", "?"),
                model=result_dict.get("model"), prompt_version=result_dict.get("prompt_version"),
                request=request, response=result_dict, validation_ok=True,
                latency_ms=latency_ms, keep_raw=self.config.ai.log_raw_requests)
        except Exception:  # noqa: BLE001 - logging must never break the session
            pass

    def submit_response(self, response: str, idempotency_key: str | None = None) -> TurnView:
        state = self._state()
        exercise, generated = self._resolve_exercise(state.current_exercise_id or "")
        if exercise is None:
            return TurnView(kind="info", extra={"message": "No exercise in progress. Start a session first."})
        plan = self._today_plan()
        hints_used = state.hints_used_current

        # deterministic grading for simple MCQs (cost control, spec 04 §7)
        if exercise.interaction_type == InteractionType.MCQ:
            evaluation = self._grade_mcq_locally(exercise, response)
            confidence = self._confidences.get(exercise.skill_id)
            if confidence is not None and evaluation.correct is not None:
                if confidence >= 4 and evaluation.correct is False:
                    evaluation.confidence_signal = "overconfident"
                elif confidence <= 2 and evaluation.correct is True:
                    evaluation.confidence_signal = "underconfident"
                else:
                    evaluation.confidence_signal = "calibrated"
        else:
            context = self._ai_context(exercise, state)
            t0 = time.perf_counter()
            evaluation = self.ai.evaluate(exercise, response, context)
            self._log_ai("evaluate", evaluation, int((time.perf_counter() - t0) * 1000),
                         request={"exercise": exercise.id, "response": response[:500]})

        # amendment: low AI self-confidence never drives aggressive engine decisions
        low_confidence = (evaluation.ai_confidence is not None and evaluation.ai_confidence < 0.5)

        assistance_level = 6 if state.pending_action == "solution_revealed" else hints_used
        outcome = mastery.outcome_for_attempt(evaluation.correct, evaluation.score,
                                              assistance_level, state.pending_action == "solution_revealed")
        unit = self.curriculum.units.get(exercise.unit_id)
        records = mastery.evidence_for_attempt(unit, exercise.interaction_type, outcome)
        for r in records:
            r.skill_id = exercise.skill_id
            r.evidence_type = EvidenceType(exercise.role.value)  # role defines demonstrated type
            r.assistance_level = assistance_level
        attempt = Attempt(id=None, session_id=self.session.id, learner_id=self.learner.id,
                          exercise_id=exercise.id, skill_id=exercise.skill_id,
                          response=response[:4000], is_correct=evaluation.correct,
                          score=evaluation.score, evaluation=evaluation.to_dict(),
                          hints_used=hints_used,
                          max_assistance_level=6 if state.pending_action == "solution_revealed" \
                              else min(hints_used, 6),
                          independent_success=(evaluation.correct is True and hints_used == 0
                                               and state.pending_action != "solution_revealed"),
                          completed=evaluation.correct is True,
                          solution_revealed=(state.pending_action == "solution_revealed"),
                          ai_provider=evaluation.provider, ai_model=evaluation.model,
                          prompt_version=evaluation.prompt_version,
                          idempotency_key=idempotency_key)

        # recompute assessment from the full evidence stream
        all_records = {}
        for record in self.storage.evidence_for_learner(self.learner.id) + records:
            all_records.setdefault(record.dimension, []).append(record)
        assessment = self.storage.assessments_for_learner(self.learner.id).get(
            exercise.skill_id) or SkillAssessment(learner_id=self.learner.id, skill_id=exercise.skill_id)
        now = utcnow()
        for dim, recs in all_records.items():
            assessment.set_dim(dim, mastery.dimension_score(recs, now))
        assessment.evidence_count = sum(len(v) for v in all_records.values())
        assessment.independent_successes = sum(
            1 for v in all_records.values() for r in v if r.outcome == EvidenceOutcome.INDEPENDENT_SUCCESS)
        if exercise.skill_id in self._confidences:
            assessment.confidence_avg = float(self._confidences[exercise.skill_id])
        assessment.updated_at = now
        self.storage.upsert_assessment(assessment)

        events = [self._event(EventType.ANSWER_SUBMITTED,
                              {"exercise": exercise.id, "response": response[:500]}),
                  self._event(EventType.ANSWER_EVALUATED, evaluation.to_dict()),
                  self._event(EventType.PROBLEM_COMPLETED if evaluation.correct else EventType.PROBLEM_FAILED,
                              {"exercise": exercise.id, "score": evaluation.score,
                               "independent": attempt.independent_success})]
        if state.pending_action == "remediation" and evaluation.correct:
            events.append(self._event(EventType.REMEDIATION_COMPLETED, {"exercise": exercise.id}))

        snapshot = self._snapshot(state)
        # include the attempt being decided on — the engine must never see stale evidence
        snapshot.evidence.setdefault(exercise.skill_id, []).extend(records)
        decision = self.engine.decide_after_attempt(
            snapshot, exercise, evaluation.score, evaluation.correct, hints_used,
            attempt.solution_revealed,
            ai_recommended=None if low_confidence else evaluation.recommended_action,
            ai_missing_skill=None if low_confidence else evaluation.missing_skill)
        if low_confidence:
            decision.why.append("AI observation was low-confidence -> engine used deterministic "
                                "evidence only (AI stays advisory)")

        # unit completion bookkeeping
        if evaluation.correct and exercise.unit_id not in state.completed_unit_ids:
            unit_exs = self.curriculum.exercises_for_unit(exercise.unit_id)
            done = all(self._exercise_completed(state, e.id) for e in unit_exs if e.id != exercise.id)
            if done and unit_exs:
                state.completed_unit_ids.append(exercise.unit_id)
        if hints_used == 0:
            state.hints_used_current = 0
        state.hints_used_current = 0  # hints are per-attempt; reset for the next exercise
        # choose next exercise from the decision
        if decision.action == EngineAction.END_SESSION:
            state.current_exercise_id = None
            self.storage.record_interaction(attempt, records, assessment, state, events)
            return self._end_naturally(decision)

        next_exercise, next_generated, ai_degraded = self._exercise_for_decision(decision, state)
        if next_exercise is None:
            state.current_exercise_id = None
            self.storage.record_interaction(attempt, records, assessment, state, events)
            return self._end_naturally(EngineDecision(EngineAction.END_SESSION,
                                                      why=["no next exercise available"]))

        # budget guard: stop when time is exhausted; do not open a new unit late in the session
        remaining = self._remaining_minutes()
        if remaining is not None and (
                remaining <= 0 or
                (next_exercise.unit_id != exercise.unit_id
                 and remaining < self.config.engine.short_window_minutes)):
            state.current_exercise_id = None
            self.storage.record_interaction(attempt, records, assessment, state, events)
            decision.why.append(f"only {remaining:.1f} min remain -> stop at a natural point")
            return self._end_naturally(decision)

        state.current_skill_id = next_exercise.skill_id
        state.current_unit_id = next_exercise.unit_id
        state.current_exercise_id = next_exercise.id
        state.pending_action = decision.action.value
        self.storage.record_interaction(attempt, records, assessment, state, events)
        # present through the standard gate so a mid-session advance into a new skill's
        # teach unit shows the study text before its first check (same as session start)
        view = self._present_from_decision(decision, state, plan)
        view.evaluation = evaluation
        view.extra["ai_degraded"] = ai_degraded
        return view

    def _exercise_completed(self, state: LearnerState, exercise_id: str) -> bool:
        return any(a.exercise_id == exercise_id and a.completed
                   for a in self.storage.attempts_for_learner(self.learner.id))

    def _grade_mcq_locally(self, exercise: Exercise, response: str) -> EvaluationResult:
        from ..ai.builtin_provider import grade_mcq
        correct, score, feedback = grade_mcq(exercise, response)
        return EvaluationResult(correct=correct, score=score, understood_concept=correct,
                                identified_misconception=None, missing_skill=None,
                                recommended_action="acknowledge_advance" if correct else "micro_question",
                                hint_level=None, feedback=feedback, provider="deterministic",
                                model=None, prompt_version="local-mcq-v1")

    def _ai_context(self, exercise: Exercise, state: LearnerState) -> dict:
        unit = self.curriculum.units.get(exercise.unit_id)
        skill = self.curriculum.skills.get(exercise.skill_id)
        recent = [a for a in self.storage.attempts_for_learner(self.learner.id)
                  if a.skill_id == exercise.skill_id][-3:]
        return {
            "learner_name": self.learner.name,
            "skill_id": exercise.skill_id,
            "skill_title": skill.title if skill else exercise.skill_id,
            "unit_title": unit.title if unit else "",
            "unit_goal": unit.goal if unit else "",
            "theory_excerpt": (unit.theory[:600] if unit and unit.theory else ""),
            "hints_used": state.hints_used_current,
            "confidence": self._confidences.get(exercise.skill_id),
            "recent_attempts": [{"exercise": a.exercise_id, "correct": a.is_correct,
                                 "score": a.score, "hints": a.hints_used} for a in recent],
            "valid_skill_ids": sorted(self.curriculum.skills.keys()),
        }

    def _exercise_for_decision(self, decision: EngineDecision, state: LearnerState):
        """Resolve a decision to a concrete exercise; REMEDIATION generates fresh AI content."""
        if decision.action == EngineAction.REMEDIATION:
            skill = self.curriculum.skills.get(decision.skill_id)
            skill_title = skill.title if skill else decision.skill_id
            context = {"skill_title": skill_title, "micro_index": self._gen_counter,
                       "valid_skill_ids": sorted(self.curriculum.skills.keys())}
            import time as _time
            _t0 = _time.perf_counter()
            generated = self.ai.generate_controlled_remediation(decision.skill_id, context)
            self._log_ai("generate_controlled_remediation", generated,
                         int((_time.perf_counter() - _t0) * 1000),
                         request={"skill_id": decision.skill_id})
            self._gen_counter += 1
            fallback_unit = state.current_unit_id
            if fallback_unit is None or fallback_unit not in self.curriculum.units:
                units = self.curriculum.units_for_skill(decision.skill_id)
                fallback_unit = units[0].id if units else "adhoc"
            ex = Exercise(
                id=f"rem_{decision.skill_id}_{self._gen_counter:03d}",
                unit_id=fallback_unit,
                skill_id=decision.skill_id,
                interaction_type=InteractionType(generated.interaction_type),
                prompt=generated.prompt, payload=generated.payload,
                difficulty=generated.difficulty, source="ai",
                prompt_version=generated.prompt_version, requires_ai=False)
            self.storage.ensure_exercise(ex)
            # keep the decision truthful about what will actually be presented
            decision.exercise_id = ex.id
            decision.unit_id = ex.unit_id
            return ex, True, getattr(self.ai, "last_fallback_reason", None)
        if decision.exercise_id:
            exercise, generated = self._resolve_exercise(decision.exercise_id)
            if exercise is not None:
                # readiness gate (review amendment 3): problems require demonstrated capabilities
                ready, message = self.engine.check_readiness(self._snapshot(state), exercise)
                if ready:
                    return exercise, generated, getattr(self.ai, "last_fallback_reason", None)
                alternative = self.engine._alternative_exercise(self._snapshot(state), exercise)
                if alternative is not None and alternative.id != exercise.id:
                    decision.why.append(message)
                    decision.exercise_id = alternative.id
                    decision.unit_id = alternative.unit_id
                    return alternative, False, getattr(self.ai, "last_fallback_reason", None)
                decision.why.append(message)
                return exercise, generated, getattr(self.ai, "last_fallback_reason", None)
        # fall back to engine's own selection
        fresh = self.engine.select_next(self._snapshot(state))
        if fresh.exercise_id:
            exercise, generated = self._resolve_exercise(fresh.exercise_id)
            if exercise is not None:
                decision.skill_id = fresh.skill_id or exercise.skill_id
                decision.unit_id = fresh.unit_id or exercise.unit_id
                decision.exercise_id = exercise.id
                return exercise, generated, getattr(self.ai, "last_fallback_reason", None)
        return None, False, None

    # ------------------------------------------------------------ hints / confidence / explanation
    def request_hint(self) -> TurnView:
        state = self._state()
        exercise, _ = self._resolve_exercise(state.current_exercise_id or "")
        if exercise is None or self.session is None:
            return TurnView(kind="info", extra={"message": "No exercise in progress."})
        if state.hints_used_current >= exercise.max_hints + 1:
            return TurnView(kind="info", extra={
                "message": ("Assistance ladder exhausted (L5 partial solution given). "
                            "Type 'solution' for the complete reveal (L6) — the attempt "
                            "will count as assisted, not independent.")})
        context = self._ai_context(exercise, state)
        t0 = time.perf_counter()
        hint = self.ai.generate_hint(exercise, state.pending_action or "", state.hints_used_current, context)
        self._log_ai("generate_hint", hint, int((time.perf_counter() - t0) * 1000),
                     request={"exercise": exercise.id, "hints_used": state.hints_used_current})
        state.hints_used_current += 1
        self.storage.save_state(state)
        self.storage.append_event(self._event(EventType.HINT_REQUESTED,
                                              {"exercise": exercise.id, "level": state.hints_used_current}))
        self.storage.append_event(self._event(EventType.HINT_DELIVERED,
                                              {"exercise": exercise.id, "kind": hint.kind,
                                               "level": hint.level, "provider": hint.provider}))
        self.storage.record_hint_event(
            learner_id=self.learner.id, session_id=self.session.id, attempt_id=None,
            exercise_id=exercise.id, level=hint.level, kind=hint.kind,
            text=hint.text, provider=hint.provider)
        return TurnView(kind="exercise", exercise=exercise, hint=hint,
                        remaining_minutes=self._remaining_minutes(), daily=self._today_plan())

    def reveal_solution(self) -> TurnView:
        state = self._state()
        exercise, _ = self._resolve_exercise(state.current_exercise_id or "")
        if exercise is None:
            return TurnView(kind="info", extra={"message": "No exercise in progress."})
        solution = exercise.payload.get("solution") if isinstance(exercise.payload, dict) else None
        explanation = exercise.payload.get("explanation")
        state.pending_action = "solution_revealed"
        self.storage.save_state(state)
        if not solution and not explanation:
            return TurnView(kind="info", extra={"message": "No stored solution for this exercise — use 'hint' for guidance."})
        text = solution or f"Reference explanation: {explanation}"
        return TurnView(kind="info", extra={"message": text, "revealed": True})

    def report_confidence(self, skill_id: str, rating: int) -> TurnView:
        if not 1 <= rating <= 5:
            return TurnView(kind="info", extra={"message": "Confidence must be 1..5."})
        self._confidences[skill_id] = rating
        self._confidence_asked.add(skill_id)
        assessment = self.storage.assessments_for_learner(self.learner.id).get(skill_id)
        if assessment is not None:
            assessment.confidence_avg = float(rating)
            self.storage.upsert_assessment(assessment)
        self.storage.append_event(self._event(EventType.CONFIDENCE_REPORTED,
                                              {"skill": skill_id, "rating": rating}))
        return TurnView(kind="info", extra={"message": f"Confidence for '{skill_id}' recorded: {rating}/5."})

    def explain_current(self) -> TurnView:
        state = self._state()
        exercise, _ = self._resolve_exercise(state.current_exercise_id or "")
        if exercise is None:
            return TurnView(kind="info", extra={"message": "Nothing to explain yet."})
        unit = self.curriculum.units.get(exercise.unit_id)
        connect = (f"You are on '{exercise.id}' for skill '{exercise.skill_id}' "
                   f"({state.pending_action or 'working'}). Re-read the mechanism, then answer.")
        t0 = time.perf_counter()
        result = self.ai.explain(unit.theory if unit else None, connect)
        self._log_ai("explain", result, int((time.perf_counter() - t0) * 1000),
                     request={"exercise": exercise.id})
        text = result.text if hasattr(result, "text") else str(result)
        return TurnView(kind="info", extra={"message": text})

    # ------------------------------------------------------------ session plan
    def session_plan(self) -> dict:
        """Deterministic preview of what this session will cover: the next incomplete
        units in curriculum order (bounded by today's remaining unit target), with
        theory/question counts so the learner knows what is coming."""
        state = self._state()
        plan = self._today_plan()
        remaining_today = max(0, plan.target_units - plan.completed_units)
        assessments = self.storage.assessments_for_learner(self.learner.id)
        evidence: dict[str, list] = {}
        for record in self.storage.evidence_for_learner(self.learner.id):
            evidence.setdefault(record.skill_id, []).append(record)
        now = utcnow()
        from ..domain import mastery as _mastery
        items = []
        for skill in self.curriculum.ordered_skills():
            if remaining_today <= 0:
                break
            records = evidence.get(skill.id, [])
            if _mastery.derive_state(records, set(skill.evidence_requirements), now) in \
                    {_mastery.MasteryState.PRACTICED, _mastery.MasteryState.PROFICIENT,
                     _mastery.MasteryState.INDEPENDENT}:
                continue
            for unit in self.curriculum.units_for_skill(skill.id):
                if remaining_today <= 0:
                    break
                if unit.id in state.completed_unit_ids:
                    continue
                exercises = self.curriculum.exercises_for_unit(unit.id)
                if not exercises:
                    continue
                has_theory = bool(unit.theory) and \
                    f"theory:{unit.id}" not in state.completed_unit_ids
                items.append({
                    "skill": skill.id, "title": unit.title,
                    "type": unit.unit_type.value,
                    "theory": bool(has_theory),
                    "questions": len(exercises),
                })
                remaining_today -= 1
        total_questions = sum(i["questions"] for i in items)
        theory_blocks = sum(1 for i in items if i["theory"])
        mastered = sum(1 for skill in self.curriculum.ordered_skills()
                       if _mastery.derive_state(evidence.get(skill.id, []),
                                                set(skill.evidence_requirements), now)
                       in {_mastery.MasteryState.PROFICIENT, _mastery.MasteryState.INDEPENDENT})
        return {"items": items, "questions": total_questions,
                "theory_blocks": theory_blocks, "units": len(items),
                "mastered": mastered, "total_skills": len(self.curriculum.skills),
                "pace_budget": self.session.budget_minutes if self.session else None,
                "remaining_minutes": self._remaining_minutes()}

    # ------------------------------------------------------------ progress
    def progress_report(self) -> dict:
        assessments = self.storage.assessments_for_learner(self.learner.id)
        plan = self._today_plan()
        evidence_all = self.storage.evidence_for_learner(self.learner.id)
        now = utcnow()
        rows = []
        for skill in self.curriculum.ordered_skills():
            records = [r for r in evidence_all if r.skill_id == skill.id]
            state = mastery.derive_state(records, set(skill.evidence_requirements), now)
            rows.append({
                "skill": skill.id, "title": skill.title, "section": skill.section,
                "module": skill.module,
                "state": state.value,
                "evidence": len(records), "mastered": state in {mastery.MasteryState.PROFICIENT,
                                                                mastery.MasteryState.INDEPENDENT},
                "boundary": skill.is_boundary, "optional": skill.is_optional,
            })
        return {"skills": rows,
                "daily": {"date": str(plan.plan_date), "target_units": plan.target_units,
                          "completed_units": plan.completed_units, "status": plan.status}}


    # ---------------------------------------------------------- read-only snapshot (Slice 1B)
    def session_snapshot(self) -> TurnView:
        """Read-only snapshot of the authoritative current turn (design doc §3 #2, review R3).

        Performs NO writes: no events, no state saves, no session-row updates, no daily-plan
        creation. Used by GET /sessions/{id}; the HTTP contract requires zero writes.
        """
        state = self._state()
        session = self.storage.latest_active_session(self.learner.id)
        if session is None:
            return TurnView(kind="info", extra={"message": "No active session."})
        self.session = session  # in-memory context attach only; nothing persisted
        plan = self.storage.daily_plan(self.learner.id, date.today())  # read-only: never creates
        # pending theory outranks re-presenting the exercise: the check is still current,
        # but the study text must come first (same precedence as start/resume presentation)
        unit = self.curriculum.units.get(state.current_unit_id) if state.current_unit_id else None
        if unit is not None and unit.theory and not self._unit_theory_seen(state, unit.id):
            decision = EngineDecision(EngineAction.ADVANCE, skill_id=state.current_skill_id,
                                      unit_id=unit.id,
                                      why=["authoritative current turn (read-only snapshot): theory pending"])
            return TurnView(kind="theory", decision=decision, unit=unit,
                            remaining_minutes=self._remaining_minutes(), daily=plan)
        if state.current_exercise_id:
            exercise, generated = self._resolve_exercise(state.current_exercise_id)
            if exercise is not None:
                pending = state.pending_action
                note = None
                if pending == "solution_revealed":
                    action = EngineAction.REPEAT
                    note = "solution revealed — resubmission will count as assisted"
                else:
                    try:
                        action = EngineAction(pending) if pending else EngineAction.ADVANCE
                    except ValueError:
                        action = EngineAction.ADVANCE
                decision = EngineDecision(action, skill_id=state.current_skill_id,
                                          unit_id=state.current_unit_id, exercise_id=exercise.id,
                                          why=["authoritative current turn (read-only snapshot)"]
                                              + ([note] if note else []))
                return self._snapshot_exercise_view(decision, exercise, generated, session, plan)
        decision = self.engine.select_next(self._snapshot(state))
        if decision.action == EngineAction.END_SESSION or not decision.exercise_id:
            return TurnView(kind="ended", decision=decision,
                            extra={"message": "Session complete — " + decision.explanation})
        exercise, generated = self._resolve_exercise(decision.exercise_id)
        if exercise is None:
            return TurnView(kind="info", extra={"message": "No presentable activity in snapshot."})
        return self._snapshot_exercise_view(decision, exercise, generated, session, plan)

    def _snapshot_exercise_view(self, decision, exercise, generated, session, plan):
        unit = self.curriculum.units.get(exercise.unit_id)
        unit_exercises = self.curriculum.exercises_for_unit(exercise.unit_id)
        idx = next((i for i, e in enumerate(unit_exercises, 1) if e.id == exercise.id), None)
        extra = {"unit_position": (idx, len(unit_exercises))} if idx else {}
        return TurnView(kind="exercise", decision=decision, unit=unit, exercise=exercise,
                        generated=generated, remaining_minutes=self._remaining_minutes(),
                        daily=plan, confidence_request=None, extra=extra)

    # ------------------------------------------------------------ session export (AutoClaw coaching loop)
    def export_last_session(self, out_dir="exports") -> str:
        """Write the most recent session as a readable markdown transcript.

        Drop the file into a chat with AutoClaw and it can review your reasoning,
        misconceptions and hint usage like a human tutor — no API key involved.
        """
        from pathlib import Path
        session = self.storage.latest_session(self.learner.id)
        if session is None:
            raise RuntimeError("No sessions recorded yet.")
        attempts = {a.exercise_id: a for a in self.storage.attempts_for_learner(self.learner.id)
                    if a.session_id == session.id}
        events = self.storage.events_for_session(session.id)
        lines = [
            f"# Session {session.id} — {session.started_at:%Y-%m-%d %H:%M} UTC "
            f"({session.pace.value}, {session.status.value})",
            "", f"Learner: {self.learner.name} · budget {session.budget_minutes} min · "
            f"end reason: {session.end_reason or '-'}", "",
            "## Timeline", "",
        ]
        for ev in events:
            payload = ev.payload
            if ev.event_type.value == "ANSWER_EVALUATED":
                lines.append(f"- `{ev.event_type.value}` score={payload.get('score')} "
                             f"correct={payload.get('correct')} "
                             f"misconception={payload.get('identified_misconception')} "
                             f"missing_skill={payload.get('missing_skill')} "
                             f"provider={payload.get('provider')}")
            elif ev.event_type.value in {"ANSWER_SUBMITTED", "QUESTION_PRESENTED"}:
                preview = str(payload.get("response") or payload.get("exercise") or "")[:160]
                lines.append(f"- `{ev.event_type.value}` {payload.get('exercise', '')} {preview}")
            else:
                extra = {k: v for k, v in payload.items() if k in
                         {"exercise", "kind", "level", "rating", "skill", "action", "reason", "units_completed"}}
                lines.append(f"- `{ev.event_type.value}` {extra}")
        lines += ["", "## Attempts", ""]
        for ex_id, a in attempts.items():
            unit = self.curriculum.units.get(
                self.curriculum.exercises[ex_id].unit_id) if ex_id in self.curriculum.exercises else None
            lines += [f"### {ex_id} — skill `{a.skill_id}`"
                      + (f" ({unit.title})" if unit else ""),
                       f"- response: `{(a.response or '')[:400]}`",
                       f"- correct={a.is_correct} score={a.score} hints={a.hints_used} "
                       f"independent={a.independent_success} provider={a.ai_provider}",
                       f"- evaluation: {json.dumps(a.evaluation, ensure_ascii=False)[:500]}", ""]
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"session_{session.id}.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return str(path)


def build_curriculum() -> Curriculum:
    curriculum = Curriculum(SKILLS, PREREQS, UNITS, EXERCISES, TOPICS)
    errors = curriculum.validate()
    if errors:
        raise RuntimeError("curriculum invalid: " + "; ".join(errors))
    return curriculum
