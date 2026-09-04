"""Runtime progression regressions for the Layer 1 flow (Graph Slice A Layer 1).

Covers two learner-facing defects found in manual testing:
1. a teach unit's study text was skipped (MCQ presented before the theory turn) on
   mid-session advance, on resume, and on the read-only snapshot;
2. the engine kept re-selecting already-attempted MCQs instead of progressing, because
   the problem-readiness gate crashed on matching evidence (missing import) and only
   looked at same-skill evidence, permanently blocking problem activities whose
   capabilities are demonstrated in prerequisite skills.

The tests assert curriculum/readiness behavior — never a universal theory-first rule.
"""
from datetime import timedelta

import pytest

from conftest import correct_answer_for
from dsa_tutor.domain.engine import EngineSnapshot
from dsa_tutor.domain.mastery import MasteryState, derive_state
from dsa_tutor.domain.models import (
    EngineAction, EvidenceOutcome, EvidenceRecord, EvidenceType, LearnerState,
    MasteryDimension, Pace, utcnow,
)

LAYER1_SKILLS = {"traversal_boundary", "component_discovery", "component_enumeration"}

# learner-authored implementations (never the stored solution: verbatim copies are
# rejected by the grader's copy detection)
OWN_CODE = {
    "bfs": (
        "from collections import deque\n\n"
        "def bfs(graph, start):\n"
        "    seen = {start}\n"
        "    pending = deque([start])\n"
        "    out = []\n"
        "    while pending:\n"
        "        cur = pending.popleft()\n"
        "        out.append(cur)\n"
        "        for nb in graph[cur]:\n"
        "            if nb not in seen:\n"
        "                seen.add(nb)\n"
        "                pending.append(nb)\n"
        "    return out\n"
    ),
    "dfs": (
        "def dfs(graph, start, seen=None):\n"
        "    if seen is None:\n"
        "        seen = set()\n"
        "    seen.add(start)\n"
        "    out = [start]\n"
        "    for nb in graph[start]:\n"
        "        if nb not in seen:\n"
        "            out = out + dfs(graph, nb, seen)\n"
        "    return out\n"
    ),
    "count_reachable": (
        "def count_reachable(graph, start):\n"
        "    seen = {start}\n"
        "    todo = [start]\n"
        "    while todo:\n"
        "        v = todo.pop()\n"
        "        for w in graph[v]:\n"
        "            if w not in seen:\n"
        "                seen.add(w)\n"
        "                todo.append(w)\n"
        "    return len(seen)\n"
    ),
    "bfs_levels": (
        "from collections import deque\n\n"
        "def bfs_levels(graph, start):\n"
        "    dist = {start: 0}\n"
        "    q = deque([start])\n"
        "    while q:\n"
        "        v = q.popleft()\n"
        "        for w in graph[v]:\n"
        "            if w not in dist:\n"
        "                dist[w] = dist[v] + 1\n"
        "                q.append(w)\n"
        "    return dist\n"
    ),
    "count_components": (
        "from collections import deque\n\n"
        "def count_components(graph):\n"
        "    n = len(graph)\n"
        "    unseen = [True] * n\n"
        "    total = 0\n"
        "    for s in range(n):\n"
        "        if not unseen[s]:\n"
        "            continue\n"
        "        total += 1\n"
        "        unseen[s] = False\n"
        "        q = deque([s])\n"
        "        while q:\n"
        "            v = q.popleft()\n"
        "            for w in graph[v]:\n"
        "                if unseen[w]:\n"
        "                    unseen[w] = False\n"
        "                    q.append(w)\n"
        "    return total\n"
    ),
    "label_components": (
        "from collections import deque\n\n"
        "def label_components(graph):\n"
        "    n = len(graph)\n"
        "    comp = [-1] * n\n"
        "    cid = 0\n"
        "    for s in range(n):\n"
        "        if comp[s] != -1:\n"
        "            continue\n"
        "        comp[s] = cid\n"
        "        q = deque([s])\n"
        "        while q:\n"
        "            v = q.popleft()\n"
        "            for w in graph[v]:\n"
        "                if comp[w] == -1:\n"
        "                    comp[w] = cid\n"
        "                    q.append(w)\n"
        "        cid += 1\n"
        "    return comp\n"
    ),
    # Layer 2 learner implementations
    "bfs_distances": (
        "from collections import deque\n\n"
        "def bfs_distances(graph, start):\n"
        "    step = {start: 0}\n"
        "    todo = deque([start])\n"
        "    while todo:\n"
        "        v = todo.popleft()\n"
        "        for w in graph[v]:\n"
        "            if w not in step:\n"
        "                step[w] = step[v] + 1\n"
        "                todo.append(w)\n"
        "    return [step.get(i, -1) for i in range(len(graph))]\n"
    ),
    "bfs_distances_completed": (
        "from collections import deque\n\n"
        "def bfs_distances_completed(graph, start):\n"
        "    n = len(graph)\n"
        "    distance = [-1] * n\n"
        "    distance[start] = 0\n"
        "    queue = deque([start])\n"
        "    while queue:\n"
        "        v = queue.popleft()\n"
        "        for nxt in graph[v]:\n"
        "            if distance[nxt] == -1:\n"
        "                distance[nxt] = 1 + distance[v]\n"
        "                queue.append(nxt)\n"
        "    return distance\n"
    ),
    "reconstruct_path_completed": (
        "def reconstruct_path_completed(parent, source, target):\n"
        "    if target != source and parent[target] == -1:\n"
        "        return []\n"
        "    path = []\n"
        "    v = target\n"
        "    while True:\n"
        "        path.append(v)\n"
        "        if source == v:\n"
        "            break\n"
        "        v = parent[v]\n"
        "    path.reverse()\n"
        "    return path\n"
    ),
    "shortest_path": (
        "from collections import deque\n\n"
        "def shortest_path(graph, source, target):\n"
        "    if source == target:\n"
        "        return [source]\n"
        "    prev = {source: None}\n"
        "    todo = deque([source])\n"
        "    while todo:\n"
        "        v = todo.popleft()\n"
        "        for w in graph[v]:\n"
        "            if w not in prev:\n"
        "                prev[w] = v\n"
        "                todo.append(w)\n"
        "    if target not in prev:\n"
        "        return []\n"
        "    out = []\n"
        "    v = target\n"
        "    while v is not None:\n"
        "        out.append(v)\n"
        "        v = prev[v]\n"
        "    return out[::-1]\n"
    ),
    # Layer 3 learner implementations
    "detect_cycle_completed": (
        "def detect_cycle_completed(graph):\n"
        "    n = len(graph)\n"
        "    seen = [False] * n\n"
        "\n"
        "    def go(v, prev):\n"
        "        seen[v] = True\n"
        "        for nxt in graph[v]:\n"
        "            if nxt == prev:\n"
        "                continue\n"
        "            if seen[nxt]:\n"
        "                return True\n"
        "            if go(nxt, v):\n"
        "                return True\n"
        "        return False\n"
        "\n"
        "    for s in range(n):\n"
        "        if not seen[s] and go(s, -1):\n"
        "            return True\n"
        "    return False\n"
    ),
    "has_cycle_undirected": (
        "def has_cycle_undirected(graph):\n"
        "    seen = set()\n"
        "\n"
        "    def walk(v, came_from):\n"
        "        seen.add(v)\n"
        "        for nxt in graph[v]:\n"
        "            if nxt == came_from:\n"
        "                continue\n"
        "            if nxt in seen:\n"
        "                return True\n"
        "            if walk(nxt, v):\n"
        "                return True\n"
        "        return False\n"
        "\n"
        "    return any(walk(s, None) for s in range(len(graph)) if s not in seen)\n"
    ),
    "has_cycle_bfs": (
        "from collections import deque\n\n"
        "def has_cycle_bfs(graph):\n"
        "    seen = set()\n"
        "    for s in range(len(graph)):\n"
        "        if s in seen:\n"
        "            continue\n"
        "        seen.add(s)\n"
        "        todo = deque([(s, None)])\n"
        "        while todo:\n"
        "            v, came_from = todo.popleft()\n"
        "            for nxt in graph[v]:\n"
        "                if nxt == came_from:\n"
        "                    continue\n"
        "                if nxt in seen:\n"
        "                    return True\n"
        "                seen.add(nxt)\n"
        "                todo.append((nxt, v))\n"
        "    return False\n"
    ),
}


