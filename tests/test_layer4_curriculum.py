"""Layer 4 curriculum acceptance criteria (Graph Slice A: Bipartite Graphs / 2-Coloring).

All tests are deterministic: they assert curriculum structure (skills, prereqs,
units, evidence) and execute the stored reference solutions against their own
test payloads — no AI, no randomness.

Audit decisions encoded here (see the Layer 4 audit):
- exactly FOUR new permanent skills (the approved compact set): two_color_constraint,
  color_propagation, color_conflict_detection, bipartite_graph;
- disconnected handling is NOT a skill: the Layer 1 outer-loop pattern is reused
  via a supporting prerequisite (component_enumeration) and exercised inside the
  bipartite check activities;
- the odd/even cycle connection is NOT a skill: undirected_cycle_detection is a
  supporting prerequisite and the parity intuition lives in conflict/bipartite
  evidence;
- the DFS variant is a controlled implementation variation inside bipartite_graph,
  not a separate skill (BFS-first ordering per the approved design);
- no existing skill covered coloring/partition/two-group constraints, so nothing
  is duplicated.
"""
import re

import pytest

from dsa_tutor.content.curriculum_v0 import EXERCISES, PREREQS, SKILLS, UNITS
from dsa_tutor.domain.models import (
    ActivityRole, ActivityScope, InteractionType, PrereqStrength, UnitType,
)

LAYER4_SKILLS = ("two_color_constraint", "color_propagation",
                 "color_conflict_detection", "bipartite_graph")


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
def test_exactly_four_layer4_skills_added():
    ids = {s.id for s in SKILLS}
    assert set(LAYER4_SKILLS) <= ids
    # no duplicate/granular candidate nodes leaked in: general coloring, matching,
    # odd-cycle theory and per-check variants must not be standalone skills
    forbidden = {"graph_coloring", "k_coloring", "bipartite_matching", "hopcroft_karp",
                 "odd_cycle", "bipartite_check", "disconnected_bipartite",
                 "bipartite_dfs", "bipartite_bfs"}
    assert not forbidden & ids


def test_layer4_prereq_ladder(curriculum):
    # the conceptual ladder must hold in the engine's prerequisite-first order:
    # fundamentals/connectedness -> constraint -> (+BFS) propagation -> conflict -> bipartite
    order = curriculum.learning_order()
    for a, b in [("connectedness", "two_color_constraint"),
                 ("bfs_intuition", "two_color_constraint"),
                 ("two_color_constraint", "color_propagation"),
                 ("bfs_visited_handling", "color_propagation"),
                 ("color_propagation", "color_conflict_detection"),
                 ("color_conflict_detection", "bipartite_graph"),
                 ("bfs_implementation", "bipartite_graph")]:
        assert order.index(a) < order.index(b), f"{a} must precede {b}"
    # reuse, not duplication: existing concepts are the prerequisites
    assert {"connectedness", "bfs_intuition"} <= core_prereqs("two_color_constraint")
    assert {"two_color_constraint", "bfs_visited_handling"} <= core_prereqs("color_propagation")
    assert {"color_propagation", "bfs_manual_tracing"} <= core_prereqs("color_conflict_detection")
    assert {"color_conflict_detection", "bfs_implementation"} <= core_prereqs("bipartite_graph")
    # layer-1/layer-3 reasoning reused as supporting links, never duplicated
    assert "component_enumeration" in all_prereqs("bipartite_graph")
    assert "undirected_cycle_detection" in all_prereqs("bipartite_graph")
    assert "dfs_implementation" in all_prereqs("bipartite_graph")
    # no Layer 4 skill may hang off the V0 boundary
    for sid in LAYER4_SKILLS:
        assert "v0_readiness" not in core_prereqs(sid)


