"""Layer 5 curriculum acceptance criteria (Graph Slice A: Multi-Source BFS).

All tests are deterministic: they assert curriculum structure (skills, prereqs,
units, evidence) and execute the stored reference solutions against their own
test payloads — no AI, no randomness.

Audit decisions encoded here (see the Layer 5 audit):
- exactly THREE new permanent skills (the approved compact set):
  multi_source_initialization, nearest_source_distance, multi_source_bfs;
- simultaneous expansion is NOT a skill: it is the mental model carried by
  multi_source_initialization's theory/tracing evidence;
- repeated-BFS comparison is NOT a skill: it lives as free-form explanation
  evidence inside nearest_source_distance;
- the layer deliberately reuses Layer 2 BFS distance machinery via core
  prerequisites (bfs_distance, bfs_implementation) — no duplicate BFS skill;
- sourceless components / single-source reduction / duplicate sources are edge
  conventions, exercised inside multi_source_bfs evidence, not separate skills.
"""
import re

import pytest

from dsa_tutor.content.curriculum_v0 import EXERCISES, PREREQS, SKILLS, UNITS
from dsa_tutor.domain.models import (
    ActivityRole, ActivityScope, InteractionType, PrereqStrength, UnitType,
)

LAYER5_SKILLS = ("multi_source_initialization", "nearest_source_distance",
                 "multi_source_bfs")


def core_prereqs(skill_id):
    return {p.prerequisite_skill_id for p in PREREQS
            if p.skill_id == skill_id and p.strength is PrereqStrength.CORE}


def all_prereqs(skill_id):
    return {p.prerequisite_skill_id for p in PREREQS if p.skill_id == skill_id}


def exercises_for(skill_id):
    return [e for e in EXERCISES if e.skill_id == skill_id]


def code_writing_for(skill_id, fn_name):
    return next(e for e in exercises_for(skill_id)
                if e.interaction_type is InteractionType.CODE_WRITING
                and e.payload["function_name"] == fn_name)


# ---------------------------------------------------------------- structure
def test_exactly_three_layer5_skills_added():
    ids = {s.id for s in SKILLS}
    assert set(LAYER5_SKILLS) <= ids
    # no duplicate/granular candidate nodes leaked in: simultaneous expansion,
    # repeated-BFS merging, propagation stories and Dijkstra variants must not
    # be standalone skills
    forbidden = {"simultaneous_expansion", "repeated_bfs", "wave_expansion",
                 "multi_source_dijkstra", "nearest_vertex", "propagation",
                 "voronoi", "dynamic_sources"}
    assert not forbidden & ids


def test_layer5_prereq_ladder(curriculum):
    # the conceptual ladder must hold in the engine's prerequisite-first order:
    # BFS distance -> initialization -> nearest-source reasoning -> multi-source BFS
    order = curriculum.learning_order()
    for a, b in [("bfs_distance", "multi_source_initialization"),
                 ("bfs_implementation", "multi_source_initialization"),
                 ("multi_source_initialization", "nearest_source_distance"),
                 ("nearest_source_distance", "multi_source_bfs"),
                 ("bfs_implementation", "multi_source_bfs")]:
        assert order.index(a) < order.index(b), f"{a} must precede {b}"
    # reuse, not duplication: existing BFS concepts are the prerequisites
    assert {"bfs_distance", "bfs_implementation"} <= core_prereqs("multi_source_initialization")
    assert {"multi_source_initialization"} <= core_prereqs("nearest_source_distance")
    assert {"nearest_source_distance", "bfs_implementation"} <= core_prereqs("multi_source_bfs")
    # layer-1 reasoning reused as supporting links, never duplicated
    assert "component_enumeration" in all_prereqs("multi_source_bfs")
    assert "connectedness" in all_prereqs("nearest_source_distance")
    # no Layer 5 skill may hang off the V0 boundary
    for sid in LAYER5_SKILLS:
        assert "v0_readiness" not in core_prereqs(sid)