def learner_answer(exercise):
    t = exercise.interaction_type.value
    if t == "code_writing":
        return OWN_CODE[exercise.payload["function_name"]]
    if t in {"output_prediction", "code_tracing"}:
        # the frontend submits one output line per row (newline-joined)
        return exercise.payload["expected_output"]
    return correct_answer_for(exercise)


def seed_mastery(service, skill_ids):
    """Give each skill independent evidence of every required evidence type."""
    now = utcnow()
    for sid in skill_ids:
        skill = service.curriculum.skill(sid)
        for i, etype in enumerate(sorted(skill.evidence_requirements,
                                         key=lambda e: e.value)):
            for k in range(2):
                service.storage.evidence.append(EvidenceRecord(
                    attempt_id=None, skill_id=sid,
                    dimension=MasteryDimension.KNOWLEDGE, evidence_type=etype,
                    outcome=EvidenceOutcome.INDEPENDENT_SUCCESS, weight=1.0,
                    created_at=now - timedelta(days=1, minutes=10 * i + k)))


def seed_v0_mastered(service):
    seed_mastery(service, [s.id for s in service.curriculum.skills.values()
                           if s.id not in LAYER1_SKILLS])


def drive(service, view, max_turns=120, on_turn=None):
    """Answer everything correctly; returns (view, history). Handles theory turns."""
    history = []
    for _ in range(max_turns):
        if on_turn is not None:
            on_turn(view)
        if view.kind == "ended":
            return view, history
        if view.kind in {"info", "notice"}:
            return view, history
        if view.kind == "theory":
            history.append(("theory", view.unit.skill_id, None))
            view = service.mark_theory_seen()
            continue
        if view.kind == "exercise":
            history.append(("exercise", view.exercise.skill_id, view.exercise.id))
            view = service.submit_response(learner_answer(view.exercise))
            continue
        return view, history
    raise AssertionError(f"drive loop guard tripped after {max_turns} turns")


