"""Layer 7 curriculum acceptance criteria (Graph Slice A: Integration & Transfer).

Deterministic: asserts curriculum structure and executes stored solutions against
their own test payloads — no AI, no randomness.

Audit decisions encoded here (see the Layer 7 audit):
- NO new skill nodes: graph_problem_modeling, algorithm_selection,
  information_selection and transfer_to_unfamiliar_contexts are cross-cutting
  capabilities represented as integration units/evidence on EXISTING skills
  (recognizing_traversal, bfs_vs_dfs, traversal_application);
- Layer 7 teaches no new algorithm: every integration task composes Slice A
  techniques (components, BFS distance, path reconstruction, cycle detection,
  bipartite coloring, multi-source BFS, grid-as-graph);
- the selection map is exercised through justified free-form modeling, not a
  memorization table.
"""
import re

import pytest

from dsa_tutor.content.curriculum_v0 import EXERCISES, PREREQS, SKILLS, UNITS
from dsa_tutor.domain.models import (
    ActivityRole, ActivityScope, InteractionType, UnitType,
)

LAYER7_HOST_SKILLS = ("recognizing_traversal", "bfs_vs_dfs", "traversal_application")

FORBIDDEN_TOPICS = [r"\bdijkstra\b", r"\bbellman\b", r"\bdsu\b", r"\bscc\b", r"\bmst\b",
                    "topological", "0-1 bfs", r"\ba\s*\*\b", "articulation",
                    r"\bbridge", "flow", "matching", "bitmask", "segment tree", r"weighted"]


def exercises_for(skill_id):
    return [e for e in EXERCISES if e.skill_id == skill_id]


def integration_units(skill_id):
    return [u for u in UNITS if u.skill_id == skill_id and u.unit_type is UnitType.APPLY
            and "integration" in (u.title or "").lower()]


def integration_exercises(skill_id):
    units = integration_units(skill_id)
    ids = {u.id for u in units}
    return [e for e in EXERCISES if e.unit_id in ids]


# ---------------------------------------------------------------- structure
def test_layer7_adds_no_new_skills():
    """Layer 7 teaches no new algorithm and adds no permanent skill nodes."""
    assert len(SKILLS) == 56
    forbidden = {"graph_problem_modeling", "algorithm_selection", "information_selection",
                 "transfer_to_unfamiliar_contexts", "integration", "graph_modeling",
                 "slice_a_readiness", "integration_assessment"}
    ids = {s.id for s in SKILLS}
    assert not forbidden & ids
    # no new prerequisites were added by Layer 7 either (reuse, not re-wiring)
    assert all("integration" not in p.skill_id and "integration" not in p.prerequisite_skill_id
               for p in PREREQS)


def test_integration_units_exist_on_existing_skills():
    for sid in LAYER7_HOST_SKILLS:
        units = integration_units(sid)
        assert units, f"{sid}: no integration unit"
        exs = integration_exercises(sid)
        assert exs, f"{sid}: integration unit has no exercises"


def test_modeling_tasks_cover_the_full_selection_map():
    """Every Slice A technique must be reachable through the unlabeled stories:
    reachability, components, shortest distance, actual route, undirected cycle,
    two-group constraints, nearest source, grid-as-graph."""
    text = " ".join(
        ex.prompt.lower() + " " + ex.payload.get("reference_points", "").__str__()
        for sid in LAYER7_HOST_SKILLS for ex in integration_exercises(sid)
    )
    for concept in ["component", "fewest", "cycle", "two", "nearest", "implicit",
                    "grid", "bfs", "parent", "distance"]:
        assert concept in text, f"selection map concept '{concept}' not exercised"


def test_state_diagnostic_what_changes():
    """The high-value diagnostic: same traversal, different retained state
    (distance / parent / multi-source initialization)."""
    exs = [e for e in integration_exercises("bfs_vs_dfs")
           if "state" in (e.prompt or "").lower() or "distance" in (e.prompt or "").lower()]
    assert exs, "no 'what changes?' state-diagnostic activity"
    text = " ".join(e.prompt.lower() + " " + str(e.payload.get("reference_points")).lower() for e in exs)
    for state in ["distance", "parent", "distance 0"]:
        assert state in text, f"state diagnostic missing '{state}'"


def test_unfamiliar_context_implementation_is_concept_local():
    """The independent implementation task uses an unlabeled story but only Slice A
    machinery: an unweighted shortest distance via BFS."""
    ex = next(e for e in integration_exercises("traversal_application")
              if e.interaction_type is InteractionType.CODE_WRITING)
    assert ex.payload["function_name"] == "fewest_legs"
    assert ex.scope is ActivityScope.PROBLEM
    text = (ex.prompt or "").lower()
    assert "algorithm name is not given" in text or "no algorithm name" in text
    # the stored solution is the ordinary BFS distance pattern
    assert "distance" in ex.payload["solution"] and "deque" in ex.payload["solution"]