def test_layer5_evidence_progression():
    """Recognition -> tracing -> code completion -> independent implementation ->
    edge-case reasoning -> transfer, per the approved progression."""
    for sid in LAYER5_SKILLS:
        exs = exercises_for(sid)
        assert any(e.interaction_type is InteractionType.MCQ for e in exs), \
            f"{sid}: no recognition evidence"
    # all three skills carry wave/queue tracing evidence
    for sid in LAYER5_SKILLS:
        assert any(e.interaction_type in {InteractionType.CODE_TRACING,
                                          InteractionType.OUTPUT_PREDICTION}
                   for e in exercises_for(sid)), f"{sid}: no tracing evidence"
    # repeated-BFS comparison lives as explanation evidence, not a skill
    nearest = exercises_for("nearest_source_distance")
    assert any(e.interaction_type is InteractionType.FREE_FORM and e.requires_ai
               for e in nearest), "no repeated-vs-multi-source explanation evidence"
    # the synthesis skill: guided completion + from-scratch implementation
    writers = [e for e in exercises_for("multi_source_bfs")
               if e.interaction_type is InteractionType.CODE_WRITING]
    assert {e.payload["function_name"] for e in writers} == \
        {"nearest_distances_completed", "multi_source_distances"}
    starters = [w.payload["starter"] for w in writers]
    assert any("# line" in s for s in starters), "no guided completion activity"
    assert any("# line" not in s for s in starters), "no from-scratch activity"
    # independent transfer under multi_source_bfs (apply unit)
    apply_units = [u for u in UNITS
                   if u.skill_id == "multi_source_bfs" and u.unit_type is UnitType.APPLY]
    assert apply_units and any(
        e.interaction_type is InteractionType.FREE_FORM and e.role is ActivityRole.APPLICATION
        for u in apply_units for e in EXERCISES if e.unit_id == u.id)


def test_layer5_exclusions():
    """Explicit spec exclusions must not leak into Layer 5 content."""
    forbidden = [r"\bdijkstra\b", r"\bvoronoi\b", "0-1 bfs", "time-dependent",
                 "dynamic source", "weighted multi-source", "dijkstra multi"]
    for sid in LAYER5_SKILLS:
        skill = next(s for s in SKILLS if s.id == sid)
        text = " ".join([skill.id, skill.title, skill.description]).lower()
        units = [u for u in UNITS if u.skill_id == sid]
        text += " ".join((u.title or "") + " " + (u.goal or "") for u in units).lower()
        for ex in exercises_for(sid):
            text += " " + ex.prompt.lower()
            text += " " + " ".join(h["text"].lower() for h in ex.hint_ladder)
        for token in forbidden:
            assert not re.search(token, text), f"{sid}: excluded topic '{token}' leaked"


def test_layer5_problem_activities_declare_scope_and_capabilities(curriculum):
    from dsa_tutor.domain.models import EvidenceType
    problems = [e for e in exercises_for("multi_source_bfs")
                if e.scope is ActivityScope.PROBLEM]
    assert problems, "multi_source_bfs code-writing must be problem-scope"
    for e in problems:
        assert e.required_capabilities == {EvidenceType.IMPLEMENTATION, EvidenceType.TRACE}
    closure = curriculum.prerequisite_closure("multi_source_bfs")
    assert "bfs_implementation" in closure
    assert any(x.skill_id == "bfs_implementation"
               and x.interaction_type is InteractionType.CODE_WRITING
               for x in EXERCISES)


# ---------------------------------------------------------------- semantics
def _exec_solution(exercise):
    ns = {}
    exec(exercise.payload["solution"], ns)
    return ns[exercise.payload["function_name"]]


def _run_payload_tests(exercise):
    fn = _exec_solution(exercise)
    for t in exercise.payload["tests"]:
        args = {k: v for k, v in t.items() if k not in ("expected", "args")}
        assert fn(**args) == t["expected"], f"{exercise.id} failed on {args}"


def test_all_stored_solutions_pass_their_own_payload_tests():
    for sid in LAYER5_SKILLS:
        for ex in exercises_for(sid):
            if ex.interaction_type is InteractionType.CODE_WRITING:
                _run_payload_tests(ex)


def test_one_source_reduces_to_ordinary_bfs():
    """S=1 must give exactly the Layer 2 single-source distance array."""
    ms = _exec_solution(code_writing_for("multi_source_bfs", "multi_source_distances"))
    assert ms([[1], [0, 2], [1], [4], [3], []], [0]) == [0, 1, 2, -1, -1, -1]
    assert ms([[1, 2], [3], [3, 4], [5], [5], []], [0]) == [0, 1, 1, 2, 2, 3]