# ---------------------------------------------------------------- Test 1: theory selection
def test_layer1_entry_presents_teach_theory_before_first_mcq(service):
    seed_v0_mastered(service)
    view = service.start_session(pace=Pace.NORMAL)
    # entering the Layer 1 path, the first learning activity of the new skill is its
    # teach unit's study text, then that unit's first check — curriculum-driven order
    assert view.kind == "theory"
    assert view.unit.skill_id == "traversal_boundary"
    assert view.unit.unit_type.value == "teach"
    assert view.unit.theory
    view = service.mark_theory_seen()
    assert view.kind == "exercise"
    assert view.exercise.skill_id == "traversal_boundary"
    assert service.curriculum.unit(view.exercise.unit_id).unit_type.value == "teach"
    assert f"theory:{view.exercise.unit_id}" in service._state().completed_unit_ids


def test_midsession_advance_into_new_skill_shows_theory_first(service):
    seed_v0_mastered(service)
    view = service.start_session(pace=Pace.NORMAL)
    # finish traversal_boundary entirely; the next decision advances into
    # component_discovery's teach unit
    for _ in range(8):
        if view.kind == "theory":
            if view.unit.skill_id == "component_discovery":
                break
            view = service.mark_theory_seen()
        elif view.kind == "exercise" and view.exercise.skill_id == "traversal_boundary":
            view = service.submit_response(learner_answer(view.exercise))
        else:
            break
    assert view.kind == "theory", "mid-session advance must present the new teach unit's theory"
    assert view.unit.skill_id == "component_discovery"
    assert f"theory:{view.unit.id}" not in service._state().completed_unit_ids


def test_resume_with_pending_theory_shows_theory_not_the_check(service):
    seed_v0_mastered(service)
    view = service.start_session(pace=Pace.NORMAL)
    assert view.kind == "theory"
    unit_id = view.unit.id
    service.stop_session("paused while studying")
    view = service.start_session(resume=True)
    assert view.kind == "theory", "resume must not skip pending study text"
    assert view.unit.id == unit_id
    view = service.mark_theory_seen()
    assert view.kind == "exercise"


def test_snapshot_shows_pending_theory_before_current_check(service):
    seed_v0_mastered(service)
    view = service.start_session(pace=Pace.NORMAL)
    assert view.kind == "theory"
    # the read-only snapshot (frontend refresh / active-session resume) must keep the
    # same precedence: pending study text outranks re-presenting the current check
    snapshot = service.session_snapshot()
    assert snapshot.kind == "theory"
    assert snapshot.unit.id == view.unit.id


# ---------------------------------------------------------------- Test 2: MCQ progression
def test_mcq_answer_does_not_trap_engine_on_component_enumeration(service):
    seed_v0_mastered(service)
    view = service.start_session(pace=Pace.NORMAL)
    seen_exercises = []
    code_writing_seen = []
    consecutive = 1

    def track(v):
        nonlocal consecutive
        if v.kind == "exercise":
            if seen_exercises and seen_exercises[-1] == v.exercise.id:
                consecutive += 1
            else:
                consecutive = 1
            seen_exercises.append(v.exercise.id)
            if v.exercise.skill_id == "component_enumeration" \
                    and v.exercise.interaction_type.value == "code_writing":
                code_writing_seen.append(v.exercise.id)
        else:
            consecutive = 1

    view, _ = drive(service, view, max_turns=100, on_turn=track)
    # the flow reaches a natural end: all Layer 1 skills (and the curriculum) complete
    assert view.kind == "ended"
    assert "component_enumeration" in (view.extra.get("message") or "") or \
        view.decision.action == EngineAction.END_SESSION
    # the problem-scope activities are actually reached and passed — the engine did not
    # hide behind endless MCQ re-selection
    assert code_writing_seen, "component_enumeration code-writing problems were never served"
    # no already-attempted activity is selected indefinitely
    assert consecutive <= 2, f"exercise {seen_exercises[-1]} selected {consecutive}x in a row"
    mastered = service.progress_report()["skills"]
    by_id = {row["skill"]: row for row in mastered}
    for sid in LAYER1_SKILLS:
        assert by_id[sid]["mastered"], f"{sid} not mastered after a fully correct run"


