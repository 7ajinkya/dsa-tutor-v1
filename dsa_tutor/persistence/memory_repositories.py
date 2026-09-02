"""In-memory repositories — same interface as the MySQL ones.

Used by the learning engine tests and offline/demo mode: the engine must be
testable without real model calls AND without a database (spec 06 §11).
"""
from __future__ import annotations

from ..domain.models import (
    Attempt, DailyPlan, EvidenceRecord, Learner, LearnerState, SessionEvent,
    SkillAssessment, TutoringSession, utcnow,
)


class MemoryStorage:
    def __init__(self):
        self.learners: dict[str, Learner] = {}
        self.sessions: dict[int, TutoringSession] = {}
        self.events: list[SessionEvent] = []
        self.attempts: list[Attempt] = []
        self.evidence: list[EvidenceRecord] = []
        self.assessments: dict[tuple[int, str], SkillAssessment] = {}
        self.states: dict[int, LearnerState] = {}
        self.daily_plans: dict[tuple[int, str], DailyPlan] = {}
        self.generated_exercises: dict[str, object] = {}
        self.ai_interactions: list[dict] = []
        self.hint_events: list[dict] = []
        self._session_seq = 0
        self._attempt_seq = 0
        self._event_seq = 0

    # ------------------------------------------------ learners
    def get_or_create_learner(self, name: str) -> Learner:
        if name not in self.learners:
            self.learners[name] = Learner(id=len(self.learners) + 1, name=name)
        return self.learners[name]

    # ------------------------------------------------ sessions & events
    def create_session(self, session: TutoringSession) -> int:
        self._session_seq += 1
        session.id = self._session_seq
        self.sessions[session.id] = session
        return session.id

    def update_session(self, session: TutoringSession) -> None:
        self.sessions[session.id] = session

    def get_session(self, session_id: int) -> TutoringSession | None:
        return self.sessions.get(session_id)

    def latest_session(self, learner_id: int) -> TutoringSession | None:
        candidates = [s for s in self.sessions.values() if s.learner_id == learner_id]
        return max(candidates, key=lambda s: s.started_at) if candidates else None

    def latest_active_session(self, learner_id: int) -> TutoringSession | None:
        candidates = [s for s in self.sessions.values()
                      if s.learner_id == learner_id and s.status in {"active", "paused"}]
        return max(candidates, key=lambda s: s.started_at) if candidates else None

    def append_event(self, event: SessionEvent) -> None:
        self._event_seq += 1
        event.id = self._event_seq
        event.seq = event.seq or self._event_seq
        self.events.append(event)

    def events_for_session(self, session_id: int) -> list[SessionEvent]:
        return [e for e in self.events if e.session_id == session_id]

    # ------------------------------------------------ attempts & evidence
    def save_attempt(self, attempt: Attempt) -> int:
        self._attempt_seq += 1
        attempt.id = self._attempt_seq
        self.attempts.append(attempt)
        return attempt.id

    def attempts_for_learner(self, learner_id: int) -> list[Attempt]:
        return [a for a in self.attempts if a.learner_id == learner_id]

    def find_attempt_by_idempotency_key(self, learner_id: int, session_id: int,
                                        idempotency_key: str) -> Attempt | None:
        """Slice 1B: locate a prior submission by its idempotency identity (replay source)."""
        found = [a for a in self.attempts
                 if a.learner_id == learner_id and a.session_id == session_id
                 and a.idempotency_key == idempotency_key]
        return found[-1] if found else None

    def save_evidence(self, records: list[EvidenceRecord], learner_id: int) -> None:
        for r in records:
            r.created_at = r.created_at or utcnow()
            self.evidence.append(r)

    def evidence_for_learner(self, learner_id: int) -> list[EvidenceRecord]:
        return list(self.evidence)

    def upsert_assessment(self, assessment: SkillAssessment) -> None:
        self.assessments[(assessment.learner_id, assessment.skill_id)] = assessment

    def assessments_for_learner(self, learner_id: int) -> dict[str, SkillAssessment]:
        return {sid: a for (lid, sid), a in self.assessments.items() if lid == learner_id}

    # ------------------------------------------------ state & daily plan
    def save_state(self, state: LearnerState) -> None:
        state.updated_at = utcnow()
        self.states[state.learner_id] = state

    def load_state(self, learner_id: int) -> LearnerState | None:
        return self.states.get(learner_id)

    def upsert_daily_plan(self, plan: DailyPlan) -> None:
        self.daily_plans[(plan.learner_id, plan.plan_date.isoformat())] = plan

    def daily_plan(self, learner_id: int, plan_date) -> DailyPlan | None:
        return self.daily_plans.get((learner_id, plan_date.isoformat()))

    # ------------------------------------------------ atomic interaction record
    def record_interaction(self, attempt: Attempt, evidence: list[EvidenceRecord],
                           assessment: SkillAssessment, state: LearnerState,
                           events: list[SessionEvent]) -> int:
        """Persist one full interaction coherently (in-memory: sequential, test-equivalent)."""
        attempt_id = self.save_attempt(attempt)
        for r in evidence:
            r.attempt_id = attempt_id
        self.save_evidence(evidence, attempt.learner_id)
        self.upsert_assessment(assessment)
        self.save_state(state)
        for event in events:
            self.append_event(event)
        return attempt_id

    def ensure_exercise(self, exercise) -> None:
        """Register a generated (AI-source) exercise so attempts can reference it."""
        self.generated_exercises[exercise.id] = exercise

    def get_exercise(self, exercise_id: str):
        return self.generated_exercises.get(exercise_id)

    # ------------------------------------------------ AI interaction / hint logs
    def log_ai_interaction(self, learner_id: int, session_id: int | None, operation: str,
                           provider: str, model: str | None, prompt_version: str | None,
                           request: dict | None, response: dict | None,
                           validation_ok: bool, latency_ms: int | None,
                           keep_raw: bool = False) -> None:
        self.ai_interactions.append({
            "learner_id": learner_id, "session_id": session_id, "operation": operation,
            "provider": provider, "model": model, "prompt_version": prompt_version,
            "request": request if keep_raw else None, "response": response if keep_raw else None,
            "validation_ok": validation_ok, "latency_ms": latency_ms,
        })

    def record_hint_event(self, learner_id: int, session_id: int | None, attempt_id: int | None,
                          exercise_id: str, level: int, kind: str, text: str,
                          provider: str) -> None:
        self.hint_events.append({
            "learner_id": learner_id, "session_id": session_id, "exercise_id": exercise_id,
            "level": level, "kind": kind, "text": text[:2000], "provider": provider,
        })