def test_layer4_evidence_progression():
    """Recognition -> tracing -> code completion -> independent BFS implementation ->
    DFS controlled variation -> transfer, per the approved BFS-first progression."""
    for sid in LAYER4_SKILLS:
        exs = exercises_for(sid)
        assert any(e.interaction_type is InteractionType.MCQ for e in exs), \
            f"{sid}: no recognition evidence"
    # propagation and conflict carry tracing evidence
    for sid in ("color_propagation", "color_conflict_detection", "bipartite_graph"):
        assert any(e.interaction_type in {InteractionType.CODE_TRACING,
                                          InteractionType.OUTPUT_PREDICTION}
                   for e in exercises_for(sid)), f"{sid}: no tracing evidence"
    # the synthesis skill: guided completion + BFS implementation + DFS variation
    writers = [e for e in exercises_for("bipartite_graph")
               if e.interaction_type is InteractionType.CODE_WRITING]
    assert {e.payload["function_name"] for e in writers} == \
        {"is_bipartite_completed", "is_bipartite", "is_bipartite_dfs"}
    starters = [w.payload["starter"] for w in writers]
    assert any("# line" in s for s in starters), "no guided completion activity"
    assert any("# line" not in s for s in starters), "no from-scratch activity"
    # BFS is implemented before the DFS variation (BFS-first ordering)
    bfs_writer = code_writing_for("bipartite_graph", "is_bipartite")
    dfs_writer = code_writing_for("bipartite_graph", "is_bipartite_dfs")
    assert bfs_writer.ordering < dfs_writer.ordering
    # independent transfer under bipartite_graph (apply unit)
    apply_units = [u for u in UNITS
                   if u.skill_id == "bipartite_graph" and u.unit_type is UnitType.APPLY]
    assert apply_units and any(
        e.interaction_type is InteractionType.FREE_FORM and e.role is ActivityRole.APPLICATION
        for u in apply_units for e in EXERCISES if e.unit_id == u.id)


def test_layer4_exclusions():
    """Explicit spec exclusions must not leak into Layer 4 content."""
    forbidden = [r"\bmatching\b", r"\bhall\b", "hopcroft", r"\bflow\b", r"k-color",
                 "chromatic", "3-color", "stable marriage", r"\bmunkres\b"]
    for sid in LAYER4_SKILLS:
        skill = next(s for s in SKILLS if s.id == sid)
        text = " ".join([skill.id, skill.title, skill.description]).lower()
        units = [u for u in UNITS if u.skill_id == sid]
        text += " ".join((u.title or "") + " " + (u.goal or "") for u in units).lower()
        for ex in exercises_for(sid):
            text += " " + ex.prompt.lower()
            text += " " + " ".join(h["text"].lower() for h in ex.hint_ladder)
        for token in forbidden:
            assert not re.search(token, text), f"{sid}: excluded topic '{token}' leaked"


def test_layer4_problem_activities_declare_scope_and_capabilities(curriculum):
    from dsa_tutor.domain.models import EvidenceType
    problems = [e for e in exercises_for("bipartite_graph")
                if e.scope is ActivityScope.PROBLEM]
    assert problems, "bipartite_graph code-writing must be problem-scope"
    for e in problems:
        assert e.required_capabilities == {EvidenceType.IMPLEMENTATION, EvidenceType.TRACE}
    # IMPLEMENTATION must be demonstrable inside the prerequisite closure
    closure = curriculum.prerequisite_closure("bipartite_graph")
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
    for sid in LAYER4_SKILLS:
        for ex in exercises_for(sid):
            if ex.interaction_type is InteractionType.CODE_WRITING:
                _run_payload_tests(ex)


def test_even_cycles_two_color_odd_cycles_do_not():
    """The core parity intuition: a square (even cycle) is bipartite, a triangle
    (odd cycle) is not."""
    bfs = _exec_solution(code_writing_for("bipartite_graph", "is_bipartite"))
    dfs = _exec_solution(code_writing_for("bipartite_graph", "is_bipartite_dfs"))
    square = [[1, 3], [0, 2], [1, 3], [2, 0]]
    triangle = [[1, 2], [0, 2], [0, 1]]
    five_cycle = [[1, 4], [0, 2], [1, 3], [2, 4], [3, 0]]
    for fn in (bfs, dfs):
        assert fn(square) is True, "even cycle wrongly rejected"
        assert fn(triangle) is False, "odd cycle wrongly accepted"
        assert fn(five_cycle) is False, "5-cycle wrongly accepted"