def test_readiness_gate_accepts_capabilities_from_prerequisite_skills(service):
    engine = service.engine
    ex = next(e for e in service.curriculum.exercises.values()
              if e.skill_id == "bfs_implementation"
              and e.interaction_type.value == "code_writing")
    now = utcnow()

    def snapshot_with(records):
        evidence = {}
        for r in records:
            evidence.setdefault(r.skill_id, []).append(r)
        return EngineSnapshot(state=LearnerState(learner_id=1), assessments={},
                              evidence=evidence, session=None)

    # TRACE demonstrated in the prerequisite skill, RECOGNITION in the skill itself
    records = [
        EvidenceRecord(attempt_id=None, skill_id="bfs_implementation",
                       dimension=MasteryDimension.KNOWLEDGE,
                       evidence_type=EvidenceType.RECOGNITION,
                       outcome=EvidenceOutcome.INDEPENDENT_SUCCESS, weight=1.0,
                       created_at=now),
        EvidenceRecord(attempt_id=None, skill_id="bfs_manual_tracing",
                       dimension=MasteryDimension.EXECUTION,
                       evidence_type=EvidenceType.TRACE,
                       outcome=EvidenceOutcome.INDEPENDENT_SUCCESS, weight=1.0,
                       created_at=now - timedelta(days=1)),
    ]
    ready, message = engine.check_readiness(snapshot_with(records), ex)
    assert ready, message  # would NameError before the fix once matching evidence existed

    # without TRACE anywhere in the foundation the problem stays gated
    ready, message = engine.check_readiness(snapshot_with(records[:1]), ex)
    assert not ready
    assert "TRACE" in message


def test_reduce_difficulty_serves_a_different_simpler_activity(service):
    engine = service.engine
    skill_id = "visited_state"
    teach_unit = next(u for u in service.curriculum.units.values()
                      if u.skill_id == skill_id and u.unit_type.value == "teach")
    ex = service.curriculum.exercises_for_unit(teach_unit.id)[0]
    state = LearnerState(learner_id=1, current_skill_id=skill_id,
                         exercise_failures={ex.id: 3})
    now = utcnow()
    records = [EvidenceRecord(attempt_id=None, skill_id=skill_id,
                              dimension=MasteryDimension.KNOWLEDGE,
                              evidence_type=EvidenceType.RECOGNITION,
                              outcome=EvidenceOutcome.FAILED, weight=1.0,
                              created_at=now)]
    snapshot = EngineSnapshot(state=state, assessments={}, evidence={skill_id: records},
                              session=None, recent_scores=[0.0, 0.0])
    decision = engine.decide_after_attempt(snapshot, ex, 0.0, False, 0, False)
    assert decision.action == EngineAction.REDUCE_DIFFICULTY
    assert decision.exercise_id != ex.id, \
        "the smaller step must be a different activity, not the failed one re-served"


# ---------------------------------------------------------------- Test 3: V0 unchanged
def test_v0_progression_completes_past_first_problem_activity(service):
    """A fresh learner answering correctly progresses through V0 — previously the very
    first problem activity (bfs_implementation) was permanently blocked and the flow
    stalled on the unit's MCQs. V0 ordering/semantics themselves are unchanged."""
    view = service.start_session(pace=Pace.NORMAL)
    reached = []

    def track(v):
        if v.kind == "exercise":
            reached.append((v.exercise.skill_id, v.exercise.interaction_type.value))

    view, _ = drive(service, view, max_turns=320, on_turn=track)
    assert view.kind == "ended"
    skills_seen = [s for s, _ in reached]
    assert "bfs_implementation" in skills_seen
    assert ("bfs_implementation", "code_writing") in reached, \
        "the first V0 problem activity must be servable"
    # curriculum order preserved: BFS implementation before DFS implementation,
    # Layer 1 skills after their traversal prerequisites
    assert skills_seen.index("bfs_implementation") < skills_seen.index("dfs_implementation")
    assert skills_seen.index("dfs_manual_tracing") < skills_seen.index("traversal_boundary")
    report = {row["skill"]: row for row in service.progress_report()["skills"]}
    for sid in ["graph_definition", "bfs_implementation", "dfs_implementation",
                "traversal_boundary", "component_enumeration"]:
        assert report[sid]["mastered"], f"{sid} not mastered"
