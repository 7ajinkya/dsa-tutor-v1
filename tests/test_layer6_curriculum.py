"""Layer 6 curriculum acceptance criteria (Graph Slice A: Grid as Graph).

All tests are deterministic: they assert curriculum structure (skills, prereqs,
units, evidence) and execute the stored reference solutions against their own
test payloads — no AI, no randomness.

Audit decisions encoded here (see the Layer 6 audit):
- exactly THREE new permanent skills (the approved compact set): grid_graph_model,
  implicit_neighbor_generation, grid_traversal;
- grid reachability, grid components, grid shortest path, grid distance, and
  multi-source grid BFS are NOT separate skills: they are application/evidence
  capabilities inside grid_traversal, reusing the Layer 1 outer loop, Layer 2
  BFS distance, and Layer 5 multi-source initialization via prerequisites;
- the 4-vs-8 direction variation lives as a controlled variation exercise
  (count_regions_8dir) inside grid_traversal, not a skill;
- no duplicate traversal skill: BFS/DFS are reused through core prerequisites.
"""
import re

import pytest

from dsa_tutor.content.curriculum_v0 import EXERCISES, PREREQS, SKILLS, UNITS
from dsa_tutor.domain.models import (
    ActivityRole, ActivityScope, InteractionType, PrereqStrength, UnitType,
)

LAYER6_SKILLS = ("grid_graph_model", "implicit_neighbor_generation", "grid_traversal")


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
def test_exactly_three_layer6_skills_added():
    ids = {s.id for s in SKILLS}
    assert set(LAYER6_SKILLS) <= ids
    # no duplicate/granular candidate nodes leaked in: per-application skills and
    # advanced shortest-path machinery must not be standalone skills
    forbidden = {"grid_reachability", "grid_components", "grid_shortest_path",
                 "grid_distance", "grid_multi_source_bfs", "islands", "flood_fill",
                 "grid_dijkstra", "zero_one_bfs", "a_star", "maze_solver"}
    assert not forbidden & ids


def test_layer6_prereq_ladder(curriculum):
    # the conceptual bridge must hold in the engine's prerequisite-first order:
    # graph vocabulary -> grid-as-graph -> neighbor generation -> traversal
    order = curriculum.learning_order()
    for a, b in [("vertices_edges", "grid_graph_model"),
                 ("adjacency", "grid_graph_model"),
                 ("grid_graph_model", "implicit_neighbor_generation"),
                 ("adjacency_list", "implicit_neighbor_generation"),
                 ("implicit_neighbor_generation", "grid_traversal"),
                 ("bfs_implementation", "grid_traversal"),
                 ("dfs_implementation", "grid_traversal")]:
        assert order.index(a) < order.index(b), f"{a} must precede {b}"
    # reuse, not duplication: existing traversal concepts are the prerequisites
    assert {"vertices_edges", "adjacency"} <= core_prereqs("grid_graph_model")
    assert {"grid_graph_model", "adjacency_list"} <= core_prereqs("implicit_neighbor_generation")
    assert {"implicit_neighbor_generation", "bfs_implementation",
            "dfs_implementation"} <= core_prereqs("grid_traversal")
    # layer 1/2/5 reasoning reused as supporting links, never duplicated
    assert {"component_enumeration", "bfs_distance", "multi_source_bfs"} <= \
        all_prereqs("grid_traversal")
    # no Layer 6 skill may hang off the V0 boundary
    for sid in LAYER6_SKILLS:
        assert "v0_readiness" not in core_prereqs(sid)


def test_layer6_evidence_progression():
    """Recognition -> tracing -> neighbor generation -> independent implementation ->
    components/shortest-path/multi-source applications -> transfer."""
    for sid in LAYER6_SKILLS:
        exs = exercises_for(sid)
        assert any(e.interaction_type is InteractionType.MCQ for e in exs), \
            f"{sid}: no recognition evidence"
    # all three skills carry tracing evidence
    for sid in LAYER6_SKILLS:
        assert any(e.interaction_type in {InteractionType.CODE_TRACING,
                                          InteractionType.OUTPUT_PREDICTION}
                   for e in exercises_for(sid)), f"{sid}: no tracing evidence"
    # the synthesis skill: guided completion + from-scratch implementations covering
    # the full application family (components, shortest path, 8-dir, multi-source)
    writers = [e for e in exercises_for("grid_traversal")
               if e.interaction_type is InteractionType.CODE_WRITING]
    assert {e.payload["function_name"] for e in writers} == \
        {"grid_shortest_completed", "count_islands", "count_regions_8dir",
         "grid_multi_source_distances"}
    starters = [w.payload["starter"] for w in writers]
    assert any("# line" in s for s in starters), "no guided completion activity"
    assert sum("# line" not in s for s in starters) >= 3, "missing from-scratch activities"
    # neighbor generation is implemented inside its own skill
    assert code_writing_for("implicit_neighbor_generation", "valid_neighbors")
    # independent transfer under grid_traversal (apply unit)
    apply_units = [u for u in UNITS
                   if u.skill_id == "grid_traversal" and u.unit_type is UnitType.APPLY]
    assert apply_units and any(
        e.interaction_type is InteractionType.FREE_FORM and e.role is ActivityRole.APPLICATION
        for u in apply_units for e in EXERCISES if e.unit_id == u.id)


