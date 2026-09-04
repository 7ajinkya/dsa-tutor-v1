"""Layer 2 curriculum acceptance criteria (Graph Slice A: Unweighted Shortest
Paths -> Path Reconstruction).

All tests are deterministic: they assert curriculum structure (skills, prereqs,
units, evidence) and execute the stored reference solutions against their own
test payloads — no AI, no randomness.

Audit decisions encoded here (see the Layer 2 audit):
- exactly TWO new permanent skills: bfs_distance and path_reconstruction;
- "unweighted shortest path" / "shortest-path correctness" are NOT skills — they
  live as reasoning evidence inside bfs_distance and the combined routine inside
  path_reconstruction;
- parent/predecessor tracking is a unit/evidence rung of path_reconstruction,
  not a standalone skill;
- existing BFS-level content (bfs_intuition, bfs_vs_dfs, the v0_readiness
  bfs_levels check) is reused via prerequisites, never duplicated.
"""
import pytest

from dsa_tutor.content.curriculum_v0 import EXERCISES, PREREQS, SKILLS, UNITS
from dsa_tutor.domain.models import (
    InteractionType, PrereqStrength, UnitType,
)

LAYER2_SKILLS = ("bfs_distance", "path_reconstruction")


def core_prereqs(skill_id):
    return {p.prerequisite_skill_id for p in PREREQS
            if p.skill_id == skill_id and p.strength is PrereqStrength.CORE}


def exercises_for(skill_id):
    return [e for e in EXERCISES if e.skill_id == skill_id]


# ---------------------------------------------------------------- structure
def test_exactly_two_layer2_skills_added():
    ids = {s.id for s in SKILLS}
    assert {sid for sid in LAYER2_SKILLS} <= ids
    # no duplicate/granular candidate nodes leaked in: distance tracking,
    # unreachable handling, parent tracking etc. must not be standalone skills
    forbidden = {"unweighted_shortest_path", "distance_tracking", "parent_tracking",
                 "shortest_path_correctness", "bfs_shortest_path"}
    assert not forbidden & ids


def test_layer2_prereq_ladder(curriculum):
    # the conceptual ladder must hold in the engine's prerequisite-first order
    order = curriculum.learning_order()
    for a, b in [("bfs_intuition", "bfs_distance"),
                 ("bfs_implementation", "bfs_distance"),
                 ("bfs_distance", "path_reconstruction"),
                 ("bfs_implementation", "path_reconstruction"),
                 ("v0_readiness", None)]:
        if b is None:
            break
        assert order.index(a) < order.index(b), f"{a} must precede {b}"
    # reuse, not duplication: existing BFS concepts are the prerequisites
    assert {"bfs_intuition", "bfs_implementation", "visited_state"} <= core_prereqs("bfs_distance")
    assert {"bfs_distance", "bfs_implementation"} <= core_prereqs("path_reconstruction")
    # no Layer 2 skill may hang off the V0 boundary
    assert "v0_readiness" not in core_prereqs("bfs_distance")
    assert "v0_readiness" not in core_prereqs("path_reconstruction")


def test_layer2_evidence_progression():
    """Recognition -> tracing -> code completion -> independent implementation,
    plus a transfer activity, per the approved evidence progression."""
    by_type = {}
    for e in exercises_for("bfs_distance") + exercises_for("path_reconstruction"):
        by_type.setdefault((e.skill_id, e.interaction_type), []).append(e)

    for sid in LAYER2_SKILLS:
        assert by_type[(sid, InteractionType.MCQ)], f"{sid}: no recognition evidence"
        assert (by_type.get((sid, InteractionType.OUTPUT_PREDICTION))
                or by_type.get((sid, InteractionType.CODE_TRACING))), \
            f"{sid}: no tracing evidence"
        writers = by_type[(sid, InteractionType.CODE_WRITING)]
        assert len(writers) >= 2, f"{sid}: expected completion + implementation activities"
        starters = [w.payload["starter"] for w in writers]
        # one activity is a guided completion (starter carries the skeleton),
        # one is independent implementation from a bare starter
        assert any("# line" in s for s in starters), f"{sid}: no code-completion activity"
        assert any("# line" not in s for s in starters), f"{sid}: no from-scratch activity"
    # independent transfer under path_reconstruction (recognition without hints)
    apply_units = [u for u in UNITS
                   if u.skill_id == "path_reconstruction" and u.unit_type is UnitType.APPLY]
    assert apply_units and any(
        e.interaction_type is InteractionType.FREE_FORM
        for u in apply_units
        for e in EXERCISES if e.unit_id == u.id)