def test_disconnected_components_decide_together():
    """One non-bipartite component fails the whole graph; all-clean components pass."""
    bfs = _exec_solution(code_writing_for("bipartite_graph", "is_bipartite"))
    dfs = _exec_solution(code_writing_for("bipartite_graph", "is_bipartite_dfs"))
    clean_plus_triangle = [[1], [0], [3, 4], [2, 4], [2, 3]]
    two_clean_components = [[1, 2], [0], [0], [4], [3]]
    for fn in (bfs, dfs):
        assert fn(clean_plus_triangle) is False
        assert fn(two_clean_components) is True
        assert fn([[], [], []]) is True    # isolated vertices only
        assert fn([[]]) is True            # single isolated vertex


def test_self_loop_is_not_bipartite():
    """A self-loop is an odd cycle of length one — and the equal-color check needs
    no special case to reject it."""
    bfs = _exec_solution(code_writing_for("bipartite_graph", "is_bipartite"))
    dfs = _exec_solution(code_writing_for("bipartite_graph", "is_bipartite_dfs"))
    for fn in (bfs, dfs):
        assert fn([[0]]) is False
        assert fn([[0, 1], [0]]) is False


def test_traces_execute_to_their_expected_output():
    """The trace exercises' embedded code must really produce the expected output."""
    import io
    from contextlib import redirect_stdout
    for sid in ("color_propagation", "color_conflict_detection", "bipartite_graph"):
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


def test_bfs_and_dfs_variants_agree():
    bfs = _exec_solution(code_writing_for("bipartite_graph", "is_bipartite"))
    dfs = _exec_solution(code_writing_for("bipartite_graph", "is_bipartite_dfs"))
    graphs = [
        [[1], [0]],
        [[1, 2], [0], [0]],
        [[1, 3], [0, 2], [1, 3], [2, 0]],
        [[1, 2], [0, 2], [0, 1]],
        [[1, 2, 3], [0], [0], [0]],
        [[1, 3], [0, 2], [1, 3], [2, 0], []],           # square + isolated vertex
        [[1, 2], [0, 3], [0, 3], [1, 2], [4], [4]],     # K2,2 + separate edge
        [[0]],
        [[], [], []],
    ]
    for graph in graphs:
        assert bfs(graph) == dfs(graph), f"variants disagree on {graph}"


def test_completion_activity_keeps_guided_skeleton():
    """The guided completion must keep the coloring-BFS + outer-loop skeleton in the
    starter (the learner fills only the invariant lines)."""
    completion = code_writing_for("bipartite_graph", "is_bipartite_completed")
    starter = completion.payload["starter"]
    assert "# line 1" in starter and "# line 2" in starter
    assert "color" in starter and "for start in range" in starter
    _run_payload_tests(completion)


# ---------------------------------------------------------------- runtime progression
def test_layer4_entry_presents_two_color_constraint_theory_first(service):
    from test_layer1_progression import seed_mastery
    from dsa_tutor.domain.models import Pace

    seed_mastery(service, [s.id for s in service.curriculum.skills.values()
                           if s.id not in LAYER4_SKILLS])
    view = service.start_session(pace=Pace.NORMAL)
    assert view.kind == "theory"
    assert view.unit.skill_id == "two_color_constraint"
    view = service.mark_theory_seen()
    assert view.kind == "exercise"


def test_full_correct_run_masters_layer4_and_completes(service):
    """A learner answering everything correctly progresses through the whole
    curriculum including Layer 4 (prereq gates must not stall on the new problem
    activities, and the BFS-before-DFS implementation ladder must be reachable)."""
    from test_layer1_progression import drive, seed_mastery
    from dsa_tutor.domain.models import Pace

    seed_mastery(service, [s.id for s in service.curriculum.skills.values()
                           if s.id not in LAYER4_SKILLS])
    view = service.start_session(pace=Pace.NORMAL)
    seen = []
    view, _ = drive(service, view, max_turns=260,
                    on_turn=lambda v: seen.append(v.exercise.skill_id)
                    if v.kind == "exercise" else None)
    assert view.kind == "ended"
    for sid in LAYER4_SKILLS:
        assert sid in seen, f"{sid} was never served"
    report = {row["skill"]: row for row in service.progress_report()["skills"]}
    for sid in LAYER4_SKILLS:
        assert report[sid]["mastered"], f"{sid} not mastered after a fully correct run"
