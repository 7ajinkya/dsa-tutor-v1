"""Layer 3 curriculum acceptance criteria (Graph Slice A: Undirected Cycle Detection).

All tests are deterministic: they assert curriculum structure (skills, prereqs,
units, evidence) and execute the stored reference solutions against their own
test payloads — no AI, no randomness.

Audit decisions encoded here (see the Layer 3 audit):
- exactly THREE new permanent skills: cycle_encounter_reasoning,
  parent_aware_traversal, undirected_cycle_detection;
- disconnected-graph handling is NOT a skill: the Layer 1 outer-loop pattern is
  reused via a prerequisite (component_enumeration) and exercised as a rung
  inside undirected_cycle_detection (trace + completion skeleton + tests);
- the BFS variant is implementation evidence inside undirected_cycle_detection,
  not a separate skill (same for the DFS variant);
- parent tracking itself is NOT duplicated: path_reconstruction already owns the
  BFS discovery-parent content and is reused as a supporting prerequisite;
- existing cycle / visited-handling / implementation skills are reused via
  prerequisites, never duplicated.
"""
import re

import pytest

from dsa_tutor.content.curriculum_v0 import EXERCISES, PREREQS, SKILLS, UNITS
from dsa_tutor.domain.models import (
    ActivityRole, ActivityScope, InteractionType, PrereqStrength, UnitType,
)

LAYER3_SKILLS = ("cycle_encounter_reasoning", "parent_aware_traversal",
                 "undirected_cycle_detection")


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
def test_exactly_three_layer3_skills_added():
    ids = {s.id for s in SKILLS}
    assert set(LAYER3_SKILLS) <= ids
    # no duplicate/granular candidate nodes leaked in: per-traversal variants,
    # parent-edge bookkeeping and self-loop handling must not be standalone skills
    forbidden = {"dfs_cycle_detection", "bfs_cycle_detection", "cycle_detection_bfs",
                 "disconnected_cycle_detection", "cycle_parent_edge", "parent_edge_skipping",
                 "self_loop_handling"}
    assert not forbidden & ids


def test_layer3_prereq_ladder(curriculum):
    # the conceptual ladder must hold in the engine's prerequisite-first order
    order = curriculum.learning_order()
    for a, b in [("cycle", "cycle_encounter_reasoning"),
                 ("dfs_visited_handling", "cycle_encounter_reasoning"),
                 ("cycle_encounter_reasoning", "parent_aware_traversal"),
                 ("dfs_implementation", "parent_aware_traversal"),
                 ("parent_aware_traversal", "undirected_cycle_detection")]:
        assert order.index(a) < order.index(b), f"{a} must precede {b}"
    # reuse, not duplication: existing concepts are the prerequisites
    assert {"cycle", "dfs_visited_handling"} <= core_prereqs("cycle_encounter_reasoning")
    assert {"cycle_encounter_reasoning", "dfs_implementation"} \
        <= core_prereqs("parent_aware_traversal")
    assert {"parent_aware_traversal", "dfs_implementation"} \
        <= core_prereqs("undirected_cycle_detection")
    assert "path_reconstruction" in all_prereqs("parent_aware_traversal")
    assert "component_enumeration" in all_prereqs("undirected_cycle_detection")
    assert "bfs_implementation" in all_prereqs("undirected_cycle_detection")
    # no Layer 3 skill may hang off the V0 boundary
    for sid in LAYER3_SKILLS:
        assert "v0_readiness" not in core_prereqs(sid)


def test_layer3_evidence_progression():
    """Recognition -> tracing (tree vs genuine cycle) -> explanation -> guided code
    completion -> independent DFS implementation -> BFS variant -> transfer."""
    for sid in LAYER3_SKILLS:
        exs = exercises_for(sid)
        assert any(e.interaction_type is InteractionType.MCQ for e in exs), \
            f"{sid}: no recognition evidence"
        assert any(e.interaction_type in {InteractionType.CODE_TRACING,
                                          InteractionType.OUTPUT_PREDICTION} for e in exs), \
            f"{sid}: no tracing evidence"
    # the two reasoning skills carry explanation evidence
    for sid in ("cycle_encounter_reasoning", "parent_aware_traversal"):
        assert any(e.interaction_type is InteractionType.FREE_FORM
                   for e in exercises_for(sid)), f"{sid}: no explanation evidence"
    # the synthesis skill: guided completion + from-scratch DFS + BFS variant
    writers = [e for e in exercises_for("undirected_cycle_detection")
               if e.interaction_type is InteractionType.CODE_WRITING]
    assert {e.payload["function_name"] for e in writers} == \
        {"detect_cycle_completed", "has_cycle_undirected", "has_cycle_bfs"}
    starters = [w.payload["starter"] for w in writers]
    assert any("# line" in s for s in starters), "no guided completion activity"
    assert any("# line" not in s for s in starters), "no from-scratch activity"
    # independent transfer under undirected_cycle_detection (apply unit)
    apply_units = [u for u in UNITS
                   if u.skill_id == "undirected_cycle_detection" and u.unit_type is UnitType.APPLY]
    assert apply_units and any(
        e.interaction_type is InteractionType.FREE_FORM and e.role is ActivityRole.APPLICATION
        for u in apply_units for e in EXERCISES if e.unit_id == u.id)