def test_nearest_source_distances_are_the_per_vertex_minimum():
    """The core claim: one multi-source pass equals the min over per-source BFS runs."""
    from collections import deque

    def single(graph, start):
        dist = [-1] * len(graph)
        dist[start] = 0
        q = deque([start])
        while q:
            v = q.popleft()
            for nxt in graph[v]:
                if dist[nxt] == -1:
                    dist[nxt] = dist[v] + 1
                    q.append(nxt)
        return dist

    ms = _exec_solution(code_writing_for("multi_source_bfs", "multi_source_distances"))
    graphs = [
        [[1], [0, 2], [1, 3], [2, 4], [3], []],   # line + isolated 5
        [[2], [3], [3], [1, 2, 4], [3]],           # wave collision
        [[1], [0], [3], [2]],                     # sources in different components
        [[1, 2], [0], [0, 3], [2]],               # asymmetric tree
    ]
    for graph in graphs:
        n = len(graph)
        for sources in ([0], [0, n - 1] if n > 1 else [0], list(range(0, n, 2))):
            merged = [min((single(graph, s)[v] for s in sources
                           if single(graph, s)[v] != -1), default=-1) for v in range(n)]
            assert ms(graph, sources) == merged, f"min-merge mismatch on {graph}, {sources}"


def test_sourceless_component_stays_minus_one_and_empty_sources():
    """No wave can enter a sourceless component; no sources at all -> all -1."""
    ms = _exec_solution(code_writing_for("multi_source_bfs", "multi_source_distances"))
    assert ms([[1], [0, 2], [1], [4], [3], []], [0]) == [0, 1, 2, -1, -1, -1]
    assert ms([[1], [0]], []) == [-1, -1]
    completed = _exec_solution(code_writing_for(
        "multi_source_bfs", "nearest_distances_completed"))
    assert completed([[1], [0]], []) == [-1, -1]


def test_duplicate_sources_are_absorbed():
    """A repeated source must not change the answer (absorbed by the -1 check)."""
    ms = _exec_solution(code_writing_for("multi_source_bfs", "multi_source_distances"))
    graph = [[1], [0, 2], [1, 3], [2, 4], [3], []]
    assert ms(graph, [0, 0, 4]) == ms(graph, [0, 4]) == [0, 1, 2, 1, 0, -1]


def test_traces_execute_to_their_expected_output():
    """The trace exercises' embedded code must really produce the expected output."""
    import io
    from contextlib import redirect_stdout
    for sid in LAYER5_SKILLS:
        for ex in exercises_for(sid):
            if ex.interaction_type is not InteractionType.CODE_TRACING:
                continue
            lines = ex.prompt.splitlines()
            code_start = next(i for i, ln in enumerate(lines)
                              if ln.startswith(("from ", "graph", "def ", "import ")))
            code = "\n".join(lines[code_start:])
            ns, buf = {}, io.StringIO()
            with redirect_stdout(buf):
                exec(code, ns)
            assert buf.getvalue().rstrip("\n") == ex.payload["expected_output"], \
                f"{ex.id}: prompt code does not produce the expected output"


def test_completion_activity_keeps_guided_skeleton():
    """The guided completion must keep the seeding-loop skeleton in the starter
    (the learner fills only the two initialization lines)."""
    completion = code_writing_for("multi_source_bfs", "nearest_distances_completed")
    starter = completion.payload["starter"]
    assert "# line 1" in starter and "# line 2" in starter
    assert "for s in sources" in starter and "while queue" in starter
    _run_payload_tests(completion)


# ---------------------------------------------------------------- runtime progression
def test_layer5_entry_presents_multi_source_initialization_theory_first(service):
    from test_layer1_progression import seed_mastery
    from dsa_tutor.domain.models import Pace

    seed_mastery(service, [s.id for s in service.curriculum.skills.values()
                           if s.id not in LAYER5_SKILLS])
    view = service.start_session(pace=Pace.NORMAL)
    assert view.kind == "theory"
    assert view.unit.skill_id == "multi_source_initialization"
    view = service.mark_theory_seen()
    assert view.kind == "exercise"


def test_full_correct_run_masters_layer5_and_completes(service):
    """A learner answering everything correctly progresses through the whole
    curriculum including Layer 5 (prereq gates must not stall on the new problem
    activities)."""
    from test_layer1_progression import drive, seed_mastery
    from dsa_tutor.domain.models import Pace

    seed_mastery(service, [s.id for s in service.curriculum.skills.values()
                           if s.id not in LAYER5_SKILLS])
    view = service.start_session(pace=Pace.NORMAL)
    seen = []
    view, _ = drive(service, view, max_turns=500,
                    on_turn=lambda v: seen.append(v.exercise.skill_id)
                    if v.kind == "exercise" else None)
    assert view.kind == "ended"
    for sid in LAYER5_SKILLS:
        assert sid in seen, f"{sid} was never served"
    report = {row["skill"]: row for row in service.progress_report()["skills"]}
    for sid in LAYER5_SKILLS:
        assert report[sid]["mastered"], f"{sid} not mastered after a fully correct run"
