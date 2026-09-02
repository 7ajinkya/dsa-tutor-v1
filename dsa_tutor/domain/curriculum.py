"""Curriculum object: validated graph over skills/units/exercises with prerequisite logic."""
from __future__ import annotations

from collections import deque

from .models import (
    EvidenceType, LearningUnit, MasteryDimension, PrereqStrength, Skill,
    SkillPrerequisite, Exercise,
)


class CurriculumError(Exception):
    pass


class Curriculum:
    def __init__(self, skills, prerequisites, units, exercises, topics=None):
        self.skills: dict[str, Skill] = {s.id: s for s in skills}
        self.prerequisites: list[SkillPrerequisite] = list(prerequisites)
        self.units: dict[str, LearningUnit] = {u.id: u for u in units}
        self.exercises: dict[str, Exercise] = {e.id: e for e in exercises}
        self.topics = topics or []

    # ------------------------------------------------ lookups
    def skill(self, skill_id) -> Skill:
        return self._get(self.skills, skill_id, "skill")

    def unit(self, unit_id) -> LearningUnit:
        return self._get(self.units, unit_id, "unit")

    def exercise(self, exercise_id) -> Exercise:
        return self._get(self.exercises, exercise_id, "exercise")

    @staticmethod
    def _get(mapping, key, kind):
        try:
            return mapping[key]
        except KeyError:
            raise CurriculumError(f"unknown {kind}: {key}") from None

    def ordered_skills(self) -> list[Skill]:
        return sorted(self.skills.values(), key=lambda s: s.ordering)

    def units_for_skill(self, skill_id) -> list[LearningUnit]:
        return sorted([u for u in self.units.values() if u.skill_id == skill_id], key=lambda u: u.ordering)

    def exercises_for_unit(self, unit_id) -> list[Exercise]:
        return sorted([e for e in self.exercises.values() if e.unit_id == unit_id], key=lambda e: e.ordering)

    def core_prerequisites(self, skill_id) -> list[str]:
        return [p.prerequisite_skill_id for p in self.prerequisites
                if p.skill_id == skill_id and p.strength == PrereqStrength.CORE]

    def supporting_prerequisites(self, skill_id) -> list[str]:
        return [p.prerequisite_skill_id for p in self.prerequisites
                if p.skill_id == skill_id and p.strength == PrereqStrength.SUPPORTING]

    def all_prerequisites(self, skill_id) -> list[str]:
        return [p.prerequisite_skill_id for p in self.prerequisites if p.skill_id == skill_id]

    def prerequisite_closure(self, skill_id) -> set[str]:
        """All direct AND transitive prerequisites of a skill."""
        seen: set[str] = set()
        frontier = list(self.all_prerequisites(skill_id))
        while frontier:
            pid = frontier.pop()
            if pid in seen:
                continue
            seen.add(pid)
            frontier.extend(self.all_prerequisites(pid))
        return seen

    # ------------------------------------------------ validation
    def validate(self) -> list[str]:
        errors: list[str] = []
        for s in self.skills.values():
            errors.extend(s.validate())
        for p in self.prerequisites:
            if p.skill_id not in self.skills:
                errors.append(f"prereq target unknown: {p.skill_id}")
            if p.prerequisite_skill_id not in self.skills:
                errors.append(f"prereq source unknown: {p.prerequisite_skill_id}")
            if p.skill_id == p.prerequisite_skill_id:
                errors.append(f"self-prerequisite: {p.skill_id}")
        valid_skills = set(self.skills)
        for u in self.units.values():
            if u.skill_id not in valid_skills:
                errors.append(f"unit {u.id}: unknown skill {u.skill_id}")
        for e in self.exercises.values():
            errors.extend(e.validate(valid_skills))
            if e.unit_id not in self.units:
                errors.append(f"exercise {e.id}: unknown unit {e.unit_id}")
        errors.extend(self._validate_acyclic())
        errors.extend(self._validate_boundary())
        errors.extend(self._validate_coverage())
        errors.extend(self._validate_evidence_requirements())
        errors.extend(self._validate_activity_capability_mapping())
        return errors

    def _validate_evidence_requirements(self) -> list[str]:
        """Review hardening item 2: every required evidence type must be demonstrable
        through an actual authored activity of this skill — impossible skills are
        detected here, not at runtime."""
        errors = []
        for skill in self.skills.values():
            supported = {EvidenceType(e.role.value)
                         for u in self.units_for_skill(skill.id)
                         for e in self.exercises_for_unit(u.id)}
            for req in skill.evidence_requirements:
                if req not in supported:
                    errors.append(
                        f"skill {skill.id}: required evidence type '{req.value}' has no "
                        f"supporting learning activity (impossible skill)")
        return errors

    def _validate_activity_capability_mapping(self) -> list[str]:
        """Every activity must map to a valid evidence type, and every problem
        capability must be a valid evidence type (review hardening item 2)."""
        from .models import ActivityScope
        errors = []
        valid_types = {t.value for t in EvidenceType}
        for e in self.exercises.values():
            if e.role.value not in valid_types:
                errors.append(f"exercise {e.id}: role '{e.role.value}' is not a valid evidence type")
            for cap in e.required_capabilities:
                if cap.value not in valid_types:
                    errors.append(f"exercise {e.id}: capability '{cap.value}' is not a valid "
                                  f"evidence type")
            if e.scope is ActivityScope.PROBLEM and not e.required_capabilities:
                errors.append(f"exercise {e.id}: problem-scope activity must declare its "
                              f"required capabilities")
        return errors

    def _validate_acyclic(self) -> list[str]:
        indeg = {sid: 0 for sid in self.skills}
        adj: dict[str, list[str]] = {sid: [] for sid in self.skills}
        for p in self.prerequisites:  # edge prereq -> skill (learn prereq first)
            adj[p.prerequisite_skill_id].append(p.skill_id)
            indeg[p.skill_id] += 1
        q = deque([sid for sid, d in indeg.items() if d == 0])
        seen = 0
        while q:
            n = q.popleft()
            seen += 1
            for m in adj[n]:
                indeg[m] -= 1
                if indeg[m] == 0:
                    q.append(m)
        if seen != len(self.skills):
            return ["prerequisite graph contains a cycle"]
        return []

    def _validate_boundary(self) -> list[str]:
        errors = []
        boundary = [s for s in self.skills.values() if s.is_boundary]
        if len(boundary) != 1:
            errors.append(f"exactly one boundary skill expected, found {len(boundary)}")
        # nothing may depend on the boundary skill (nothing beyond V0)
        for p in self.prerequisites:
            if p.prerequisite_skill_id == "v0_readiness":
                errors.append(f"skill {p.skill_id} depends on the V0 boundary — advanced topic leak")
        return errors

    def _validate_coverage(self) -> list[str]:
        errors = []
        for sid, s in self.skills.items():
            units = self.units_for_skill(sid)
            if not units:
                errors.append(f"skill {sid} has no learning units")
                continue
            has_exercise = any(self.exercises_for_unit(u.id) for u in units)
            if not has_exercise:
                errors.append(f"skill {sid} has units but no exercises")
            for dim in s.required_dimensions:
                covered = any(dim in u.required_dimensions or dim in s.required_dimensions
                              for u in units)
                if not covered and dim != MasteryDimension.TRANSFER:
                    errors.append(f"skill {sid}: required dimension {dim.value} not covered by any unit")
        return errors

    # ------------------------------------------------ topological order (prereq-first)
    def learning_order(self) -> list[str]:
        indeg = {sid: 0 for sid in self.skills}
        adj: dict[str, list[str]] = {sid: [] for sid in self.skills}
        for p in self.prerequisites:
            adj[p.prerequisite_skill_id].append(p.skill_id)
            indeg[p.skill_id] += 1
        # deterministic: process in curriculum order
        q = deque([s.id for s in self.ordered_skills() if indeg[s.id] == 0])
        order: list[str] = []
        while q:
            n = q.popleft()
            order.append(n)
            for m in adj[n]:
                indeg[m] -= 1
                if indeg[m] == 0:
                    q.append(m)
        if len(order) != len(self.skills):
            raise CurriculumError("cannot produce learning order: prerequisite cycle")
        return order