def test_layer3_exclusions():
    """Explicit spec exclusions must not leak into Layer 3 content."""
    forbidden = ["topological", r"\bunion\b", r"\bdsu\b", r"\bkruskal\b", r"\bprim\b",
                 "spanning", "articulation", r"\bbridge\b", "strongly connected",
                 "tarjan", r"back edge", r"(?<!un)directed"]
    for sid in LAYER3_SKILLS:
        skill = next(s for s in SKILLS if s.id == sid)
        text = " ".join([skill.id, skill.title, skill.description]).lower()
        units = [u for u in UNITS if u.skill_id == sid]
        text += " ".join((u.title or "") + " " + (u.goal or "") for u in units).lower()
        for ex in exercises_for(sid):
            text += " " + ex.prompt.lower()
            text += " " + " ".join(h["text"].lower() for h in ex.hint_ladder)
        for token in forbidden:
            assert not re.search(token, text), f"{sid}: excluded topic '{token}' leaked"


def test_layer3_problem_activities_declare_scope_and_capabilities(curriculum):
    from dsa_tutor.domain.models import EvidenceType
    problems = [e for e in exercises_for("undirected_cycle_detection")
                if e.scope is ActivityScope.PROBLEM]
    assert problems, "undirected_cycle_detection code-writing must be problem-scope"
    for e in problems:
        assert e.required_capabilities == {EvidenceType.IMPLEMENTATION, EvidenceType.TRACE}
        # IMPLEMENTATION must be demonstrable inside the prerequisite closure
        closure = curriculum.prerequisite_closure("undirected_cycle_detection")
        assert "dfs_implementation" in closure
        assert any(x.skill_id == "dfs_implementation"
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
    for sid in LAYER3_SKILLS:
        for ex in exercises_for(sid):
            if ex.interaction_type is InteractionType.CODE_WRITING:
                _run_payload_tests(ex)


def test_parent_edge_is_not_cycle_evidence():
    """The core invariant's negative side: on trees every vertex meets its parent
    visited (the arrival edge stored both ways), yet no cycle exists."""
    dfs = _exec_solution(code_writing_for("undirected_cycle_detection", "has_cycle_undirected"))
    bfs = _exec_solution(code_writing_for("undirected_cycle_detection", "has_cycle_bfs"))
    single_edge = [[1], [0]]
    path_3 = [[1], [0, 2], [1]]
    star = [[1, 2, 3], [0], [0], [0]]
    forest = [[1], [0, 2], [1], [4], [3], []]
    for graph in (single_edge, path_3, star, forest):
        assert dfs(graph) is False, f"DFS wrongly reports a cycle on {graph}"
        assert bfs(graph) is False, f"BFS wrongly reports a cycle on {graph}"


def test_visited_non_parent_is_cycle_evidence():
    dfs = _exec_solution(code_writing_for("undirected_cycle_detection", "has_cycle_undirected"))
    bfs = _exec_solution(code_writing_for("undirected_cycle_detection", "has_cycle_bfs"))
    triangle = [[1, 2], [0, 2], [0, 1]]
    tree_plus_edge = [[1, 2], [0, 2], [1, 0]]      # tree A-B-C + closing edge C-A
    four_cycle = [[1, 3], [0, 2], [1, 3], [2, 0]]
    for graph in (triangle, tree_plus_edge, four_cycle):
        assert dfs(graph) is True, f"DFS misses the cycle in {graph}"
        assert bfs(graph) is True, f"BFS misses the cycle in {graph}"


def test_disconnected_graphs_and_isolated_vertices():
    """A cycle in ANY component decides the answer (outer loop); isolated vertices
    and acyclic components must not fake or mask evidence."""
    dfs = _exec_solution(code_writing_for("undirected_cycle_detection", "has_cycle_undirected"))
    bfs = _exec_solution(code_writing_for("undirected_cycle_detection", "has_cycle_bfs"))
    cycle_in_later_component = [[1], [0], [3, 4], [2, 4], [2, 3], []]
    isolated_only = [[], [], []]
    single_isolated = [[]]
    for fn in (dfs, bfs):
        assert fn(cycle_in_later_component) is True
        assert fn(isolated_only) is False
        assert fn(single_isolated) is False


def test_self_loop_is_a_cycle():
    """A self-loop is genuine cycle evidence, never an ordinary parent edge — and
    the parent-skip must not mask it even alongside a normal edge."""
    dfs = _exec_solution(code_writing_for("undirected_cycle_detection", "has_cycle_undirected"))
    bfs = _exec_solution(code_writing_for("undirected_cycle_detection", "has_cycle_bfs"))
    for fn in (dfs, bfs):
        assert fn([[0]]) is True
        assert fn([[0, 1], [0]]) is True   # self-loop plus a normal edge


def test_detection_independent_of_adjacency_order():
    """Controlled variation 'adjacency-order changes': the verdict must not depend
    on the order in which neighbors are listed."""
    dfs = _exec_solution(code_writing_for("undirected_cycle_detection", "has_cycle_undirected"))
    orders = [
        [[1, 2], [0, 2], [0, 1]],
        [[2, 1], [2, 0], [1, 0]],
        [[1, 2], [2, 0], [0, 1]],
    ]
    for graph in orders:
        assert dfs(graph) is True, f"order sensitivity on {graph}"
    assert dfs([[1], [0, 2], [1]]) is False   # forest order flipped, still acyclic


def test_bfs_and_dfs_variants_agree():
    dfs = _exec_solution(code_writing_for("undirected_cycle_detection", "has_cycle_undirected"))
    bfs = _exec_solution(code_writing_for("undirected_cycle_detection", "has_cycle_bfs"))
    graphs = [
        [[1], [0]],
        [[1, 2], [0, 2], [0, 1]],
        [[1], [0, 2], [1]],
        [[], [], []],
        [[0]],
        [[1], [0], [3, 4], [2, 4], [2, 3], []],
        [[1, 2, 3], [0], [0], [0]],
        [[1, 2], [0, 3], [0, 3], [1, 2]],   # K2,2: an even cycle
        [[1, 3], [0, 2], [1, 3], [2, 0]],
    ]
    for graph in graphs:
        assert dfs(graph) == bfs(graph), f"variants disagree on {graph}"


def test_completion_activity_keeps_guided_skeleton():
    """The guided completion must keep the outer loop + parent skeleton in the
    starter (the learner fills only the invariant lines)."""
    completion = code_writing_for("undirected_cycle_detection", "detect_cycle_completed")
    starter = completion.payload["starter"]
    assert "# line 1" in starter and "# line 2" in starter and "# line 3" in starter
    assert "parent" in starter and "for start in range" in starter
    _run_payload_tests(completion)


# ---------------------------------------------------------------- runtime progression
def test_layer3_entry_presents_cycle_encounter_reasoning_theory_first(service):
    from test_layer1_progression import seed_mastery
    from dsa_tutor.domain.models import Pace

    seed_mastery(service, [s.id for s in service.curriculum.skills.values()
                           if s.id not in LAYER3_SKILLS])
    view = service.start_session(pace=Pace.NORMAL)
    assert view.kind == "theory"
    assert view.unit.skill_id == "cycle_encounter_reasoning"
    view = service.mark_theory_seen()
    assert view.kind == "exercise"


def test_variation_preference_does_not_starve_required_evidence(service):
    """Regression (found in manual full-run testing): a raised difficulty shift used to
    act as a hard filter in the variation pool, permanently excluding the skill's
    trace/MCQ activities. TRACE is a required evidence type of
    undirected_cycle_detection, so mastery became unreachable. The shift must only
    REORDER equal-attempt alternatives, never exclude activity types."""
    from test_layer1_progression import drive, learner_answer, seed_mastery
    from dsa_tutor.domain.models import Pace

    seed_mastery(service, [s.id for s in service.curriculum.skills.values()
                           if s.id not in LAYER3_SKILLS])
    service._state().difficultylevel_shift = 1
    view = service.start_session(pace=Pace.NORMAL)
    served_types = []
    view, _ = drive(service, view, max_turns=120,
                    on_turn=lambda v: served_types.append(v.exercise.interaction_type.value)
                    if v.kind == "exercise" else None)
    assert view.kind == "ended", "the skill must be masterable despite shift +1"
    assert "code_tracing" in served_types, \
        "the trace rung must remain reachable when a harder preference is active"


def test_full_correct_run_masters_layer3_and_completes(service):
    """A learner answering everything correctly progresses through the whole
    curriculum including Layer 3 (prereq gates must not stall on the new
    problem activities, and the trace/completion/implementation ladder must be
    reachable and servable in order)."""
    from test_layer1_progression import drive, seed_mastery
    from dsa_tutor.domain.models import Pace

    seed_mastery(service, [s.id for s in service.curriculum.skills.values()
                           if s.id not in LAYER3_SKILLS])
    view = service.start_session(pace=Pace.NORMAL)
    seen = []
    view, _ = drive(service, view, max_turns=220,
                    on_turn=lambda v: seen.append(v.exercise.skill_id)
                    if v.kind == "exercise" else None)
    assert view.kind == "ended"
    for sid in LAYER3_SKILLS:
        assert sid in seen, f"{sid} was never served"
    report = {row["skill"]: row for row in service.progress_report()["skills"]}
    for sid in LAYER3_SKILLS:
        assert report[sid]["mastered"], f"{sid} not mastered after a fully correct run"