def test_layer6_exclusions():
    """Explicit spec exclusions must not leak into Layer 6 content."""
    forbidden = [r"\bdijkstra\b", r"\ba\s*\*\b", "0-1 bfs", "0-1 bfs", "weighted grid",
                 "a-star", "maze dp", "grid dp", "state-space"]
    for sid in LAYER6_SKILLS:
        skill = next(s for s in SKILLS if s.id == sid)
        text = " ".join([skill.id, skill.title, skill.description]).lower()
        units = [u for u in UNITS if u.skill_id == sid]
        text += " ".join((u.title or "") + " " + (u.goal or "") for u in units).lower()
        for ex in exercises_for(sid):
            text += " " + ex.prompt.lower()
            text += " " + " ".join(h["text"].lower() for h in ex.hint_ladder)
        for token in forbidden:
            assert not re.search(token, text), f"{sid}: excluded topic '{token}' leaked"


def test_layer6_problem_activities_declare_scope_and_capabilities(curriculum):
    from dsa_tutor.domain.models import EvidenceType
    problems = [e for e in exercises_for("grid_traversal")
                if e.scope is ActivityScope.PROBLEM]
    assert problems, "grid_traversal code-writing must be problem-scope"
    for e in problems:
        assert e.required_capabilities == {EvidenceType.IMPLEMENTATION, EvidenceType.TRACE}
    closure = curriculum.prerequisite_closure("grid_traversal")
    assert "bfs_implementation" in closure and "dfs_implementation" in closure


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
    for sid in LAYER6_SKILLS:
        for ex in exercises_for(sid):
            if ex.interaction_type is InteractionType.CODE_WRITING:
                _run_payload_tests(ex)


def test_grid_shortest_distance_matches_bfs_on_explicit_graph():
    """The grid IS an unweighted graph: grid BFS distances must equal explicit-graph
    BFS distances for the same neighborhood."""
    from collections import deque

    def graph_bfs(adj, start):
        dist = {start: 0}
        q = deque([start])
        while q:
            v = q.popleft()
            for w in adj[v]:
                if w not in dist:
                    dist[w] = dist[v] + 1
                    q.append(w)
        return dist

    shortest = _exec_solution(code_writing_for("grid_traversal", "grid_shortest_completed"))
    grids = [
        ["...", ".#.", "..."],
        ["....", ".##.", "...."],
        ["..", ".."],
    ]
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    for grid in grids:
        assert grid[0][0] == ".", "start cell must be open for this comparison"
        rows, cols = len(grid), len(grid[0])
        adj = {}
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] == ".":
                    adj[(r, c)] = [(r + dr, c + dc) for dr, dc in directions
                                   if 0 <= r + dr < rows and 0 <= c + dc < cols
                                   and grid[r + dr][c + dc] == "."]
        dist = graph_bfs(adj, (0, 0))
        for goal in adj:
            expected = dist.get(goal, -1)
            assert shortest(grid, (0, 0), goal) == expected, \
                f"grid BFS disagrees with graph BFS on {grid} -> {goal}"


def test_islands_count_matches_component_enumeration():
    """count_islands is the Layer 1 outer loop on the implicit grid graph."""
    count = _exec_solution(code_writing_for("grid_traversal", "count_islands"))
    count8 = _exec_solution(code_writing_for("grid_traversal", "count_regions_8dir"))
    # 4-direction: diagonal touching does NOT join regions
    assert count([".#", "#."]) == 2
    # 8-direction: the same grid is ONE region
    assert count8([".#", "#."]) == 1
    assert count(["##"]) == count8(["##"]) == 0
    assert count(["..."]) == count8(["..."]) == 1
    # spirals and stripes
    assert count([".#.", ".#.", ".#."]) == 2
    assert count8([".#.", ".#.", ".#."]) == 2


