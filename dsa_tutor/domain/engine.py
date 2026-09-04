"""The deterministic learning engine (spec 03).

Owns: learner state interpretation, prerequisite readiness, mastery aggregation calls,
session budgeting, and final next-step selection. NEVER calls the AI and NEVER does I/O:
all inputs are passed in, all outputs are EngineDecision values — fully testable offline.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from .curriculum import Curriculum
from .mastery import PROFICIENT_RECENCY_DAYS, derive_state, is_state_at_least, MasteryState
from .models import (
    EngineAction, EngineDecision, EvidenceOutcome, EvidenceRecord, Exercise,
    InteractionType, LearnerState, MasteryDimension, Pace, SkillAssessment,
    TutoringSession, utcnow,
)

STRUGGLE_FAILURES = 2          # consecutive failed attempts that signal struggle
EXCELLENT_STREAK = 3           # consecutive independent excellent results -> raise difficulty
EXCELLENT_SCORE = 0.9
PREREQ_READINESS_FLOOR = 0.5   # supporting minimum for the *next* skill's core prereqs


@dataclass
class EngineSnapshot:
    """Everything the engine needs for one decision — assembled by the application layer."""
    state: LearnerState
    assessments: dict[str, SkillAssessment]
    evidence: dict[str, list[EvidenceRecord]]      # skill_id -> records
    session: TutoringSession | None
    remaining_minutes: float | None = None         # budget remaining right now
    recent_scores: list[float] | None = None       # last attempts on the current skill (newest last)


class LearningEngine:
    def __init__(self, curriculum: Curriculum, config):
        self.curriculum = curriculum
        self.config = config  # EngineConfig

    # ------------------------------------------------------------- helpers
    def _dim_scores(self, snapshot: EngineSnapshot, skill_id: str) -> dict[MasteryDimension, float]:
        skill = self.curriculum.skill(skill_id)
        by_dim: dict[MasteryDimension, list[EvidenceRecord]] = {}
        for r in snapshot.evidence.get(skill_id, []):
            by_dim.setdefault(r.dimension, []).append(r)
        now = utcnow()
        return {d: dimension_score(by_dim.get(d, []), now) for d in MasteryDimension}

    def _skill_mastered(self, snapshot: EngineSnapshot, skill_id: str) -> bool:
        """Mastery decision via evidence predicates (review hardening item 1):
        uses skill.evidence_requirements — never required_dimensions or numeric thresholds."""
        skill = self.curriculum.skill(skill_id)
        state = derive_state(snapshot.evidence.get(skill_id, []),
                             set(skill.evidence_requirements), utcnow())
        return state in {MasteryState.PROFICIENT, MasteryState.INDEPENDENT}

    def _state(self, snapshot: EngineSnapshot, skill_id: str) -> MasteryState:
        skill = self.curriculum.skill(skill_id)
        return derive_state(snapshot.evidence.get(skill_id, []),
                            set(skill.evidence_requirements), utcnow())

    def _all_core_done(self, snapshot: EngineSnapshot, order: list[str], optional_id: str) -> bool:
        """An optional skill is served only once every non-optional skill is mastered."""
        return all(self._skill_mastered(snapshot, sid) for sid in order
                   if sid != optional_id and not self.curriculum.skill(sid).is_optional)

    def _prereq_blockers(self, snapshot: EngineSnapshot, skill_id: str) -> list[str]:
        """Core prereqs with insufficient evidence (review amendment 1: predicates, not
        numbers). A prereq is ready once its required evidence types each have >=1 success
        (state PRACTICED or beyond)."""
        blockers = []
        now = utcnow()
        for pid in self.curriculum.core_prerequisites(skill_id):
            prereq_skill = self.curriculum.skill(pid)
            state = derive_state(snapshot.evidence.get(pid, []),
                                 set(prereq_skill.evidence_requirements), now)
            if state in {MasteryState.NOT_SEEN, MasteryState.INTRODUCED, MasteryState.DEVELOPING}:
                blockers.append(pid)
        return blockers

    def _next_unit_needing_work(self, snapshot: EngineSnapshot, skill_id: str):
        """First unmastered unit of the skill, preferring ones not yet completed."""
        units = self.curriculum.units_for_skill(skill_id)
        for unit in units:
            if unit.id in snapshot.state.completed_unit_ids:
                continue
            return unit
        return units[0] if units else None  # all completed: revisit first unit (repeat/variation)

    def _first_exercise_of(self, unit_id: str, state: LearnerState | None = None):
        exs = self.curriculum.exercises_for_unit(unit_id)
        if state is not None:
            # pick the exercise with fewest attempts (variation over grind)
            exs = sorted(exs, key=lambda e: state.total_attempts_for(e.id))
        return exs[0] if exs else None

    # ------------------------------------------------------------- session start
    def select_next(self, snapshot: EngineSnapshot) -> EngineDecision:
        """Choose the smallest useful next learning step from scratch state."""
        why: list[str] = []
        order = self.curriculum.learning_order()

        # budget guard: too little time left -> prefer a short check or a natural stop
        if snapshot.remaining_minutes is not None:
            if snapshot.remaining_minutes <= 0:
                return EngineDecision(EngineAction.END_SESSION,
                                      why=["session budget exhausted", "stop at natural boundary"])
            if snapshot.remaining_minutes < self.config.short_window_minutes:
                why.append(f"only {snapshot.remaining_minutes:.1f} min left "
                           f"(< {self.config.short_window_minutes} short window)")

        for skill_id in order:
            if self._skill_mastered(snapshot, skill_id):
                continue
            # placement bypass (RC-23): a skill whose evidence already reaches PRACTICED
            # is not re-taught — bypass is evidence-based, never claim-based
            if self._state(snapshot, skill_id) in {MasteryState.PRACTICED,
                                                   MasteryState.PROFICIENT,
                                                   MasteryState.INDEPENDENT}:
                continue
            if self.curriculum.skill(skill_id).is_optional and not self._all_core_done(snapshot, order, skill_id):
                continue
            why.append(f"skill '{skill_id}' not yet mastered "
                       f"(required dims: {', '.join(d.value for d in self.curriculum.skill(skill_id).required_dimensions)})")
            blockers = self._prereq_blockers(snapshot, skill_id)
            if blockers:
                pid = blockers[0]
                prereq_state = self._state(snapshot, pid)
                why.append(f"core prerequisite '{pid}' has insufficient evidence "
                           f"(state {prereq_state.value}); revisit it while staying on task")
                unit = self._next_unit_needing_work(snapshot, pid)
                ex = self._first_exercise_of(unit.id, snapshot.state) if unit else None
                return EngineDecision(EngineAction.PREREQUISITE_REVISIT, skill_id=pid,
                                      unit_id=unit.id if unit else None,
                                      exercise_id=ex.id if ex else None, why=why)
            unit = self._next_unit_needing_work(snapshot, skill_id)
            if unit is None:
                why.append("no units available; skipping skill")
                continue
            ex = self._first_exercise_of(unit.id, snapshot.state)
            if ex is None:
                why.append(f"unit {unit.id} has no exercises")
                continue
            action = EngineAction.ADVANCE if skill_id == snapshot.state.current_skill_id or \
                snapshot.state.current_skill_id is None else EngineAction.ADVANCE
            why.append(f"selected unit '{unit.id}' ({unit.unit_type.value}) of skill '{skill_id}'")
            return EngineDecision(action, skill_id=skill_id, unit_id=unit.id,
                                  exercise_id=ex.id, why=why)

        why.append("all V0 skills mastered — curriculum complete")
        return EngineDecision(EngineAction.END_SESSION, why=why)

    # ------------------------------------------------------------- after an attempt
    def decide_after_attempt(self, snapshot: EngineSnapshot, exercise: Exercise,
                             score: float, is_correct: bool | None, hints_used: int,
                             solution_revealed: bool,
                             ai_recommended: str | None = None,
                             ai_missing_skill: str | None = None) -> EngineDecision:
        why: list[str] = []
        state = snapshot.state
        skill_id = exercise.skill_id
        ex_id = exercise.id
        state.exercise_failures.setdefault(ex_id, 0)
        state.unit_attempt_counts[ex_id] = state.unit_attempt_counts.get(ex_id, 0) + 1

        if ai_missing_skill and ai_missing_skill in self.curriculum.skills \
                and ai_missing_skill != skill_id:
            blockers = self._prereq_blockers(snapshot, skill_id)
            if ai_missing_skill in blockers or ai_missing_skill in self.curriculum.all_prerequisites(skill_id):
                why.append(f"AI observation links failure to prerequisite '{ai_missing_skill}'")

        if is_correct:
            state.exercise_failures[ex_id] = 0
            if state.difficultylevel_shift < 0:
                # a success ends the reduced-difficulty period; keeping the -1 preference
                # forever would lock the learner out of the non-MCQ activities that the
                # remaining evidence requirements need
                state.difficultylevel_shift = 0
                why.append("success after intervention -> reduced-difficulty preference ends")
            excellent = score >= EXCELLENT_SCORE and hints_used == 0 and not solution_revealed
            why.append(f"correct attempt (score {score:.2f}, hints {hints_used}, "
                       f"independent={str(hints_used == 0 and not solution_revealed).lower()})")

            if not excellent and (hints_used > 0 or solution_revealed):
                why.append("assisted success is learning evidence but not independent mastery -> vary the task")
                return self._variation_or_repeat(snapshot, exercise, why)

            skill_state = self._state(snapshot, skill_id)
            why.append(f"evidence state of '{skill_id}': {skill_state.value}")

            if excellent and skill_state in {MasteryState.PROFICIENT, MasteryState.INDEPENDENT}:
                if state.difficultylevel_shift < 1 and self._has_harder_variant(exercise):
                    state.difficultylevel_shift += 1
                    why.append("strong independent streak -> increase difficulty with a harder variation")
                    return EngineDecision(EngineAction.INCREASE_DIFFICULTY, skill_id=skill_id,
                                          unit_id=exercise.unit_id, exercise_id=ex_id, why=why)
                if self._skill_mastered(snapshot, skill_id):
                    nxt = self._next_skill_unit(snapshot, skill_id, why)
                    return nxt
                why.append("mastery threshold not yet reached across all evidence -> one more variation")
                return self._variation_or_repeat(snapshot, exercise, why)

            if self._skill_mastered(snapshot, skill_id):
                return self._next_skill_unit(snapshot, skill_id, why)

            why.append("skill not yet consolidated -> keep practicing with a variation")
            return self._variation_or_repeat(snapshot, exercise, why)

        # ---- failure path: the struggle ladder (spec 01 §8 / 04 §5)
        # Amendment RC-12: three attempts are an INTERVENTION threshold, not a failure limit.
        state.exercise_failures[ex_id] = state.consecutive_failures_for(ex_id) + 1
        failures = state.consecutive_failures_for(ex_id)
        why.append(f"attempt failed (score {score:.2f}); consecutive failures on this exercise: {failures}")

        if ai_recommended and ai_recommended not in {"retry", "hint_needed"}:
            why.append(f"AI recommended action: {ai_recommended}")

        if failures == 1:
            why.append("struggle detected -> start remediation with a smaller micro-question")
            return EngineDecision(EngineAction.REMEDIATION, skill_id=skill_id,
                                  unit_id=exercise.unit_id, exercise_id=ex_id, why=why)

        if failures >= STRUGGLE_FAILURES:
            missing = ai_missing_skill
            if missing and missing in self.curriculum.prerequisite_closure(skill_id):
                why.append(f"recurring failure linked to prerequisite '{missing}' -> "
                           f"brief prerequisite revisit, then connect back to the current task")
                return EngineDecision(EngineAction.PREREQUISITE_REVISIT, skill_id=missing,
                                      unit_id=exercise.unit_id, exercise_id=ex_id, why=why)
            if failures >= 3:
                # INTERVENTION threshold (not a punishment): reassess before continuing.
                improving = self._trend_improving(snapshot, skill_id)
                if improving:
                    why.append("attempt 3 triggers reassessment, but evidence shows progress "
                               "-> continue with a variation at the same difficulty")
                    return self._variation_or_repeat(snapshot, exercise, why)
                weak_state = self._state(snapshot, skill_id) in {
                    MasteryState.NOT_SEEN, MasteryState.INTRODUCED, MasteryState.DEVELOPING}
                if weak_state:
                    state.difficultylevel_shift = -1
                    why.append("intervention: no meaningful progress -> reduce difficulty "
                               "and serve a smaller reasoning step")
                    # a smaller step must actually be a different, simpler activity —
                    # re-serving the identical exercise would trap the learner
                    smaller = self._alternative_exercise(snapshot, exercise)
                    return EngineDecision(
                        EngineAction.REDUCE_DIFFICULTY, skill_id=skill_id,
                        unit_id=smaller.unit_id if smaller else exercise.unit_id,
                        exercise_id=smaller.id if smaller else ex_id, why=why)
                why.append("intervention: cool down this activity for now -> serve a "
                           "smaller variation; the original may return later in the session")
                return self._variation_or_repeat(snapshot, exercise, why)
            why.append("repeated failure -> repeat the unit with a simpler variation")
            return EngineDecision(EngineAction.REPEAT, skill_id=skill_id,
                                  unit_id=exercise.unit_id, exercise_id=ex_id, why=why)

        why.append("single failure -> retry with a variation")
        return self._variation_or_repeat(snapshot, exercise, why)

    def _trend_improving(self, snapshot: EngineSnapshot, skill_id: str) -> bool:
        """Meaningful progress detection (amendment RC-12): the newest attempt scored
        better than the previous one. Deterministic, from caller-supplied history."""
        scores = snapshot.recent_scores or []
        return len(scores) >= 2 and scores[-1] > scores[-2]

    # ------------------------------------------------------- readiness gate (RC-13)
    def check_readiness(self, snapshot: EngineSnapshot,
                        exercise: Exercise) -> tuple[bool, str]:
        """Explicit evidence-requirement readiness (review amendment 3): a problem
        activity lists the evidence capabilities it requires; readiness compares those
        requirements with demonstrated INDEPENDENT evidence — never an ordinal state score."""
        from .models import ActivityScope, EvidenceOutcome
        if exercise.scope is not ActivityScope.PROBLEM or not exercise.required_capabilities:
            return True, ""
        # capabilities may be demonstrated anywhere in the skill's foundation: the skill
        # itself or its prerequisite closure (its own non-problem activities cannot
        # always evidence every required capability, e.g. IMPLEMENTATION or TRACE)
        records = list(snapshot.evidence.get(exercise.skill_id, []))
        for pid in self.curriculum.prerequisite_closure(exercise.skill_id):
            records.extend(snapshot.evidence.get(pid, []))
        now = utcnow()
        missing = []
        for cap in exercise.required_capabilities:
            has_independent = any(
                r.evidence_type is cap and r.outcome is EvidenceOutcome.INDEPENDENT_SUCCESS
                and r.created_at >= now - timedelta(days=PROFICIENT_RECENCY_DAYS)
                for r in records)
            if not has_independent:
                guided = any(r.evidence_type is cap and r.outcome in
                             {EvidenceOutcome.ASSISTED_SUCCESS, EvidenceOutcome.PARTIAL_SUCCESS}
                             for r in records)
                missing.append((cap.value, "only guided attempts" if guided else "no attempts"))
        if not missing:
            return True, ""
        detail = "; ".join(f"{cap}: {note}" for cap, note in missing)
        message = (f"This problem requires independent {', '.join(c for c, _ in missing)}, "
                   f"but your current evidence shows {detail}. "
                   "A smaller activity is therefore selected first.")
        return False, message

    # ------------------------------------------------------------- utilities
    def _variation_or_repeat(self, snapshot: EngineSnapshot, exercise: Exercise,
                             why: list[str]) -> EngineDecision:
        alt = self._alternative_exercise(snapshot, exercise)
        action = EngineAction.VARIATION if alt and alt.id != exercise.id else EngineAction.REPEAT
        if alt:
            why.append(f"next exercise: '{alt.id}' ({alt.interaction_type.value})")
            return EngineDecision(action, skill_id=exercise.skill_id,
                                  unit_id=alt.unit_id, exercise_id=alt.id, why=why)
        why.append("no alternative exercise available -> repeat current exercise")
        return EngineDecision(EngineAction.REPEAT, skill_id=exercise.skill_id,
                              unit_id=exercise.unit_id, exercise_id=exercise.id, why=why)

    def _alternative_exercise(self, snapshot: EngineSnapshot, exercise: Exercise):
        pool = [e for e in self.curriculum.exercises_for_unit(exercise.unit_id)
                if e.id != exercise.id]
        pool += [e for u in self.curriculum.units_for_skill(exercise.skill_id)
                 for e in self.curriculum.exercises_for_unit(u.id) if e.id != exercise.id]
        if not pool:
            return None
        state = snapshot.state
        # The difficulty shift is a PREFERENCE, not a filter: it reorders equal-attempt
        # alternatives but must never permanently exclude an activity type. A hard filter
        # would starve the micro activities that a skill's required evidence types
        # (e.g. recognition/trace) depend on, making mastery unreachable.
        if state.difficultylevel_shift < 0:
            preferred = {InteractionType.MCQ, InteractionType.OUTPUT_PREDICTION}
        elif state.difficultylevel_shift > 0:
            preferred = {InteractionType.CODE_WRITING, InteractionType.FREE_FORM,
                         InteractionType.COMPLEXITY_QUESTION}
        else:
            preferred = set()
        pool.sort(key=lambda e: (state.total_attempts_for(e.id),
                                 0 if e.interaction_type in preferred else 1,
                                 e.ordering, e.id))
        return pool[0]

    def _has_harder_variant(self, exercise: Exercise) -> bool:
        pool = [e for e in self.curriculum.exercises_for_unit(exercise.unit_id)
                if e.id != exercise.id]
        pool += [e for u in self.curriculum.units_for_skill(exercise.skill_id)
                 for e in self.curriculum.exercises_for_unit(u.id) if e.id != exercise.id]
        return any(e.interaction_type in {InteractionType.CODE_WRITING,
                                          InteractionType.FREE_FORM,
                                          InteractionType.COMPLEXITY_QUESTION} for e in pool)

    def _next_skill_unit(self, snapshot: EngineSnapshot, current_skill_id: str,
                         why: list[str]) -> EngineDecision:
        """Current skill mastered: mark unit complete and move on (respecting the boundary)."""
        order = self.curriculum.learning_order()
        idx = order.index(current_skill_id)
        why.append(f"skill '{current_skill_id}' mastered on all required dimensions")
        for nxt in order[idx + 1:]:
            if self._skill_mastered(snapshot, nxt):
                continue
            skill = self.curriculum.skill(nxt)
            if skill.is_boundary:
                why.append(f"reached the V0 boundary skill '{nxt}' — nothing beyond V0")
            blockers = self._prereq_blockers(snapshot, nxt)
            if blockers:
                pid = blockers[0]
                why.append(f"prerequisite '{pid}' below readiness floor -> revisit")
                unit2 = self._next_unit_needing_work(snapshot, pid)
                ex = self._first_exercise_of(unit2.id, snapshot.state) if unit2 else None
                return EngineDecision(EngineAction.PREREQUISITE_REVISIT, skill_id=pid,
                                      unit_id=unit2.id if unit2 else None,
                                      exercise_id=ex.id if ex else None, why=why)
            unit2 = self._next_unit_needing_work(snapshot, nxt)
            if unit2 is None:
                continue
            ex = self._first_exercise_of(unit2.id, snapshot.state)
            if ex is None:
                continue
            why.append(f"advance to '{nxt}' — unit '{unit2.id}'")
            return EngineDecision(EngineAction.ADVANCE, skill_id=nxt, unit_id=unit2.id,
                                  exercise_id=ex.id, why=why)
        why.append("all skills complete -> end session with a natural stopping point")
        return EngineDecision(EngineAction.END_SESSION, why=why)

    # ------------------------------------------------------------- session end
    def recommend_stop(self, snapshot: EngineSnapshot, reason_detail: str) -> EngineDecision:
        return EngineDecision(EngineAction.END_SESSION,
                              why=[reason_detail, "persist exact state for resume"])
