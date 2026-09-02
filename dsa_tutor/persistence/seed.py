"""Curriculum seeding: mirror the code-encoded V0 curriculum into MySQL for inspection
and future evolution. Idempotent (upsert by primary key). The engine itself reads the
code-backed Curriculum object — deterministic and migration-free — while the DB copy
satisfies the data model and keeps the door open for DB-driven curriculum later."""
from __future__ import annotations

import json
from datetime import datetime

from ..content.curriculum_v0 import EXERCISES, PREREQS, SKILLS, TOPICS, UNITS
from ..domain.models import utcnow
from .db import Database


def seed_curriculum(database: Database) -> dict[str, int]:
    counts = {"topics": 0, "skills": 0, "prerequisites": 0, "units": 0, "exercises": 0}
    now = utcnow()
    with database.transaction() as conn:
        with conn.cursor() as cur:
            for t in TOPICS:
                cur.execute("INSERT IGNORE INTO topics (id, title, ordering) VALUES (%s,%s,%s)",
                            (t.id, t.title, t.ordering))
                counts["topics"] += 1
            for s in SKILLS:
                cur.execute(
                    "INSERT INTO skills (id, title, topic_id, ordering, section, module, description, "
                    "evidence_requirements, complexity, is_boundary, is_optional, required_dims) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE title=VALUES(title), ordering=VALUES(ordering), "
                    "section=VALUES(section), module=VALUES(module), description=VALUES(description), "
                    "evidence_requirements=VALUES(evidence_requirements), complexity=VALUES(complexity), "
                    "is_boundary=VALUES(is_boundary), is_optional=VALUES(is_optional), "
                    "required_dims=VALUES(required_dims)",
                    (s.id, s.title, s.topic_id, s.ordering, s.section, s.module, s.description,
                     json.dumps(sorted(t.value for t in s.evidence_requirements)),
                     json.dumps({d.value: lvl for d, lvl in s.complexity.items()}),
                     s.is_boundary, s.is_optional,
                     json.dumps(sorted(d.value for d in s.required_dimensions))))
                counts["skills"] += 1
            for p in PREREQS:
                cur.execute(
                    "INSERT IGNORE INTO skill_prerequisites (skill_id, prerequisite_skill_id, strength) "
                    "VALUES (%s,%s,%s)", (p.skill_id, p.prerequisite_skill_id, p.strength.value))
                counts["prerequisites"] += 1
            for u in UNITS:
                cur.execute(
                    "INSERT INTO learning_units (id, skill_id, title, goal, unit_type, ordering, "
                    "theory, required_dims) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE title=VALUES(title), goal=VALUES(goal), "
                    "unit_type=VALUES(unit_type), theory=VALUES(theory), "
                    "required_dims=VALUES(required_dims)",
                    (u.id, u.skill_id, u.title, u.goal, u.unit_type.value, u.ordering, u.theory,
                     json.dumps(sorted(d.value for d in u.required_dimensions))))
                counts["units"] += 1
            for e in EXERCISES:
                cur.execute(
                    "INSERT INTO exercises (id, unit_id, skill_id, ordering, role, scope, "
                    "required_capabilities, interaction_type, prompt, payload, "
                    "difficulty, language, hint_ladder, max_hints, requires_ai, source, "
                    "prompt_version, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE prompt=VALUES(prompt), payload=VALUES(payload), "
                    "ordering=VALUES(ordering), role=VALUES(role), scope=VALUES(scope), "
                    "required_capabilities=VALUES(required_capabilities), difficulty=VALUES(difficulty), "
                    "hint_ladder=VALUES(hint_ladder), requires_ai=VALUES(requires_ai)",
                    (e.id, e.unit_id, e.skill_id, e.ordering, e.role.value, e.scope.value,
                     json.dumps(sorted(t.value for t in e.required_capabilities)) if e.required_capabilities else None,
                     e.interaction_type.value, e.prompt,
                     json.dumps(e.payload, default=str), json.dumps(e.difficulty), e.language,
                     json.dumps(e.hint_ladder), e.max_hints, e.requires_ai, e.source,
                     e.prompt_version, now))
                counts["exercises"] += 1
    return counts