def test_multi_source_grid_distances_match_layer5_on_explicit_graph():
    """Multi-source grid BFS = Layer 5 multi-source BFS on the grid's implicit graph."""
    from collections import deque

    def graph_multi(graph, sources):
        dist = [-1] * len(graph)
        q = deque()
        for s in sources:
            dist[s] = 0
            q.append(s)
        while q:
            v = q.popleft()
            for w in graph[v]:
                if dist[w] == -1:
                    dist[w] = dist[v] + 1
                    q.append(w)
        return dist

    grid_ms = _exec_solution(code_writing_for("grid_traversal", "grid_multi_source_distances"))
    grid = ["...", ".#.", "..."]
    rows, cols = len(grid), len(grid[0])
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    cells = [(r, c) for r in range(rows) for c in range(cols) if grid[r][c] == "."]
    index = {cell: i for i, cell in enumerate(cells)}
    adj = [[] for _ in cells]
    for (r, c), i in index.items():
        for dr, dc in directions:
            nxt = (r + dr, c + dc)
            if nxt in index:
                adj[i].append(index[nxt])
    sources = [(0, 0), (0, 2)]
    dist = graph_multi(adj, [index[s] for s in sources])
    expected = [[-1] * cols for _ in range(rows)]
    for (r, c), i in index.items():
        expected[r][c] = dist[i]
    assert grid_ms(grid, sources) == expected


def test_blocked_cells_are_not_vertices_and_unreachable_stays_minus_one():
    shortest = _exec_solution(code_writing_for("grid_traversal", "grid_shortest_completed"))
    ms = _exec_solution(code_writing_for("grid_traversal", "grid_multi_source_distances"))
    # a wall between start and goal -> unreachable
    assert shortest(["..#"], (0, 0), (0, 2)) == -1
    # a source ON a blocked cell seeds nothing -> everything -1
    assert ms(["#."], [(0, 0)]) == [[-1, -1]]


def test_traces_execute_to_their_expected_output():
    """The trace exercises' embedded code must really produce the expected output."""
    import io
    from contextlib import redirect_stdout
    for sid in LAYER6_SKILLS:
        for ex in exercises_for(sid):
            if ex.interaction_type is not InteractionType.CODE_TRACING:
                continue
            lines = ex.prompt.splitlines()
            code_start = next(i for i, ln in enumerate(lines)
                              if ln.startswith(("from ", "grid", "def ", "import ")))
            code = "\n".join(lines[code_start:])
            ns, buf = {}, io.StringIO()
            with redirect_stdout(buf):
                exec(code, ns)
            assert buf.getvalue().rstrip("\n") == ex.payload["expected_output"], \
                f"{ex.id}: prompt code does not produce the expected output"


def test_completion_activity_keeps_guided_skeleton():
    """The guided completion must keep the grid-BFS skeleton in the starter (the
    learner fills only the generator + discovery lines)."""
    completion = code_writing_for("grid_traversal", "grid_shortest_completed")
    starter = completion.payload["starter"]
    assert "# line 1" in starter and "# line 2" in starter
    assert "directions" in starter.replace("(-1, 0), (1, 0)", "directions") or \
        "for dr, dc in" in starter
    assert "while queue" in starter
    _run_payload_tests(completion)


# ---------------------------------------------------------------- runtime progression
def test_layer6_entry_presents_grid_graph_model_theory_first(service):
    from test_layer1_progression import seed_mastery
    from dsa_tutor.domain.models import Pace

    seed_mastery(service, [s.id for s in service.curriculum.skills.values()
                           if s.id not in LAYER6_SKILLS])
    view = service.start_session(pace=Pace.NORMAL)
    assert view.kind == "theory"
    assert view.unit.skill_id == "grid_graph_model"
    view = service.mark_theory_seen()
    assert view.kind == "exercise"


def test_full_correct_run_masters_layer6_and_completes(service):
    """A learner answering everything correctly progresses through the whole
    curriculum including Layer 6 (prereq gates must not stall on the new problem
    activities)."""
    from test_layer1_progression import drive, seed_mastery
    from dsa_tutor.domain.models import Pace

    seed_mastery(service, [s.id for s in service.curriculum.skills.values()
                           if s.id not in LAYER6_SKILLS])
    view = service.start_session(pace=Pace.NORMAL)
    seen = []
    view, _ = drive(service, view, max_turns=700,
                    on_turn=lambda v: seen.append(v.exercise.skill_id)
                    if v.kind == "exercise" else None)
    assert view.kind == "ended"
    for sid in LAYER6_SKILLS:
        assert sid in seen, f"{sid} was never served"
    report = {row["skill"]: row for row in service.progress_report()["skills"]}
    for sid in LAYER6_SKILLS:
        assert report[sid]["mastered"], f"{sid} not mastered after a fully correct run"