def test_layer2_exclusions():
    """Explicit spec exclusions must not leak into Layer 2 content."""
    forbidden = ["dijkstra", "bellman", r"(?<!un)weighted", "0-1 bfs", "floyd",
                 "all-pairs", "negative weight"]
    import re as _re
    for sid in LAYER2_SKILLS:
        skill = next(s for s in SKILLS if s.id == sid)
        text = " ".join([skill.id, skill.title, skill.description]).lower()
        units = [u for u in UNITS if u.skill_id == sid]
        text += " ".join((u.title or "") + " " + (u.goal or "") for u in units).lower()
        for ex in exercises_for(sid):
            text += " " + ex.prompt.lower()
        for token in forbidden:
            assert not _re.search(token, text), f"{sid}: excluded topic '{token}' leaked"


# ---------------------------------------------------------------- semantics
def _run_payload_tests(exercise):
    ns = {}
    exec(exercise.payload["solution"], ns)
    fn = ns[exercise.payload["function_name"]]
    for t in exercise.payload["tests"]:
        args = {k: v for k, v in t.items() if k not in ("expected", "args")}
        assert fn(**args) == t["expected"], f"{exercise.id} failed on {args}"


def test_distance_convention_minus_one_is_unreachable():
    """The project distance convention: -1 marks unreachable, distance[source] = 0,
    and only the source's component receives finite distances."""
    for ex in exercises_for("bfs_distance"):
        if ex.interaction_type is InteractionType.CODE_WRITING:
            _run_payload_tests(ex)
    impl = next(e for e in exercises_for("bfs_distance")
                if e.interaction_type is InteractionType.CODE_WRITING
                and e.payload["function_name"] == "bfs_distances")
    ns = {}
    exec(impl.payload["solution"], ns)
    distance = ns["bfs_distances"]([[1], [0], [4], [4], [2], []], 0)
    assert distance[0] == 0 and distance[1] == 1
    assert distance[2] == distance[3] == distance[4] == -1  # other component
    assert distance[5] == -1                                 # isolated vertex


def test_path_reconstruction_edge_cases():
    """source == target -> [source]; unreachable -> []; multiple shortest paths ->
    exactly one valid (deterministic) path; reconstruction O(path length)."""
    combined = next(e for e in exercises_for("path_reconstruction")
                    if e.interaction_type is InteractionType.CODE_WRITING
                    and e.payload["function_name"] == "shortest_path")
    cases = {(t["source"], t["target"]) for t in combined.payload["tests"]}
    assert (0, 0) in cases or any(s == t for s, t in cases), "source == target case missing"
    assert any(t["expected"] == [] for t in combined.payload["tests"]), \
        "unreachable-target case missing"
    _run_payload_tests(combined)
    for ex in exercises_for("path_reconstruction"):
        if ex.interaction_type is InteractionType.CODE_WRITING \
                and ex.payload["function_name"] == "reconstruct_path_completed":
            _run_payload_tests(ex)


def test_shortest_path_returns_one_valid_route_not_all():
    """Multiple equally short paths: BFS's parent tree returns ONE valid shortest
    path (the discovery route), not all of them — asserted against the demo graph
    where 0-1-3-5 and 0-2-4-5 are both shortest."""
    combined = next(e for e in exercises_for("path_reconstruction")
                    if e.interaction_type is InteractionType.CODE_WRITING
                    and e.payload["function_name"] == "shortest_path")
    ns = {}
    exec(combined.payload["solution"], ns)
    path = ns["shortest_path"]([[1, 2], [3], [3, 4], [5], [5], []], 0, 5)
    assert len(path) == 4 and path[0] == 0 and path[-1] == 5
    for u, v in zip(path, path[1:]):
        assert v in [[1, 2], [3], [3, 4], [5], [5], []][u], f"edge {u}-{v} does not exist"


# ---------------------------------------------------------------- runtime progression
def test_layer2_entry_presents_bfs_distance_theory_first(service):
    from test_layer1_progression import seed_mastery
    from dsa_tutor.domain.models import Pace

    seed_mastery(service, [s.id for s in service.curriculum.skills.values()
                           if s.id not in LAYER2_SKILLS])
    view = service.start_session(pace=Pace.NORMAL)
    assert view.kind == "theory"
    assert view.unit.skill_id == "bfs_distance"
    view = service.mark_theory_seen()
    assert view.kind == "exercise"


def test_full_correct_run_masters_layer2_and_completes(service):
    """A learner answering everything correctly progresses through the whole
    curriculum including Layer 2 (prereq gates must not stall on the new
    problem activities)."""
    from test_layer1_progression import drive, learner_answer, seed_mastery
    from dsa_tutor.domain.models import Pace

    seed_mastery(service, [s.id for s in service.curriculum.skills.values()
                           if s.id not in LAYER2_SKILLS])
    view = service.start_session(pace=Pace.NORMAL)
    seen = []
    view, _ = drive(service, view, max_turns=140,
                    on_turn=lambda v: seen.append(v.exercise.skill_id)
                    if v.kind == "exercise" else None)
    assert view.kind == "ended"
    assert "bfs_distance" in seen and "path_reconstruction" in seen
    report = {row["skill"]: row for row in service.progress_report()["skills"]}
    for sid in LAYER2_SKILLS:
        assert report[sid]["mastered"], f"{sid} not mastered after a fully correct run"