def test_layer7_exclusions():
    """No advanced algorithms leak into the integration layer."""
    for sid in LAYER7_HOST_SKILLS:
        skill = next(s for s in SKILLS if s.id == sid)
        text = " ".join([skill.id, skill.title, skill.description]).lower()
        for ex in exercises_for(sid):
            text += " " + (ex.prompt or "").lower()
            text += " " + " ".join(h["text"].lower() for h in ex.hint_ladder)
        for token in FORBIDDEN_TOPICS:
            assert not re.search(token, text), f"{sid}: excluded topic '{token}' leaked"


def test_integration_explanations_require_justification():
    """Selection must be justified, not memorized: free-form modeling tasks carry
    reference points that demand the WHY (level = distance, conflict = impossible,
    first wave = nearest, ...)."""
    modeling = [e for e in integration_exercises("recognizing_traversal")
                if e.interaction_type is InteractionType.FREE_FORM]
    assert len(modeling) >= 3
    for e in modeling:
        assert e.requires_ai and e.payload.get("reference_points")
        points = " ".join(p["text"].lower() for p in e.payload["reference_points"])
        assert any(w in points for w in ["because", ":", "first", "every", "repeated"]), \
            f"{e.id}: reference points do not justify the selection"


# ---------------------------------------------------------------- semantics
def test_fewest_legs_solution_passes_its_own_payload_tests():
    ex = next(e for e in integration_exercises("traversal_application")
              if e.interaction_type is InteractionType.CODE_WRITING)
    ns = {}
    exec(ex.payload["solution"], ns)
    fn = ns[ex.payload["function_name"]]
    for t in ex.payload["tests"]:
        args = {k: v for k, v in t.items() if k not in ("expected", "args")}
        assert fn(**args) == t["expected"], f"{ex.id} failed on {args}"


def test_fewest_legs_matches_layer2_bfs_distances():
    """The unfamiliar-context task must agree with the Layer 2 distance machinery."""
    from collections import deque

    def bfs_distances(graph, start):
        dist = [-1] * len(graph)
        dist[start] = 0
        q = deque([start])
        while q:
            v = q.popleft()
            for w in graph[v]:
                if dist[w] == -1:
                    dist[w] = dist[v] + 1
                    q.append(w)
        return dist

    ex = next(e for e in integration_exercises("traversal_application")
              if e.interaction_type is InteractionType.CODE_WRITING)
    ns = {}
    exec(ex.payload["solution"], ns)
    fn = ns["fewest_legs"]
    graphs = [
        [[1, 2], [3], [3, 4], [5], [5], []],
        [[1], [0, 2], [1], [4], [3], []],
        [[1, 2], [0], [0, 3], [2]],
    ]
    for graph in graphs:
        dist = bfs_distances(graph, 0)
        for target in range(len(graph)):
            assert fn(graph, 0, target) == dist[target]


# ---------------------------------------------------------------- runtime progression
def test_full_correct_run_serves_all_integration_units(service):
    """A fully correct run passes through the whole curriculum and enters every
    Layer 7 integration unit on the way. (The engine's minimal-evidence mastery
    may skip redundant later exercises of a unit's skill; entering the unit is the
    engine-honest guarantee — the remaining activities stay reachable via the
    variation pool.)"""
    from test_layer1_progression import drive, seed_mastery
    from dsa_tutor.domain.models import Pace

    seed_mastery(service, [s.id for s in service.curriculum.skills.values()
                           if s.id not in LAYER7_HOST_SKILLS])
    view = service.start_session(pace=Pace.NORMAL)
    seen_exercises = set()
    view, _ = drive(service, view, max_turns=800,
                    on_turn=lambda v: seen_exercises.add(v.exercise.id)
                    if v.kind == "exercise" else None)
    assert view.kind == "ended"
    for sid in LAYER7_HOST_SKILLS:
        entered = {e.id for e in integration_exercises(sid)} & seen_exercises
        assert entered, f"{sid}: integration unit never entered"
        first_ex = min(integration_exercises(sid), key=lambda e: e.ordering)
        assert first_ex.id in seen_exercises, \
            f"{sid}: integration unit's first activity not served"
    report = {row["skill"]: row for row in service.progress_report()["skills"]}
    for sid in LAYER7_HOST_SKILLS:
        assert report[sid]["mastered"], f"{sid} not mastered after a fully correct run"
