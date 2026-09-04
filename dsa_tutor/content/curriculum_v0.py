"""V0 curriculum: Graph foundations -> representation -> traversal -> BFS/DFS.

Encoded from planning doc 02-v0-graph-curriculum-and-skill-graph.md.
- 38 skills across Modules A-F (review RC-07), language-independent (exercise-level
- `language` attribute = python in V0). Learning Activities are represented by the
- Exercise class (legacy name kept for implementation compatibility; see models.py).
- Prerequisites form a DAG; the learner-facing curriculum is a tree.
- v0_readiness is the boundary skill: the engine can never advance beyond it.
"""
from __future__ import annotations

from ..domain.models import (
    ActivityRole, ActivityScope, EvidenceType, Exercise, InteractionType, LearningUnit,
    MasteryDimension as MD, PrereqStrength as PS, Skill, SkillPrerequisite, Topic, UnitType,
)

TOPICS = [Topic(id="graph_v0", title="Graph Fundamentals (V0)", ordering=1)]

K = MD.KNOWLEDGE
E = MD.EXECUTION
R = MD.REASONING
T = MD.TRANSFER


def _skill(sid, title, order, section, comp, req, boundary=False):
    return Skill(
        id=sid, title=title, topic_id="graph_v0", ordering=order, section=section,
        complexity={K: comp[0], E: comp[1], R: comp[2], T: comp[3]},
        is_boundary=boundary, required_dimensions=frozenset(req),
    )


SKILLS = [
    # --- Graph Foundations (1-8) ---
    _skill("graph_definition", "What is a graph?", 1, "Graph Foundations", (1, 1, 1, 1), {K}),
    _skill("vertices_edges", "Vertices and edges", 2, "Graph Foundations", (1, 1, 1, 1), {K}),
    _skill("directed_vs_undirected", "Directed vs undirected graphs", 3, "Graph Foundations", (2, 1, 2, 2), {K, R}),
    _skill("weighted_vs_unweighted", "Weighted vs unweighted graphs", 4, "Graph Foundations", (1, 1, 1, 2), {K}),
    _skill("degree", "Degree of a vertex", 5, "Graph Foundations", (2, 2, 2, 2), {K, E}),
    _skill("path", "Path", 6, "Graph Foundations", (2, 1, 2, 2), {K, R}),
    _skill("cycle", "Cycle", 7, "Graph Foundations", (2, 1, 2, 2), {K, R}),
    _skill("connectedness", "Connectedness", 8, "Graph Foundations", (2, 1, 2, 2), {K, R}),
    # --- Graph Representation (9-12) ---
    _skill("edge_list", "Edge list", 9, "Graph Representation", (1, 2, 1, 1), {K, E}),
    _skill("adjacency_matrix", "Adjacency matrix", 10, "Graph Representation", (2, 3, 2, 2), {K, E}),
    _skill("adjacency_list", "Adjacency list", 11, "Graph Representation", (2, 3, 2, 2), {K, E}),
    _skill("choosing_representation", "Choosing a representation", 12, "Graph Representation", (3, 2, 3, 3), {R, T}),
    # --- Traversal Fundamentals (13-17) ---
    _skill("why_traversal", "Why traversal?", 13, "Traversal Fundamentals", (2, 1, 2, 2), {K, R}),
    _skill("traversal_state", "Traversal state", 14, "Traversal Fundamentals", (2, 2, 2, 2), {K}),
    _skill("visited_state", "Visited state", 15, "Traversal Fundamentals", (3, 3, 3, 3), {K, E, R}),
    _skill("traversal_order", "Traversal order", 16, "Traversal Fundamentals", (2, 2, 2, 2), {K, E}),
    _skill("manual_tracing", "Manual traversal tracing", 17, "Traversal Fundamentals", (3, 3, 3, 2), {E, R}),
    # --- BFS (18-24) ---
    _skill("bfs_intuition", "BFS intuition", 18, "BFS", (3, 1, 3, 3), {K, R}),
    _skill("queue_mechanism", "Queue as the core mechanism", 19, "BFS", (3, 3, 3, 2), {K, E}),
    _skill("bfs_visited_handling", "BFS visited handling", 20, "BFS", (3, 3, 3, 3), {E, R}),
    _skill("bfs_manual_tracing", "Manual BFS tracing", 21, "BFS", (3, 3, 3, 3), {E, R}),
    _skill("bfs_implementation", "Plain BFS implementation", 22, "BFS", (3, 4, 3, 3), {E, K}),
    _skill("bfs_time_complexity", "BFS time complexity", 23, "BFS", (3, 1, 4, 3), {R}),
    _skill("bfs_space_complexity", "BFS space complexity", 24, "BFS", (3, 1, 4, 3), {R}),
    # --- DFS (25-32) ---
    _skill("dfs_intuition", "DFS intuition", 25, "DFS", (3, 1, 3, 3), {K, R}),
    _skill("recursion_mechanism", "Recursion as the core mechanism", 26, "DFS", (3, 3, 4, 2), {K, E}),
    _skill("dfs_visited_handling", "DFS visited handling", 27, "DFS", (3, 3, 3, 3), {E, R}),
    _skill("dfs_manual_tracing", "Manual DFS tracing", 28, "DFS", (3, 3, 3, 3), {E, R}),
    _skill("dfs_implementation", "Plain recursive DFS implementation", 29, "DFS", (3, 4, 3, 3), {E, K}),
    _skill("dfs_time_complexity", "DFS time complexity", 30, "DFS", (3, 1, 4, 3), {R}),
    _skill("dfs_space_complexity", "DFS space complexity", 31, "DFS", (3, 1, 4, 3), {R}),
    _skill("explicit_stack_dfs", "Explicit-stack DFS", 32, "DFS", (4, 4, 4, 3), {K, E}),
    # --- Comparison & Readiness (33-36) ---
    _skill("bfs_vs_dfs", "BFS vs DFS", 33, "Comparison & Readiness", (4, 2, 4, 4), {R, T}),
    _skill("recognizing_traversal", "Recognizing traversal situations", 34, "Comparison & Readiness", (4, 1, 4, 4), {T, R}),
    _skill("traversal_application", "Basic traversal application", 35, "Comparison & Readiness", (4, 4, 4, 5), {E, T}),
    _skill("v0_readiness", "V0 readiness assessment", 36, "Comparison & Readiness", (4, 4, 4, 4), {K, E, R, T}, boundary=True),
    # --- review RC-07 additions ---
    _skill("adjacency", "Adjacency", 45, "Module A - Graph Mental Model", (1, 1, 1, 1), {K}),
    _skill("conversion_between_representations", "Converting between representations", 46, "Module B - Graph Representation", (3, 3, 3, 2), {K, E}),

    # --- Layer 1: Reachability → Connected Components (Graph Slice A) ---
    # traversal_boundary: understand one traversal = exactly one connected component
    _skill("traversal_boundary", "Traversal boundary", 47, "Module F - Integration & Application",
           (3, 2, 3, 3), {K, R}),
    # component_discovery: an unvisited vertex after traversal can indicate another component
    _skill("component_discovery", "Component discovery", 48, "Module F - Integration & Application",
           (3, 3, 3, 3), {K, E, R}),
    # component_enumeration: repeat traversal from unvisited vertices to enumerate all components
    _skill("component_enumeration", "Component enumeration", 49, "Module F - Integration & Application",
           (3, 4, 4, 4), {E, R, T}),

    # --- Layer 2: Unweighted Shortest Paths → Path Reconstruction (Graph Slice A) ---
    # bfs_distance: BFS levels ARE distances; a distance array with -1 = unreachable
    _skill("bfs_distance", "BFS distance", 50, "Module F - Integration & Application",
           (3, 3, 4, 3), {K, E, R}),
    # path_reconstruction: parent/predecessor tracking → rebuild the actual shortest path
    _skill("path_reconstruction", "Path reconstruction", 51, "Module F - Integration & Application",
           (3, 4, 4, 4), {E, R, T}),

    # --- Layer 3: Undirected Cycle Detection (Graph Slice A) ---
    # cycle_encounter_reasoning: interpret meeting a visited neighbor while traversing
    # an undirected graph — not every visited neighbor is cycle evidence
    _skill("cycle_encounter_reasoning", "Cycle encounter reasoning", 52,
           "Module F - Integration & Application", (3, 2, 3, 3), {K, R}),
    # parent_aware_traversal: distinguish the parent edge (the arrival edge seen from
    # the other side) from a genuine cycle encounter
    _skill("parent_aware_traversal", "Parent-aware traversal", 53,
           "Module F - Integration & Application", (3, 3, 4, 3), {K, E, R}),
    # undirected_cycle_detection: the synthesis — DFS detection, disconnected graphs,
    # BFS variant with (vertex, parent) queue entries, self-loops, O(V+E)
    _skill("undirected_cycle_detection", "Undirected cycle detection", 54,
           "Module F - Integration & Application", (4, 4, 4, 4), {E, R, T}),
]

PREREQS = [
    SkillPrerequisite("vertices_edges", "graph_definition", PS.CORE),
    SkillPrerequisite("adjacency", "vertices_edges", PS.CORE),
    SkillPrerequisite("directed_vs_undirected", "vertices_edges", PS.CORE),
    SkillPrerequisite("weighted_vs_unweighted", "vertices_edges", PS.CORE),
    SkillPrerequisite("degree", "vertices_edges", PS.CORE),
    SkillPrerequisite("path", "vertices_edges", PS.CORE),
    SkillPrerequisite("path", "directed_vs_undirected", PS.SUPPORTING),
    SkillPrerequisite("cycle", "path", PS.CORE),
    SkillPrerequisite("connectedness", "path", PS.CORE),
    SkillPrerequisite("connectedness", "degree", PS.SUPPORTING),
    SkillPrerequisite("edge_list", "vertices_edges", PS.CORE),
    SkillPrerequisite("edge_list", "directed_vs_undirected", PS.SUPPORTING),
    SkillPrerequisite("adjacency_matrix", "edge_list", PS.CORE),
    SkillPrerequisite("adjacency_matrix", "degree", PS.SUPPORTING),
    SkillPrerequisite("adjacency_list", "edge_list", PS.CORE),
    SkillPrerequisite("adjacency_list", "adjacency_matrix", PS.SUPPORTING),
    SkillPrerequisite("conversion_between_representations", "adjacency_matrix", PS.CORE),
    SkillPrerequisite("conversion_between_representations", "adjacency_list", PS.CORE),
    SkillPrerequisite("choosing_representation", "adjacency_matrix", PS.CORE),
    SkillPrerequisite("choosing_representation", "adjacency_list", PS.CORE),
    SkillPrerequisite("why_traversal", "connectedness", PS.CORE),
    SkillPrerequisite("why_traversal", "choosing_representation", PS.SUPPORTING),
    SkillPrerequisite("traversal_state", "why_traversal", PS.CORE),
    SkillPrerequisite("visited_state", "traversal_state", PS.CORE),
    SkillPrerequisite("traversal_order", "traversal_state", PS.CORE),
    SkillPrerequisite("manual_tracing", "traversal_order", PS.CORE),
    SkillPrerequisite("manual_tracing", "visited_state", PS.CORE),
    SkillPrerequisite("bfs_intuition", "manual_tracing", PS.CORE),
    SkillPrerequisite("bfs_intuition", "visited_state", PS.SUPPORTING),
    SkillPrerequisite("queue_mechanism", "bfs_intuition", PS.CORE),
    SkillPrerequisite("bfs_visited_handling", "visited_state", PS.CORE),
    SkillPrerequisite("bfs_visited_handling", "queue_mechanism", PS.CORE),
    SkillPrerequisite("bfs_manual_tracing", "bfs_visited_handling", PS.CORE),
    SkillPrerequisite("bfs_manual_tracing", "manual_tracing", PS.SUPPORTING),
    SkillPrerequisite("bfs_implementation", "bfs_manual_tracing", PS.CORE),
    SkillPrerequisite("bfs_implementation", "bfs_visited_handling", PS.CORE),
    SkillPrerequisite("bfs_implementation", "adjacency_list", PS.SUPPORTING),
    SkillPrerequisite("bfs_time_complexity", "bfs_implementation", PS.CORE),
    SkillPrerequisite("bfs_time_complexity", "choosing_representation", PS.SUPPORTING),
    SkillPrerequisite("bfs_space_complexity", "bfs_visited_handling", PS.CORE),
    SkillPrerequisite("bfs_space_complexity", "bfs_time_complexity", PS.SUPPORTING),
    SkillPrerequisite("dfs_intuition", "manual_tracing", PS.CORE),
    SkillPrerequisite("dfs_intuition", "visited_state", PS.SUPPORTING),
    SkillPrerequisite("recursion_mechanism", "dfs_intuition", PS.CORE),
    SkillPrerequisite("dfs_visited_handling", "visited_state", PS.CORE),
    SkillPrerequisite("dfs_visited_handling", "recursion_mechanism", PS.CORE),
    SkillPrerequisite("dfs_manual_tracing", "dfs_visited_handling", PS.CORE),
    SkillPrerequisite("dfs_manual_tracing", "manual_tracing", PS.SUPPORTING),
    SkillPrerequisite("dfs_implementation", "dfs_manual_tracing", PS.CORE),
    SkillPrerequisite("dfs_implementation", "dfs_visited_handling", PS.CORE),
    SkillPrerequisite("dfs_implementation", "adjacency_list", PS.SUPPORTING),
    SkillPrerequisite("dfs_time_complexity", "dfs_implementation", PS.CORE),
    SkillPrerequisite("dfs_space_complexity", "dfs_visited_handling", PS.CORE),
    SkillPrerequisite("dfs_space_complexity", "dfs_time_complexity", PS.SUPPORTING),
    SkillPrerequisite("explicit_stack_dfs", "dfs_implementation", PS.CORE),
    SkillPrerequisite("bfs_vs_dfs", "bfs_time_complexity", PS.CORE),
    SkillPrerequisite("bfs_vs_dfs", "dfs_time_complexity", PS.CORE),
    SkillPrerequisite("bfs_vs_dfs", "bfs_intuition", PS.SUPPORTING),
    SkillPrerequisite("bfs_vs_dfs", "dfs_intuition", PS.SUPPORTING),
    SkillPrerequisite("recognizing_traversal", "bfs_vs_dfs", PS.CORE),
    SkillPrerequisite("traversal_application", "recognizing_traversal", PS.CORE),
    SkillPrerequisite("traversal_application", "bfs_implementation", PS.CORE),
    SkillPrerequisite("traversal_application", "dfs_implementation", PS.CORE),
    SkillPrerequisite("v0_readiness", "traversal_application", PS.CORE),
    SkillPrerequisite("v0_readiness", "bfs_vs_dfs", PS.CORE),
    SkillPrerequisite("v0_readiness", "bfs_space_complexity", PS.SUPPORTING),
    SkillPrerequisite("v0_readiness", "dfs_space_complexity", PS.SUPPORTING),

    # --- Layer 1: Reachability → Connected Components ---
    SkillPrerequisite("traversal_boundary", "visited_state", PS.CORE),
    SkillPrerequisite("traversal_boundary", "bfs_manual_tracing", PS.CORE),
    SkillPrerequisite("traversal_boundary", "dfs_manual_tracing", PS.CORE),
    SkillPrerequisite("component_discovery", "traversal_boundary", PS.CORE),
    SkillPrerequisite("component_discovery", "connectedness", PS.SUPPORTING),
    SkillPrerequisite("component_enumeration", "component_discovery", PS.CORE),
    SkillPrerequisite("component_enumeration", "bfs_implementation", PS.CORE),
    SkillPrerequisite("component_enumeration", "dfs_implementation", PS.CORE),

    # --- Layer 2: Unweighted Shortest Paths → Path Reconstruction ---
    SkillPrerequisite("bfs_distance", "bfs_intuition", PS.CORE),
    SkillPrerequisite("bfs_distance", "bfs_implementation", PS.CORE),
    SkillPrerequisite("bfs_distance", "visited_state", PS.CORE),
    SkillPrerequisite("bfs_distance", "bfs_manual_tracing", PS.SUPPORTING),
    SkillPrerequisite("bfs_distance", "connectedness", PS.SUPPORTING),
    SkillPrerequisite("path_reconstruction", "bfs_distance", PS.CORE),
    SkillPrerequisite("path_reconstruction", "bfs_implementation", PS.CORE),
    SkillPrerequisite("path_reconstruction", "bfs_manual_tracing", PS.SUPPORTING),

    # --- Layer 3: Undirected Cycle Detection ---
    SkillPrerequisite("cycle_encounter_reasoning", "cycle", PS.CORE),
    SkillPrerequisite("cycle_encounter_reasoning", "dfs_visited_handling", PS.CORE),
    SkillPrerequisite("cycle_encounter_reasoning", "bfs_visited_handling", PS.SUPPORTING),
    SkillPrerequisite("cycle_encounter_reasoning", "dfs_manual_tracing", PS.SUPPORTING),
    SkillPrerequisite("parent_aware_traversal", "cycle_encounter_reasoning", PS.CORE),
    SkillPrerequisite("parent_aware_traversal", "dfs_implementation", PS.CORE),
    SkillPrerequisite("parent_aware_traversal", "path_reconstruction", PS.SUPPORTING),
    SkillPrerequisite("undirected_cycle_detection", "parent_aware_traversal", PS.CORE),
    SkillPrerequisite("undirected_cycle_detection", "dfs_implementation", PS.CORE),
    SkillPrerequisite("undirected_cycle_detection", "component_enumeration", PS.SUPPORTING),
    SkillPrerequisite("undirected_cycle_detection", "bfs_implementation", PS.SUPPORTING),
]

# ------------------------------------------------------------- theory ----
THEORY = {
    "graph_definition": (
        "A graph is a way to represent things and the relationships between them. The 'things' are "
        "called vertices (or nodes) and the relationships are called edges. Graphs are everywhere: "
        "friend networks, road maps, the web, prerequisites between courses. Unlike a list, a graph "
        "does not impose a single line of order — any vertex may connect to any other."
    ),
    "vertices_edges": (
        "A vertex (node) is one entity: a person, a city, a web page. An edge connects two vertices "
        "and represents a relationship: a friendship, a road, a link. In code we usually name "
        "vertices with strings or integers, and an edge is just a pair like (A, B). An edge may be "
        "one-way or two-way depending on what it models."
    ),
    "directed_vs_undirected": (
        "In an undirected graph an edge works both ways: if A-B exists, you can go A to B and B to A "
        "— like a friendship. In a directed graph each edge has a direction: A→B does not imply B→A "
        "— like Twitter follows or one-way streets. When you model a problem, decide early which one "
        "you have, because traversal follows edge directions in directed graphs."
    ),
    "weighted_vs_unweighted": (
        "An unweighted graph treats every edge the same: crossing any edge costs one step. A weighted "
        "graph attaches a number (cost, distance, time) to each edge. For V0 we work unweighted — "
        "this is exactly the setting where BFS finds shortest paths by step count."
    ),
    "degree": (
        "The degree of a vertex is the number of edges attached to it. In a directed graph we split "
        "it: in-degree (arrows coming in) and out-degree (arrows going out). Degree tells you how "
        "connected a vertex is; in an adjacency list, the degree of u is simply len(graph[u])."
    ),
    "path": (
        "A path is a sequence of vertices where each consecutive pair is connected by an edge: "
        "A → B → D is a path if A-B and B-D are edges. A simple path never repeats a vertex. Path "
        "length is the number of edges used. Reachability means 'a path exists from u to v'."
    ),
    "cycle": (
        "A cycle is a path that starts and ends at the same vertex without reusing edges: A → B → C "
        "→ A. Graphs without cycles are acyclic; trees are connected acyclic graphs. Cycles matter "
        "for traversal: without extra memory, following a cycle can loop forever."
    ),
    "connectedness": (
        "A graph is connected when every vertex can reach every other vertex through some path. If "
        "the graph splits into pieces with no path between them, each piece is a separate connected "
        "component. A traversal started from one vertex only ever reaches that vertex's component."
    ),
    "edge_list": (
        "The simplest representation: keep a list of all edges, e.g. [('A','B'), ('B','C')]. It is "
        "compact and easy to build, but answering 'who are the neighbors of B?' requires scanning "
        "the whole list — O(E) per query. Good for input formats and algorithms that process edges "
        "one by one."
    ),
    "adjacency_matrix": (
        "A V×V grid where cell [i][j] = 1 means an edge from vertex i to vertex j. Checking 'is "
        "there an edge u→v?' is O(1). The cost is memory: O(V²) cells even when the graph has few "
        "edges, and finding all neighbors of one vertex means scanning a whole row, O(V)."
    ),
    "adjacency_list": (
        "For each vertex, keep a list of its neighbors: graph = {'A': ['B', 'C'], ...}. Memory is "
        "O(V+E), iterating neighbors of u takes time proportional to degree(u), and it is the "
        "standard representation for traversal algorithms like BFS and DFS. Checking one specific "
        "edge is O(degree(u)) instead of O(1)."
    ),
    "choosing_representation": (
        "Choose by operations and shape: dense graph + constant-time edge lookup → adjacency matrix; "
        "sparse graph (most real networks) + neighbor iteration for traversal → adjacency list. "
        "BFS/DFS iterate neighbors repeatedly, so with an adjacency list their cost is O(V+E); with "
        "a matrix each neighbor scan is O(V), making traversal O(V²)."
    ),
    "why_traversal": (
        "Traversal is the systematic way to visit every vertex reachable from a starting point. "
        "Almost every graph problem starts here: reachability, counting components, finding "
        "shortest steps, exploring states. Two orders of exploration matter in V0: BFS (level by "
        "level) and DFS (deep first). Everything else is bookkeeping around them."
    ),
    "traversal_state": (
        "While traversing you always carry state: the current vertex, the set of vertices already "
        "visited, and the frontier — vertices discovered but not yet processed (a queue for BFS, a "
        "stack or the recursion call stack for DFS). Writing this state down on paper is the single "
        "best way to understand what BFS/DFS actually do."
    ),
    "visited_state": (
        "The visited set is your memory of where you have already been. Before processing or "
        "enqueuing a neighbor you check it. Without it, any cycle throws you into an infinite loop, "
        "and even without cycles you would process the same vertex many times. With it, every "
        "vertex is processed at most once — the key fact behind O(V+E) complexity."
    ),
    "traversal_order": (
        "The data structure decides the order. Take from the front (queue) → oldest discovery first "
        "→ level by level → BFS. Take from the end (stack / recursion) → newest discovery first → "
        "dive deep, backtrack → DFS. Same graph, same visited idea, different visit order."
    ),
    "manual_tracing": (
        "To trace by hand, keep a table: current step, the frontier contents, the visited set, and "
        "the output order. Process one vertex at a time exactly as the code would, no skipping. "
        "Tracing before coding is how you debug your mental model cheaply — most BFS/DFS bugs are "
        "visible in the trace before they appear in code."
    ),
    "bfs_intuition": (
        "BFS explores like ripples in water: first everything at distance 1 from the start, then "
        "distance 2, and so on. That is why, in an unweighted graph, the first time BFS reaches a "
        "vertex it has found a shortest path (fewest edges) to it. Implementation: a queue holds "
        "the frontier; visited prevents re-entry."
    ),
    "queue_mechanism": (
        "A queue is FIFO: first in, first out — append to the back, popleft from the front. BFS "
        "uses it to preserve discovery order: older vertices (closer to start) are processed "
        "before newer ones (farther). Swap the queue for a stack and the exploration order "
        "changes completely — that is the DFS direction."
    ),
    "bfs_visited_handling": (
        "In BFS, mark a neighbor visited at enqueue time, not at dequeue time. If you mark only "
        "when dequeuing, the same vertex can sit in the queue multiple times, wasting time and "
        "memory (and on some graphs exploding). Enqueue-time marking guarantees each vertex enters "
        "the queue at most once."
    ),
    "bfs_manual_tracing": (
        "Trace BFS in a fixed rhythm: dequeue the front vertex, record it, then enqueue each "
        "unvisited neighbor while immediately marking them visited. Watch the queue: vertices "
        "enter in level order and leave in level order. One full trace of a 6-vertex graph teaches "
        "more than re-reading the definition three times."
    ),
    "bfs_implementation": (
        "Plain BFS is four moving parts: visited set seeded with the start, a queue seeded with the "
        "start, a loop that pops until empty, and an inner loop over unvisited neighbors that marks "
        "and enqueues them. Learn this exact skeleton; every BFS application in V0 is a small "
        "decoration around it."
    ),
    "bfs_time_complexity": (
        "With an adjacency list: every vertex is enqueued/dequeued at most once (O(V)) and every "
        "edge is examined at most twice — once from each endpoint (O(E)). Total O(V+E). With an "
        "adjacency matrix, finding neighbors of each vertex costs O(V), so total O(V²)."
    ),
    "bfs_space_complexity": (
        "Memory goes to the visited set (O(V)) and the queue, which in the worst case holds a "
        "whole level at once — think of a vertex connected to all others — O(V). Total O(V)."
    ),
    "dfs_intuition": (
        "DFS explores like walking a maze with one hand on the wall: go as deep as possible along "
        "one route, and only when stuck, backtrack to the last branching point. It does not give "
        "shortest paths, but it cleanly answers reachability and structure questions (components, "
        "cycles) and is natural to write recursively."
    ),
    "recursion_mechanism": (
        "A recursive function calls itself on a smaller subproblem and needs a base case to stop. "
        "In DFS the 'smaller subproblem' is an unvisited neighbor, and the visited set guarantees "
        "progress — every call permanently marks its vertex, so calls cannot loop. The call stack "
        "remembers where to backtrack to."
    ),
    "dfs_visited_handling": (
        "Mark a vertex visited the moment you enter it (before exploring neighbors). Then recurse "
        "only into unvisited neighbors. Marking only after the loop returns would allow the same "
        "vertex to be pushed onto the call stack many times — on a cycle that means infinite "
        "recursion."
    ),
    "dfs_manual_tracing": (
        "Trace DFS by following one path to its dead end, then rewinding one level at a time. On "
        "paper: current call, visited set, output order. Notice how the order differs from BFS on "
        "the same graph — depth-first dives, breadth-first sweeps."
    ),
    "dfs_implementation": (
        "Plain recursive DFS: mark the current vertex visited, record it, then for each unvisited "
        "neighbor call dfs on it. That is the whole algorithm — the visited check before the call "
        "is what keeps it finite and O(V+E)."
    ),
    "dfs_time_complexity": (
        "Each vertex is visited once and each edge examined at most twice from an adjacency list: "
        "O(V+E). Same total as BFS — the exploration order differs, not the amount of work."
    ),
    "dfs_space_complexity": (
        "Beyond visited (O(V)), memory is dominated by recursion depth: the longest path being "
        "explored, up to O(V) — a straight-line graph forces depth V. Very deep graphs can hit "
        "Python's recursion limit, which is exactly why explicit-stack DFS exists."
    ),
    "explicit_stack_dfs": (
        "Replace recursion with your own stack: push the start; pop a vertex, skip it if visited, "
        "mark and record it, push its unvisited neighbors. Push neighbors in reverse order to "
        "match the recursive visit order. Same O(V+E), no recursion depth limit."
    ),
    "bfs_vs_dfs": (
        "Same skeleton, different frontier: queue → BFS → level order → shortest-by-edges in "
        "unweighted graphs; stack/recursion → DFS → deep order → structure and reachability, "
        "natural recursion. Both O(V+E) time and O(V) space with adjacency lists. Choose by what "
        "the question asks for: nearest/shortest → BFS; any-path/structure → DFS."
    ),
    "recognizing_traversal": (
        "Signals that plain traversal is the right tool: 'can X be reached from Y?', 'how many "
        "vertices are in X's component?', 'fewest steps from X to Y (unweighted) → BFS', 'is there "
        "any path / does a structure exist → DFS'. If the problem hands you entities and "
        "connections and asks what is reachable or how far, start from BFS/DFS."
    ),
    "traversal_application": (
        "A complete small application: model the situation as a graph (vertices = entities, edges "
        "= relationships), pick a representation, run BFS or DFS from the relevant start, and read "
        "the answer from the traversal (visited size = component size, order = exploration, first-"
        "reach = shortest steps for BFS)."
    ),
    "v0_readiness": (
        "The V0 exit check: independently (no hints) write plain BFS and plain DFS, trace both by "
        "hand, explain the visited state and why it prevents infinite loops, state O(V+E)/O(V) "
        "complexity, and recognize when traversal applies. Passing this means the Graph V0 outcome "
        "list is demonstrated — advanced graph algorithms are a later version."
    ),

    # --- Layer 1 theory ---
    "traversal_boundary": (
        "A single BFS or DFS started at one vertex explores exactly one connected component — the "
        "set of all vertices reachable from that start. The traversal stops when its frontier "
        "becomes empty, meaning there are no more undiscovered vertices adjacent to anything already "
        "visited. Crucially, this does NOT mean the traversal failed; it means it has finished its "
        "job: it found everything in that one component. The visited set now contains precisely that "
        "component. If the graph has other components, their vertices remain unvisited — and that is "
        "expected, not an error."
    ),
    "component_discovery": (
        "After a traversal finishes, any vertex not in the visited set belongs to a different "
        "connected component. Starting a new traversal from any such unvisited vertex will discover "
        "its entire component. This is the key insight: to explore the whole graph, you do not run "
        "one traversal from every vertex (which would be O(V(V+E))). Instead, you run one traversal "
        "per component by starting from an unvisited vertex, marking everything it reaches, and "
        "repeating until no unvisited vertices remain. Each new start discovers exactly one new "
        "component."
    ),
    "component_enumeration": (
        "The outer loop pattern — 'for each vertex, if not visited, start a traversal' — systematically "
        "enumerates all connected components. Each iteration of the loop that actually launches a "
        "traversal corresponds to one component. You can count components by incrementing a counter "
        "each time you start a new traversal. You can label components by assigning a component ID "
        "to every vertex visited during that traversal. Because every vertex and edge is processed "
        "at most a constant number of times across all traversals, the total time is O(V+E), not "
        "O(V(V+E)). The visited set guarantees no vertex is processed twice, even though multiple "
        "traversals run in sequence."
    ),

    # --- Layer 2 theory ---
    "bfs_distance": (
        "BFS levels are not just an ordering — they ARE distances. The source sits at distance 0, "
        "every immediate neighbor at distance 1, their unvisited neighbors at distance 2, and so on: "
        "each wave of the ripple is exactly one more edge. So instead of a separate visited set you "
        "can keep a distance array: distance[v] = -1 means 'not discovered yet' (which doubles as "
        "the visited check), the source gets 0, and every newly discovered neighbor gets "
        "distance[current] + 1. Why is the FIRST discovery the minimum? BFS dequeues vertices in "
        "nondecreasing distance order, so when a vertex is first discovered, it was reached from a "
        "vertex already at the minimum possible distance — no shorter route can appear later. This "
        "is why, in an unweighted graph, BFS finds the fewest-edges route. Two cautions: shortest "
        "means fewest EDGES (not fewest vertices, not smallest weight), and this guarantee holds "
        "only for unweighted graphs. Vertices that never get a distance keep -1: they are "
        "unreachable from the source — exactly the other-component situation from connected "
        "components, now recorded as a number instead of a missing visited entry."
    ),
    "path_reconstruction": (
        "A distance tells you HOW FAR a vertex is; it does not tell you HOW to get there. For the "
        "actual route, add one more piece of state during the same BFS: a parent array. Every time "
        "a vertex is first discovered, it remembers WHO discovered it: parent[neighbor] = current. "
        "Mentally: every vertex remembers who first brought it into the BFS tree. Parents form a "
        "tree rooted at the source, and following parents from any vertex walks backward along a "
        "shortest path. To reconstruct the route from source to target: start at target, collect "
        "vertices by following parent pointers until you reach the source, then REVERSE the "
        "collected sequence — you walked backward, so the path comes out backward. Edge cases: if "
        "source == target the path is just [source]; if the target was never discovered (parent "
        "stays -1 / distance stays -1) no path exists and you return an empty path. If several "
        "shortest paths exist, BFS returns ONE valid shortest path — the one its discovery order "
        "happened to build — not all of them. The whole routine is still one BFS: O(V+E) to fill "
        "distance and parent, plus at most O(V) to walk the path backward."
    ),

    # --- Layer 3 theory ---
    "cycle_encounter_reasoning": (
        "Run a DFS on an undirected graph and watch what the traversal actually sees. The edge "
        "A—B lives in the adjacency list TWICE — as A→B and as B→A — so when you walk A → B, the "
        "vertex B will scan its neighbor list, find A there, and observe: 'A is already visited.' "
        "Nothing went wrong: that is the same physical edge, seen from the other side. So the raw "
        "observation 'my neighbor is visited' is ambiguous. On a tree it happens at every single "
        "vertex — each one sees its parent — and on a graph with cycles it additionally happens at "
        "the vertex that closes the loop. Reading the observation therefore needs one more piece of "
        "information: WHERE the traversal came from. When the visited neighbor is the vertex you "
        "just came from, you are only re-reading the edge you arrived on. When it is anyone else, a "
        "second route has reached an already-visited vertex — the first hard evidence of a cycle. "
        "This skill is only about seeing the situation correctly; the detection decision comes next."
    ),
    "parent_aware_traversal": (
        "The parent of the current vertex is the vertex from which the traversal entered it. In "
        "recursive DFS it becomes one extra parameter: dfs(graph, v, parent), and each call passes "
        "itself as the child's parent; the start has no parent. With it, the encounter rule from "
        "the previous skill becomes precise: while exploring v's neighbors, meeting the parent is "
        "normal — it is the reverse direction of the arrival edge, present in every undirected "
        "adjacency list — while meeting any OTHER visited vertex is genuine cycle evidence. Two "
        "tracing notes: the parent check applies to the CURRENT call only — a vertex visited by an "
        "earlier branch of the DFS is not your parent even if it is adjacent, and THAT encounter is "
        "exactly the evidence you must not skip; and the parent edge is skipped once per endpoint, "
        "so no information is lost — every edge is still examined from both sides, which is why the "
        "O(V+E) bound survives. You already know parents from BFS path reconstruction "
        "(parent[neighbor] = discoverer); here the same idea moves into the DFS signature, where it "
        "answers 'which edge did I arrive on?' instead of 'how do I walk back?'"
    ),
    "undirected_cycle_detection": (
        "Put the pieces together and cycle detection is four small additions to the DFS you already "
        "write: mark v visited on entry; skip the neighbor equal to parent; if a neighbor is visited "
        "— and it is not the parent — return True; otherwise recurse, passing v as the new parent. A "
        "tree returns False even though every vertex sees its parent visited; one extra edge returns "
        "True at the vertex that closes the loop. One traversal covers one component only (the "
        "traversal boundary), so the outer loop — for each vertex, if not visited, run dfs(v, none) "
        "— is required: the graph has a cycle if ANY component does, and isolated vertices are "
        "simply component-less starts whose dfs immediately returns False. The same invariant "
        "translates directly to BFS: store (vertex, parent) pairs in the queue instead of bare "
        "vertices, mark neighbors visited when enqueueing, and apply the identical test — a visited "
        "non-parent neighbor proves a cycle. Self-loops need no special code: the vertex appears in "
        "its own neighbor list, it is visited (you marked it on entry), and it is not the parent — a "
        "cycle of length one, correctly detected. Everything stays O(V+E): each vertex is visited "
        "once and each edge is examined from both endpoints across the whole run."
    ),
}

# The shared demo graph used by several deterministic exercises.
G1 = {"A": ["B", "C"], "B": ["D"], "C": ["D", "E"], "D": ["F"], "E": ["F"], "F": []}
BFS_G1 = "A B C D E F"
DFS_G1 = "A B D F C E"

THEORY["adjacency"] = (
    "Two vertices are adjacent when an edge connects them directly — they are neighbors. "
    "Adjacency is the relationship traversal exploits: at every step the algorithm asks only "
    "'which vertices are adjacent to the current one?'. In an adjacency list, the neighbors of u "
    "are literally the entries of graph[u]."
)
THEORY["conversion_between_representations"] = (
    "The three representations hold identical information, so each can be rebuilt from the others: "
    "an edge list becomes an adjacency list by appending each endpoint to the other's list; an "
    "adjacency list becomes a matrix by marking [i][j] for every neighbor entry; a matrix becomes "
    "an edge list by scanning every cell. Being able to convert means you are never locked into "
    "the representation an input format hands you."
)

# ------------------------------------------------------------- exercises ----
UNITS: list[LearningUnit] = []
EXERCISES: list[Exercise] = []
_unit_n = 0
_ex_n = 0


def _unit(skill_id, title, goal, utype, theory=None, dims=frozenset()):
    global _unit_n
    _unit_n += 1
    uid = f"u{_unit_n:03d}_{skill_id}"
    UNITS.append(LearningUnit(id=uid, skill_id=skill_id, title=title, goal=goal,
                              unit_type=utype, ordering=_unit_n, theory=theory,
                              required_dimensions=frozenset(dims)))
    return uid


def _ex(unit_id, skill_id, itype, prompt, payload, difficulty, *, language=None,
        hints=None, max_hints=4, requires_ai=False, ordering=0):
    global _ex_n
    _ex_n += 1
    eid = f"e{_ex_n:03d}_{skill_id}"
    EXERCISES.append(Exercise(
        id=eid, unit_id=unit_id, skill_id=skill_id, interaction_type=itype, prompt=prompt,
        payload=payload, ordering=ordering, difficulty=difficulty, language=language,
        hint_ladder=hints or [], max_hints=max_hints, requires_ai=requires_ai, source="curated",
    ))
    return eid


def _mcq(prompt, choices, answer, explanation, difficulty):
    if not isinstance(difficulty, dict):
        difficulty = {"conceptual": difficulty[0], "implementation": difficulty[1],
                      "reasoning": difficulty[2], "transfer": difficulty[3]}
    return {"choices": [{"id": cid, "text": text} for cid, text in choices],
            "answer_id": answer, "explanation": explanation}, difficulty


def _h(kind, text):
    return {"kind": kind, "text": text}


def _dq(comp):
    return {"conceptual": comp[0], "implementation": comp[1], "reasoning": comp[2], "transfer": comp[3]}


def _build():
    d = _dq
    from .theory_notes import EXAMPLES, PITFALLS
    for s in SKILLS:  # every skill gets a teach unit: full study text + MCQ check
        uid = _unit(s.id, f"{s.title} — study", f"Understand {s.title.lower()}", UnitType.TEACH,
                    theory=(THEORY[s.id] + "\n\nExample: " + EXAMPLES[s.id]
                            + "\n\nWatch out: " + PITFALLS[s.id]), dims={K})
        mcqs = MCQ_BANK[s.id]
        _ex(uid, s.id, InteractionType.MCQ, mcqs["prompt"], *mcqs["data"], ordering=1)
    _build_practice()
    _build_variations()


MCQ_BANK = {}


def _mcq_bank(skill, prompt, choices, answer, explanation, difficulty):
    MCQ_BANK[skill] = {"prompt": prompt, "data": _mcq(prompt, choices, answer, explanation, difficulty)}


# --- MCQ per skill -------------------------------------------------------
_mcq_bank("graph_definition", "Which statement best describes a graph?",
          [("a", "A set of vertices connected by edges that represent relationships"),
           ("b", "A linear sequence of elements with one fixed order"),
           ("c", "A table of numbers with rows and columns only"),
           ("d", "A tree where every node has exactly one parent")], "a",
          "A graph is vertices plus edges capturing arbitrary relationships — no fixed order, not necessarily a tree.", (1, 1, 1, 1))
_mcq_bank("vertices_edges", "In a social network, people are friendships are edges. Which mapping is right?",
          [("a", "People are vertices; friendships are edges"),
           ("b", "People are edges; friendships are vertices"),
           ("c", "Both are vertices"),
           ("d", "Both are edges")], "a",
          "Entities are vertices; the relationships between them are edges.", (1, 1, 1, 1))
_mcq_bank("directed_vs_undirected", "A follows B on Twitter, but B need not follow A. Which graph models this?",
          [("a", "Undirected graph"), ("b", "Directed graph"),
           ("c", "Weighted graph"), ("d", "No graph can model this")], "b",
          "The relation is one-way, so each edge needs a direction: a directed graph.", (2, 1, 2, 2))
_mcq_bank("weighted_vs_unweighted", "A road map where each road has a length in km. What must the graph have?",
          [("a", "Directed edges"), ("b", "Weights on edges"),
           ("c", "Weights on vertices"), ("d", "Self loops")], "b",
          "A number attached per edge (distance) means an edge-weighted graph.", (1, 1, 1, 2))
_mcq_bank("degree", "A center vertex connects to 4 outer vertices; the outer ones connect to nothing else. Degree of the center?",
          [("a", "1"), ("b", "3"), ("c", "4"), ("d", "5")], "c",
          "Degree counts attached edges: the center has exactly 4.", (2, 2, 2, 2))
_mcq_bank("path", "Edges: A-B, B-C, C-D, A-E. Which is a valid path from A to D?",
          [("a", "A → B → C → D"), ("b", "A → D"), ("c", "A → C → D"), ("d", "A → B → D")], "a",
          "Each consecutive pair must be an edge; only A-B, B-C, C-D qualifies.", (2, 1, 2, 2))
_mcq_bank("cycle", "Edges: A-B, B-C, C-A. What does this graph contain?",
          [("a", "A cycle A → B → C → A"), ("b", "A path from A to nothing else"),
           ("c", "A self loop"), ("d", "Nothing special — it is a tree")], "a",
          "The route returns to its start without reusing edges: a cycle.", (2, 1, 2, 2))
_mcq_bank("connectedness", "A graph is connected when...",
          [("a", "Every vertex has at least one edge"),
           ("b", "A path exists between every pair of vertices"),
           ("c", "It has no cycles"),
           ("d", "It has an even number of edges")], "b",
          "Connected = one component: everything reaches everything.", (2, 1, 2, 2))
_mcq_bank("edge_list", "Edges are stored only as a list of pairs. Finding all neighbors of B costs...",
          [("a", "O(1) — check one slot"), ("b", "O(E) — scan the whole list"),
           ("c", "O(V²) always"), ("d", "It is impossible")], "b",
          "Nothing is indexed by vertex, so you must scan every edge.", (1, 2, 1, 1))
_mcq_bank("adjacency_matrix", "In an adjacency matrix, cell [i][j] = 1 means...",
          [("a", "Vertex i has degree j"),
           ("b", "There is an edge from vertex i to vertex j"),
           ("c", "Vertex i is visited j times"),
           ("d", "Row i is the adjacency list of j")], "b",
          "A matrix cell encodes presence of an edge between the two indexed vertices.", (2, 3, 2, 2))
_mcq_bank("adjacency_list", "Which representation stores a graph with V vertices and E sparse edges in about O(V+E) memory?",
          [("a", "Adjacency matrix"), ("b", "Adjacency list"),
           ("c", "Edge list sorted by row"), ("d", "A V×E table")], "b",
          "Adjacency lists allocate per vertex plus per edge: O(V+E).", (2, 3, 2, 2))
_mcq_bank("choosing_representation", "Dense graph, and you must answer 'is there an edge u→v?' in O(1). Best choice?",
          [("a", "Adjacency list"), ("b", "Edge list"), ("c", "Adjacency matrix"), ("d", "Any of them")], "c",
          "A matrix gives O(1) edge checks; density makes its O(V²) memory acceptable.", (3, 2, 3, 3))
_mcq_bank("why_traversal", "The core purpose of graph traversal is to...",
          [("a", "Sort vertices by name"),
           ("b", "Systematically visit every vertex reachable from a start vertex"),
           ("c", "Add new edges to the graph"),
           ("d", "Shrink the graph to a tree")], "b",
          "Traversal = systematic exploration of everything reachable from a start.", (2, 1, 2, 2))
_mcq_bank("traversal_state", "During traversal, the 'frontier' is...",
          [("a", "Vertices already fully processed"),
           ("b", "Vertices discovered but not yet processed"),
           ("c", "Vertices not yet discovered"),
           ("d", "The edges that were removed")], "b",
          "Frontier = discovered, waiting in the queue/stack to be processed.", (2, 2, 2, 2))
_mcq_bank("visited_state", "The visited set exists mainly to...",
          [("a", "Make the output sorted"),
           ("b", "Prevent re-processing vertices and infinite loops on cycles"),
           ("c", "Store edge weights"),
           ("d", "Count the graph's components")], "b",
          "Visited memory stops cycles from looping forever and bounds work to O(V+E).", (3, 3, 3, 3))
_mcq_bank("traversal_order", "With a stack (take newest first) the exploration goes...",
          [("a", "Level by level, like ripples"),
           ("b", "Deep along one route, then backtrack"),
           ("c", "Randomly"), ("d", "Alphabetically")], "b",
          "Stack = newest discovery first = depth-first behavior.", (2, 2, 2, 2))
_mcq_bank("manual_tracing", "When tracing a traversal by hand, you should always record...",
          [("a", "Only the final answer"),
           ("b", "Current vertex, the frontier, the visited set, and the output order"),
           ("c", "Only the visited set"),
           ("d", "The full source code of the algorithm")], "b",
          "All four state pieces make the trace faithful to what the code does.", (3, 3, 3, 2))
_mcq_bank("bfs_intuition", "BFS explores a graph...",
          [("a", "Like ripples: all distance-1 vertices, then distance-2, ..."),
           ("b", "Like a maze walk going as deep as possible first"),
           ("c", "In reverse topological order"),
           ("d", "By decreasing vertex degree")], "a",
          "BFS = breadth-first: expanding rings of increasing distance.", (3, 1, 3, 3))
_mcq_bank("queue_mechanism", "Why does BFS use a queue and not a stack?",
          [("a", "FIFO preserves discovery order, so closer vertices are processed first"),
           ("b", "Queues are faster than stacks in Python"),
           ("c", "A stack cannot store strings"),
           ("d", "Queues automatically sort vertices")], "a",
          "FIFO ordering is exactly what produces level-by-level exploration.", (3, 3, 3, 2))
_mcq_bank("bfs_visited_handling", "In BFS you should mark a neighbor visited...",
          [("a", "When it is dequeued"), ("b", "When it is enqueued"),
           ("c", "Only after the queue empties"), ("d", "Never — visited is optional")], "b",
          "Enqueue-time marking keeps each vertex in the queue at most once.", (3, 3, 3, 3))
_mcq_bank("bfs_manual_tracing", "graph: A→[B,C], B→[D], C→[D,E], D→[F], E→[F], F→[]; BFS from A. When D is dequeued, what is in the queue?",
          [("a", "E, F"), ("b", "D, E"), ("c", "B, C"), ("d", "F")], "a",
          "Dequeue order A,B,C,D; when D pops, E was already enqueued by C and F is enqueued at that moment: queue=[E,F] with E at the front.", (3, 3, 3, 3))
_mcq_bank("bfs_implementation", "In `deque`, using popleft() vs pop() changes BFS into...",
          [("a", "Nothing, they are identical"),
           ("b", "popleft keeps BFS level order; pop turns it into a DFS-like order"),
           ("c", "pop makes it faster"),
           ("d", "popleft only works on matrices")], "b",
          "popleft = FIFO = BFS; pop = LIFO = stack-like deep exploration.", (3, 4, 3, 3))
_mcq_bank("bfs_time_complexity", "BFS with an adjacency list, V vertices and E edges: total time?",
          [("a", "O(V²) always"), ("b", "O(V+E)"), ("c", "O(E log V)"), ("d", "O(V·E)")], "b",
          "Each vertex queued once and each edge scanned a bounded number of times.", (3, 1, 4, 3))
_mcq_bank("bfs_space_complexity", "BFS extra memory (visited + queue) in the worst case is...",
          [("a", "O(V)"), ("b", "O(E)"), ("c", "O(V²)"), ("d", "O(log V)")], "a",
          "Visited holds every vertex; the queue can hold one whole level ≤ V.", (3, 1, 4, 3))
_mcq_bank("dfs_intuition", "DFS explores a graph...",
          [("a", "Level by level"), ("b", "As deep as possible along one route, then backtracks"),
           ("c", "By edge weight order"), ("d", "Only the start vertex")], "b",
          "DFS dives deep and backtracks when stuck.", (3, 1, 3, 3))
_mcq_bank("recursion_mechanism", "What guarantees that recursive DFS eventually stops?",
          [("a", "Python limits all recursion to 10 calls"),
           ("b", "Each call visits a new unvisited vertex, and vertices run out"),
           ("c", "The queue empties"),
           ("d", "The base case sorts the graph")], "b",
          "Visited-marking makes every call make progress; finitely many vertices.", (3, 3, 4, 2))
_mcq_bank("dfs_visited_handling", "In recursive DFS, the correct place to mark a vertex visited is...",
          [("a", "Right when entering the vertex, before exploring neighbors"),
           ("b", "After all neighbors return"),
           ("c", "Inside the base case only"),
           ("d", "Nowhere — DFS needs no visited set")], "a",
          "Entry-time marking prevents the same vertex entering the call stack twice.", (3, 3, 3, 3))
_mcq_bank("dfs_manual_tracing", "graph: A→[B,C], B→[D], C→[D,E], D→[F], E→[F], F→[]; recursive DFS from A visits neighbors in listed order. Which vertex is visited immediately after B?",
          [("a", "C"), ("b", "D"), ("c", "E"), ("d", "F")], "b",
          "DFS dives into B's first neighbor D before ever looking at C.", (3, 3, 3, 3))
_mcq_bank("dfs_implementation", "Recursive DFS without a visited set on a graph with a cycle will...",
          [("a", "Return the correct order anyway"),
           ("b", "Recurse forever (RecursionError)"),
           ("c", "Skip the cycle automatically"),
           ("d", "Sort the vertices")], "b",
          "Cycles re-enter the same vertices; without memory the calls never stop.", (3, 4, 3, 3))
_mcq_bank("dfs_time_complexity", "Recursive DFS with adjacency list, V vertices, E edges: total time?",
          [("a", "O(V+E)"), ("b", "O(V²) always"), ("c", "O(E²)"), ("d", "O(V log E)")], "a",
          "Same accounting as BFS: each vertex once, each edge scanned boundedly.", (3, 1, 4, 3))
_mcq_bank("dfs_space_complexity", "The dominant extra memory of recursive DFS (beyond visited) is...",
          [("a", "The queue of all vertices"),
           ("b", "The recursion call stack, up to O(V) deep"),
           ("c", "The adjacency matrix"),
           ("d", "A copy of all edges")], "b",
          "Recursion depth follows the deepest path — O(V) worst case.", (3, 1, 4, 3))
_mcq_bank("explicit_stack_dfs", "Why does explicit-stack DFS exist alongside recursive DFS?",
          [("a", "It is asymptotically faster"),
           ("b", "Same traversal without recursion depth limits"),
           ("c", "It uses a queue internally"),
           ("d", "It finds shortest paths")], "b",
          "Your own stack removes the recursion-limit risk; complexity is unchanged.", (4, 4, 4, 3))
_mcq_bank("bfs_vs_dfs", "Unweighted graph, need the route with the fewest edges from S to T. Which and why?",
          [("a", "DFS — it goes deep, so it finds long paths"),
           ("b", "BFS — the first time it reaches T is via fewest edges"),
           ("c", "Either — both always give shortest routes"),
           ("d", "Neither — traversal cannot answer this")], "b",
          "BFS expands by increasing distance; first reach = fewest edges.", (4, 2, 4, 4))
_mcq_bank("recognizing_traversal", "'How many people can be reached from Alice in this network?' This is fundamentally...",
          [("a", "A sorting problem"), ("b", "A traversal problem: explore from Alice, count visited"),
           ("c", "A shortest-weighted-path problem"), ("d", "Not solvable with traversal")], "b",
          "Reach-and-count = run any traversal from Alice, count the visited set.", (4, 1, 4, 4))
_mcq_bank("traversal_application", "The right order of steps when applying traversal to a new situation is...",
          [("a", "Code first, then guess the graph later"),
           ("b", "Model entities/edges → choose representation → run BFS/DFS → read the answer from the traversal"),
           ("c", "Memorize a solution template and paste it"),
           ("d", "Sort the input, then traverse")], "b",
          "Model → represent → traverse → interpret; that is the transferable pattern.", (4, 4, 4, 5))
_mcq_bank("v0_readiness", "You are ready to finish Graph V0 when you can...",
          [("a", "Recite BFS code from memory with the screen off"),
           ("b", "Independently write plain BFS & DFS, trace them, explain visited and complexity"),
           ("c", "Solve Dijkstra and topological sort"),
           ("d", "Name all graph algorithms")], "b",
          "Independent correctness + reasoning about state and complexity = the V0 outcome.", (4, 4, 4, 4))

# Layer 1 MCQ banks
_mcq_bank("traversal_boundary", "A single BFS from vertex A in a disconnected graph visits exactly...",
          [("a", "The whole graph"),
           ("b", "The connected component containing A"),
           ("c", "Only the neighbors of A"),
           ("d", "A single path from A")], "b",
          "One traversal = one component. BFS from A visits exactly the vertices reachable from A.", (3, 2, 3, 3))
_mcq_bank("component_discovery", "After BFS from A finishes, vertex D is unvisited. What should you do?",
          [("a", "Report an error — BFS should visit everything"),
           ("b", "Start a new BFS from D to discover its component"),
           ("c", "Restart BFS from A with a larger queue"),
           ("d", "Add an edge from A to D manually")], "b",
          "Unvisited after traversal = different component. Start a new traversal from the unvisited vertex.", (3, 3, 3, 3))
_mcq_bank("component_enumeration", "The outer loop `for v in range(n): if not visited[v]: bfs(v)` counts components. Why is total time O(V+E)?",
          [("a", "The loop only runs V times"),
           ("b", "The visited set prevents any vertex from being processed twice across all BFS runs"),
           ("c", "BFS is O(1) per vertex"),
           ("d", "It is actually O(V(V+E))")], "b",
          "Each vertex enters the queue at most once total; each edge is examined at most twice total.", (3, 4, 4, 4))

# Layer 2 MCQ banks
_mcq_bank("bfs_distance", "In BFS from A on an unweighted graph, vertex X is discovered while C is "
          "being processed and distance[C] = 2. What is distance[X]?",
          [("a", "1"), ("b", "2"), ("c", "3"), ("d", "It cannot be determined")], "c",
          "A newly discovered neighbor gets distance[current] + 1 = 3; BFS discovers in nondecreasing distance order, so this first value is already minimal.", (3, 3, 4, 3))
_mcq_bank("path_reconstruction", "parent = {B: A, C: A, D: B, E: C, F: D}, parent[A] = -1. Following parents "
          "back from F and reversing, what is the path A→F?",
          [("a", "A B D F"), ("b", "F D B A"), ("c", "A C E F"), ("d", "A B C D F")], "a",
          "Walking parents from F gives F, D, B, A; reversing yields A B D F — the discovery tree's route.", (3, 4, 4, 4))

# Layer 3 MCQ banks
_mcq_bank("cycle_encounter_reasoning", "An undirected graph is stored with every edge in BOTH endpoint "
          "adjacency lists. During a DFS, vertex C scans its neighbors and finds B already visited. "
          "By itself, what does this observation prove?",
          [("a", "A cycle exists"),
           ("b", "Nothing yet — B could simply be C's parent: the reverse direction of the edge the traversal arrived on"),
           ("c", "The visited set is being maintained incorrectly"),
           ("d", "The adjacency list was built wrongly")], "b",
          "On ANY undirected graph — even a tree — every non-start vertex sees its parent as visited, because the arrival edge is stored both ways. Only a visited NON-parent is cycle evidence.", (3, 2, 3, 3))
_mcq_bank("parent_aware_traversal", "DFS is at vertex D, having entered from A — so A is D's parent. "
          "D's neighbor list contains A (visited), B (unvisited) and C (visited). Which observation "
          "is cycle evidence?",
          [("a", "A is visited"),
           ("b", "B is unvisited"),
           ("c", "C is visited and C is not D's parent"),
           ("d", "All three observations together prove a cycle")], "c",
          "The visited parent is the arrival edge seen from the other side — normal. A visited neighbor other than the parent means a second route reached it earlier: cycle evidence.", (3, 3, 4, 3))
_mcq_bank("undirected_cycle_detection", "DFS-with-parent started at vertex 0, explored component "
          "{0, 1} and returned False. Vertices 2, 3, 4 and 5 were never visited. What is the "
          "correct graph-level conclusion?",
          [("a", "The whole graph is acyclic"),
           ("b", "Nothing yet — each remaining component needs its own traversal via the outer loop before the answer exists"),
           ("c", "DFS cannot answer cycle questions, restart with BFS"),
           ("d", "Clear the visited set and run the same DFS again from 0")], "b",
          "One traversal = one component. 'No cycle in this component' must be established for every component: run dfs from each unvisited vertex and report a cycle if any run finds one.", (3, 3, 4, 4))

_mcq_bank("adjacency", "Two vertices are adjacent when...",
          [("a", "An edge connects them directly"),
           ("b", "They have the same degree"),
           ("c", "A path exists between them"),
           ("d", "They are both in the same component")], "a",
          "Adjacency = directly connected by an edge; paths and components are reachability, not adjacency.", (1, 1, 1, 1))
_mcq_bank("conversion_between_representations", "You have an adjacency list and need fast O(1) edge lookups. What do you build?",
          [("a", "An edge list"), ("b", "An adjacency matrix"),
           ("c", "A longer adjacency list"), ("d", "Nothing — lists cannot convert")], "b",
          "Converting list → matrix marks [i][j] for each neighbor entry, buying O(1) lookups at O(V²) memory.", (3, 3, 3, 2))

# --- practice units & richer exercises -----------------------------------
def _build_practice():
    d = _dq
    # degree — construct a graph
    uid = _unit("degree", "Degree — practice", "Build a graph from degree constraints", UnitType.PRACTICE, dims={E})
    _ex(uid, "degree", InteractionType.GRAPH_CONSTRUCTION,
        "Build an undirected graph: vertex A must have degree 3; B, C, D must each have degree 1; E must be isolated (degree 0).\n"
        "Enter edges as pairs like 'A-B' separated by commas.",
        {"nodes": ["A", "B", "C", "D", "E"],
         "expected_edges": [["A", "B"], ["A", "C"], ["A", "D"]]},
        d((2, 2, 2, 2)), ordering=1,
        hints=[_h("socratic_question", "If A has degree 3, how many edges touch A — and to which vertices could they go?"),
               _h("micro_question", "B must have degree 1. Which single edge could give B its degree while also helping A?"),
               _h("light_hint", "Connect A to each of B, C, D with one edge each."),
               _h("targeted_explanation", "The three edges A-B, A-C, A-D give A degree 3 and each of B, C, D degree 1; E gets no edge, so its degree stays 0.")])

    # adjacency_matrix — predict output
    uid = _unit("adjacency_matrix", "Adjacency matrix — practice", "Read neighbor rows from a matrix", UnitType.PRACTICE, dims={E})
    _ex(uid, "adjacency_matrix", InteractionType.OUTPUT_PREDICTION,
        "What exactly does this code print?\n\n"
        'nodes = ["A", "B", "C"]\nindex = {"A": 0, "B": 1, "C": 2}\n'
        "matrix = [[0]*3 for _ in range(3)]\n"
        'edges = [("A","B"), ("B","C")]\n'
        "for u, v in edges:\n    matrix[index[u]][index[v]] = 1\n    matrix[index[v]][index[u]] = 1\n"
        'for j in range(3):\n    if matrix[index["B"]][j] == 1:\n        print(nodes[j])',
        {"code": "", "expected_output": "A C"},
        d((2, 3, 2, 2)), ordering=1,
        hints=[_h("socratic_question", "Which row of the matrix corresponds to vertex B?"),
               _h("micro_question", "After filling both directions for edges A-B and B-C, what are the values in B's row?"),
               _h("light_hint", "B's row has 1s at the columns of its two neighbors."),
               _h("targeted_explanation", "Edge A-B sets row B col A to 1, edge B-C sets row B col C to 1, so the loop prints A then C.")])

    # adjacency_list — trace building it
    uid = _unit("adjacency_list", "Adjacency list — practice", "Trace adjacency-list construction", UnitType.PRACTICE, dims={E})
    _ex(uid, "adjacency_list", InteractionType.CODE_TRACING,
        "What does this code print?\n\n"
        'edges = [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")]\ngraph = {}\n'
        "for u, v in edges:\n    graph.setdefault(u, []).append(v)\n    graph.setdefault(v, []).append(u)\n"
        'print(graph["A"])\nprint(graph["D"])',
        {"code": "", "expected_output": "['B', 'C']\n['B', 'C']"},
        d((2, 3, 2, 2)), ordering=1,
        hints=[_h("socratic_question", "setdefault(v, []).append(...) — what does the list for each vertex accumulate?"),
               _h("micro_question", "Which edges touch A? Which touch D?"),
               _h("light_hint", "Every edge appends each endpoint to the other's list."),
               _h("targeted_explanation", "A touches B and C → ['B', 'C']; D is touched by edges B-D and C-D → ['B', 'C'].")])

    # choosing_representation — free-form reasoning
    uid = _unit("choosing_representation", "Choosing representation — practice", "Justify a representation choice", UnitType.PRACTICE, dims={R, T})
    _ex(uid, "choosing_representation", InteractionType.FREE_FORM,
        "You must store a road network: 1,000,000 intersections, each with about 3 roads. "
        "Which representation do you choose and why? Two or three sentences.",
        {"reference_points": [
            {"id": "p1", "keywords": ["adjacency list", "adjacency-list", "list of neighbors", "neighbour list"],
             "text": "Chooses the adjacency list."},
            {"id": "p2", "keywords": ["sparse", "3", "few edges", "memory", "o(v+e)", "o(v + e)"],
             "text": "Reasons with sparsity/memory: list costs O(V+E)."},
            {"id": "p3", "keywords": ["matrix", "o(v^2)", "o(v²)", "o(v2)", "1000000", "10^12", "wasteful"],
             "text": "Contrasts with the matrix's O(V^2) waste."},
         ], "min_points": 2},
        d((3, 2, 3, 3)), requires_ai=True, ordering=1,
        hints=[_h("socratic_question", "Roughly how many edges does this network have, and how many cells would a matrix need?"),
               _h("micro_question", "Is the graph dense or sparse? What does that mean for memory?"),
               _h("light_hint", "Compare O(V+E) against O(V^2) for V = 1,000,000."),
               _h("targeted_explanation", "Sparse (≈3M edges): adjacency list uses O(V+E); a matrix would need 10^12 cells — almost all zero.")])

    # visited_state — free-form mechanism explanation
    uid = _unit("visited_state", "Visited state — practice", "Explain the mechanism that stops infinite loops", UnitType.PRACTICE, dims={R, K})
    _ex(uid, "visited_state", InteractionType.FREE_FORM,
        "Graph edges: A-B, B-C, C-A. A traversal without a visited set starting at A loops forever. "
        "Explain in your own words the exact mechanism that causes the loop, and what the visited set changes.",
        {"reference_points": [
            {"id": "p1", "keywords": ["revisit", "re-visit", "again", "re-process", "re-enter", "same vertex"],
             "text": "Says the walk keeps re-entering vertices it already saw."},
            {"id": "p2", "keywords": ["no memory", "does not remember", "forgets", "no record", "unbounded"],
             "text": "Identifies missing memory of past visits."},
            {"id": "p3", "keywords": ["visited", "mark", "record", "set"],
             "text": "Says the visited set marks vertices so they are not re-entered."},
         ], "min_points": 2},
        d((3, 3, 3, 3)), requires_ai=True, ordering=1,
        hints=[_h("socratic_question", "After the walk goes A → B → C, which vertex does it reach next — and has it been there before?"),
               _h("micro_question", "Does the algorithm have any memory that A was already processed?"),
               _h("light_hint", "A cycle plus no memory = the same steps repeat forever."),
               _h("targeted_explanation", "C connects back to A, so the walk re-enters A forever; a visited set records A (and others) as done, so the edge C-A is never followed again.")])

    # traversal_order — stack explore trace
    uid = _unit("traversal_order", "Traversal order — practice", "Predict a stack-based exploration order", UnitType.PRACTICE, dims={E})
    _ex(uid, "traversal_order", InteractionType.OUTPUT_PREDICTION,
        "What does this code print?\n\n"
        'graph = {"A": ["B", "C"], "B": ["D"], "C": ["D", "E"], "D": [], "E": []}\n'
        "visited = set()\nstack = [\"A\"]\norder = []\n"
        "while stack:\n    node = stack.pop()\n    if node in visited:\n        continue\n"
        "    visited.add(node)\n    order.append(node)\n"
        "    for nxt in reversed(graph[node]):\n        if nxt not in visited:\n            stack.append(nxt)\n"
        'print(" ".join(order))',
        {"code": "", "expected_output": "A B D C E"},
        d((2, 2, 2, 2)), ordering=1,
        hints=[_h("socratic_question", "pop() takes from the end: after A, which vertex is processed first?"),
               _h("micro_question", "Why is the loop over reversed(graph[node]) — what does reversing change?"),
               _h("light_hint", "Track the stack contents after every step."),
               _h("targeted_explanation", "Stack makes it deep-first: A, then B, then D; back at C, its neighbor E pops last → A B D C E.")])

    # manual_tracing — free-form trace
    uid = _unit("manual_tracing", "Manual tracing — practice", "Trace state evolution by hand", UnitType.PRACTICE, dims={E, R})
    _ex(uid, "manual_tracing", InteractionType.FREE_FORM,
        "Graph: A→[B,C], B→[], C→[]. BFS from A. Describe the trace: after each step, the queue contents, "
        "the visited set, and the output so far.",
        {"reference_points": [
            {"id": "p1", "keywords": ["queue", "frontier", "pending"],
             "text": "Tracks the queue/frontier across steps."},
            {"id": "p2", "keywords": ["visited", "marked", "seen"],
             "text": "Tracks the visited set across steps."},
            {"id": "p3", "keywords": ["a b c", "a, b, c", "order"],
             "text": "Gives the correct output order A B C."},
         ], "min_points": 2},
        d((3, 3, 3, 2)), requires_ai=True, ordering=1,
        hints=[_h("socratic_question", "Start: queue=[A], visited={A}. What happens on the first dequeue?"),
               _h("micro_question", "After dequeuing A, which vertices enter the queue, in what order?"),
               _h("light_hint", "Then B leaves the queue (nothing to add), then C."),
               _h("targeted_explanation", "queue [A]→[B,C]→[C]→[]; visited {A}→{A,B}→{A,B,C}; output A, then B, then C.")])

    # queue_mechanism — FIFO mechanics
    uid = _unit("queue_mechanism", "Queue mechanics — practice", "Predict FIFO behavior", UnitType.PRACTICE, dims={E})
    _ex(uid, "queue_mechanism", InteractionType.OUTPUT_PREDICTION,
        "What does this print?\n\n"
        "from collections import deque\nq = deque()\nq.append(\"x\")\nq.append(\"y\")\n"
        "first = q.popleft()\nq.append(\"z\")\nsecond = q.popleft()\nthird = q.popleft()\n"
        'print(first, second, third)',
        {"code": "", "expected_output": "x y z"},
        d((3, 3, 3, 2)), ordering=1,
        hints=[_h("socratic_question", "popleft takes the oldest element: which entered first?"),
               _h("micro_question", "After removing x, what is at the front when z is appended?"),
               _h("light_hint", "FIFO = exactly the insertion order: x, then y, then z."),
               _h("targeted_explanation", "Queue holds x,y → pop x; holds y,z → pop y; holds z → pop z: prints x y z.")])

    # bfs_visited_handling — enqueue-time marking trace
    uid = _unit("bfs_visited_handling", "BFS visited — practice", "See enqueue-time marking in action", UnitType.PRACTICE, dims={E, R})
    _ex(uid, "bfs_visited_handling", InteractionType.CODE_TRACING,
        "This BFS marks visited at enqueue time. What does it print?\n\n"
        'graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}\n'
        'visited = {"A"}\nqueue = deque(["A"])\norder = []\n'
        "while queue:\n    node = queue.popleft()\n    order.append(node)\n"
        "    for nxt in graph[node]:\n        if nxt not in visited:\n            visited.add(nxt)\n            queue.append(nxt)\n"
        'print(" ".join(order))',
        {"code": "", "expected_output": "A B C D"},
        d((3, 3, 3, 3)), ordering=1,
        hints=[_h("socratic_question", "D is reachable from both B and C. How many times can D enter the queue here?"),
               _h("micro_question", "When B is processed and enqueues D, what does `visited.add` prevent later?"),
               _h("light_hint", "Because D was marked when enqueued from B, C skips it."),
               _h("targeted_explanation", "A enqueues B,C; B enqueues D (marked); C finds D already visited → order A B C D, D entered the queue exactly once.")])

    # bfs_manual_tracing — classic trace
    uid = _unit("bfs_manual_tracing", "BFS tracing — practice", "Trace BFS on the demo graph", UnitType.PRACTICE, dims={E, R})
    _ex(uid, "bfs_manual_tracing", InteractionType.OUTPUT_PREDICTION,
        "graph = {\"A\": [\"B\", \"C\"], \"B\": [\"D\"], \"C\": [\"D\", \"E\"], \"D\": [\"F\"], \"E\": [\"F\"], \"F\": []}\n"
        "Standard BFS from A (queue, mark-on-enqueue, neighbors in listed order). What visit order is printed?",
        {"code": "", "expected_output": BFS_G1},
        d((3, 3, 3, 3)), ordering=1,
        hints=[_h("socratic_question", "Level 1 from A is B, C. What is level 2?"),
               _h("micro_question", "After the queue holds D (from B) and then E (from C), which leaves first?"),
               _h("light_hint", "FIFO order: D before E; F is reached from D first."),
               _h("targeted_explanation", "Levels: A | B, C | D, E | F → A B C D E F.")])

    # bfs_implementation — write BFS
    uid = _unit("bfs_implementation", "BFS implementation — practice", "Write plain BFS independently", UnitType.PRACTICE, dims={E, K})
    _ex(uid, "bfs_implementation", InteractionType.CODE_WRITING,
        "Write the function `bfs(graph, start)` that returns the BFS visit order as a list, starting from `start`. "
        "graph is an adjacency-list dict; neighbors are listed in visiting order. Use a queue and a visited set.",
        {"function_name": "bfs",
         "starter": "from collections import deque\n\ndef bfs(graph, start):\n    # your code here\n",
         "tests": [{"graph": G1, "start": "A", "expected": ["A", "B", "C", "D", "E", "F"]},
                   {"graph": {"A": ["B"], "B": []}, "start": "A", "expected": ["A", "B"]},
                   {"graph": {"A": []}, "start": "A", "expected": ["A"]},
                   {"graph": {"A": ["B", "C"], "B": [], "C": []}, "start": "A", "expected": ["A", "B", "C"]}],
         "solution": ("from collections import deque\n\n"
                      "def bfs(graph, start):\n"
                      "    visited = {start}\n    queue = deque([start])\n    order = []\n"
                      "    while queue:\n        node = queue.popleft()\n        order.append(node)\n"
                      "        for neighbor in graph[node]:\n"
                      "            if neighbor not in visited:\n"
                      "                visited.add(neighbor)\n                queue.append(neighbor)\n"
                      "    return order\n")},
        d((3, 4, 3, 3)), language="python", ordering=1,
        hints=[_h("socratic_question", "Before the loop starts, what must the visited set and the queue already contain?"),
               _h("micro_question", "Inside the loop: what do you take out of the queue, and what do you do with it first?"),
               _h("light_hint", "For each neighbor: check visited → mark → enqueue. Order of those two operations matters."),
               _h("targeted_explanation", "Skeleton: visited={start}; queue=deque([start]); while queue: node=popleft, append to order, then enqueue unvisited neighbors marking them immediately. Return order.")])

    # bfs_time_complexity
    uid = _unit("bfs_time_complexity", "BFS time — practice", "Justify O(V+E) from the algorithm's anatomy", UnitType.PRACTICE, dims={R})
    _ex(uid, "bfs_time_complexity", InteractionType.COMPLEXITY_QUESTION,
        "BFS runs on an adjacency-list graph with V vertices and E edges. What is its total worst-case time "
        "complexity? Answer with big-O, e.g. 'O(V*E)'.",
        {"acceptable": ["o(v+e)", "o(e+v)", "o(v+e)", "o(n+m)", "o(v + e)"], "kind": "sum"},
        d((3, 1, 4, 3)), ordering=1,
        hints=[_h("socratic_question", "How many times can one vertex be enqueued, given enqueue-time marking?"),
               _h("micro_question", "Across the whole run, how often is each edge examined?"),
               _h("light_hint", "Add the vertex work and the edge work."),
               _h("targeted_explanation", "Each vertex dequeued once → O(V); each edge inspected at most twice → O(E); total O(V+E).")])

    # bfs_space_complexity
    uid = _unit("bfs_space_complexity", "BFS space — practice", "Account for BFS memory", UnitType.PRACTICE, dims={R})
    _ex(uid, "bfs_space_complexity", InteractionType.COMPLEXITY_QUESTION,
        "What is the worst-case extra space of BFS (visited set + queue), in big-O? Answer like 'O(E)'.",
        {"acceptable": ["o(v)", "o(n)"], "kind": "space"},
        d((3, 1, 4, 3)), ordering=1,
        hints=[_h("socratic_question", "What does the visited set hold at the end of a run?"),
               _h("micro_question", "Can the queue hold more than all vertices at once?"),
               _h("light_hint", "Both structures only ever contain vertices."),
               _h("targeted_explanation", "Visited ≤ V vertices; the queue holds at most one level ≤ V → O(V).")])

    # recursion_mechanism
    uid = _unit("recursion_mechanism", "Recursion — practice", "Predict recursive call flow", UnitType.PRACTICE, dims={E})
    _ex(uid, "recursion_mechanism", InteractionType.OUTPUT_PREDICTION,
        "What does this print?\n\n"
        "def countdown(n):\n    if n == 0:\n        return\n    print(n)\n    countdown(n - 1)\n\ncountdown(3)",
        {"code": "", "expected_output": "3 2 1"},
        d((3, 3, 4, 2)), ordering=1,
        hints=[_h("socratic_question", "countdown(3) prints first — which call happens before 2 appears?"),
               _h("micro_question", "What is the base case here, and when is it reached?"),
               _h("light_hint", "Each call prints its own n before delegating to n-1."),
               _h("targeted_explanation", "Calls run 3 → 2 → 1, each printing before recursing; countdown(0) hits the base case and stops.")])

    # dfs_visited_handling — entry-time marking trace
    uid = _unit("dfs_visited_handling", "DFS visited — practice", "Trace entry-time marking", UnitType.PRACTICE, dims={E, R})
    _ex(uid, "dfs_visited_handling", InteractionType.CODE_TRACING,
        "What does this print?\n\n"
        'graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}\n'
        "visited = set()\norder = []\n"
        "def dfs(node):\n    visited.add(node)\n    order.append(node)\n"
        "    for nxt in graph[node]:\n        if nxt not in visited:\n            dfs(nxt)\n"
        'dfs("A")\nprint(" ".join(order))',
        {"code": "", "expected_output": "A B D C"},
        d((3, 3, 3, 3)), ordering=1,
        hints=[_h("socratic_question", "After entering B, where does DFS go before it ever considers C?"),
               _h("micro_question", "When the call on D returns, which vertex is processed next in A's loop?"),
               _h("light_hint", "D was already visited from B, so C's call skips it."),
               _h("targeted_explanation", "A → B → D (dead end), backtrack to A's loop → C; C's neighbor D already visited → order A B D C.")])

    # dfs_manual_tracing
    uid = _unit("dfs_manual_tracing", "DFS tracing — practice", "Trace recursive DFS on the demo graph", UnitType.PRACTICE, dims={E, R})
    _ex(uid, "dfs_manual_tracing", InteractionType.OUTPUT_PREDICTION,
        "graph = {\"A\": [\"B\", \"C\"], \"B\": [\"D\"], \"C\": [\"D\", \"E\"], \"D\": [\"F\"], \"E\": [\"F\"], \"F\": []}\n"
        "Recursive DFS from A, neighbors in listed order, mark-on-entry. What visit order results?",
        {"code": "", "expected_output": DFS_G1},
        d((3, 3, 3, 3)), ordering=1,
        hints=[_h("socratic_question", "From A, DFS enters B first. Where does it go from B?"),
               _h("micro_question", "After F is a dead end, which call backtracks, and what is tried next?"),
               _h("light_hint", "Path A-B-D-F exhausts, then A's next neighbor C, then E."),
               _h("targeted_explanation", "Dive A→B→D→F, backtrack, then A→C→E → A B D F C E.")])

    # dfs_implementation — write DFS
    uid = _unit("dfs_implementation", "DFS implementation — practice", "Write plain recursive DFS independently", UnitType.PRACTICE, dims={E, K})
    _ex(uid, "dfs_implementation", InteractionType.CODE_WRITING,
        "Write the function `dfs(graph, start, visited=None)` returning the DFS visit order as a list. "
        "Recursive, mark-on-entry, neighbors in listed order.",
        {"function_name": "dfs",
         "starter": "def dfs(graph, start, visited=None):\n    # your code here\n",
         "tests": [{"graph": G1, "start": "A", "expected": ["A", "B", "D", "F", "C", "E"]},
                   {"graph": {"A": ["B"], "B": []}, "start": "A", "expected": ["A", "B"]},
                   {"graph": {"A": []}, "start": "A", "expected": ["A"]},
                   {"graph": {"A": ["B", "C"], "B": [], "C": []}, "start": "A", "expected": ["A", "B", "C"]}],
         "solution": ("def dfs(graph, start, visited=None):\n"
                      "    if visited is None:\n        visited = set()\n"
                      "    visited.add(start)\n    order = [start]\n"
                      "    for neighbor in graph[start]:\n"
                      "        if neighbor not in visited:\n"
                      "            order.extend(dfs(graph, neighbor, visited))\n"
                      "    return order\n")},
        d((3, 4, 3, 3)), language="python", ordering=1,
        hints=[_h("socratic_question", "What are the very first two things the function must do with `start`?"),
               _h("micro_question", "For each neighbor, what check decides whether to recurse?"),
               _h("light_hint", "Pass the same visited set down through every recursive call."),
               _h("targeted_explanation", "visited=None → set(); add(start); order=[start]; for each unvisited neighbor extend with the recursive call; return order.")])

    # dfs_time_complexity
    uid = _unit("dfs_time_complexity", "DFS time — practice", "Account for DFS time", UnitType.PRACTICE, dims={R})
    _ex(uid, "dfs_time_complexity", InteractionType.COMPLEXITY_QUESTION,
        "Recursive DFS with an adjacency list, V vertices, E edges: total worst-case time in big-O?",
        {"acceptable": ["o(v+e)", "o(e+v)", "o(n+m)", "o(v + e)"], "kind": "sum"},
        d((3, 1, 4, 3)), ordering=1,
        hints=[_h("socratic_question", "How many times does any vertex enter the recursion, given visited marking?"),
               _h("micro_question", "How many times can one edge be looked at across the entire run?"),
               _h("light_hint", "Same two buckets as BFS: vertex work + edge work."),
               _h("targeted_explanation", "Each vertex visited once → O(V); each edge examined ≤ twice → O(E); total O(V+E).")])

    # dfs_space_complexity
    uid = _unit("dfs_space_complexity", "DFS space — practice", "Account for recursion depth", UnitType.PRACTICE, dims={R})
    _ex(uid, "dfs_space_complexity", InteractionType.COMPLEXITY_QUESTION,
        "Beyond the visited set, what is the worst-case extra space of recursive DFS in big-O? Think of a long path graph.",
        {"acceptable": ["o(v)", "o(n)"], "kind": "space"},
        d((3, 1, 4, 3)), ordering=1,
        hints=[_h("socratic_question", "On a straight path A→B→C→…→Z, how many calls are alive at the deepest moment?"),
               _h("micro_question", "What structure holds those pending calls?"),
               _h("light_hint", "Depth of recursion = length of the deepest path."),
               _h("targeted_explanation", "The call stack holds one frame per pending vertex: up to O(V) on a path graph.")])

    # explicit_stack_dfs — stack DFS trace
    uid = _unit("explicit_stack_dfs", "Explicit-stack DFS — practice", "Trace stack-based DFS", UnitType.PRACTICE, dims={E})
    _ex(uid, "explicit_stack_dfs", InteractionType.CODE_TRACING,
        "What does this print?\n\n"
        'graph = {"A": ["B", "C"], "B": ["D"], "C": ["D", "E"], "D": ["F"], "E": ["F"], "F": []}\n'
        "visited = set()\nstack = [\"A\"]\norder = []\n"
        "while stack:\n    node = stack.pop()\n    if node in visited:\n        continue\n"
        "    visited.add(node)\n    order.append(node)\n"
        "    for nxt in reversed(graph[node]):\n        if nxt not in visited:\n            stack.append(nxt)\n"
        'print(" ".join(order))',
        {"code": "", "expected_output": DFS_G1},
        d((4, 4, 4, 3)), ordering=1,
        hints=[_h("socratic_question", "Pushing reversed neighbors — which neighbor sits on top right after A?"),
               _h("micro_question", "Duplicates can sit in the stack. Which line makes them harmless?"),
               _h("light_hint", "The `if node in visited: continue` guard discards stale entries."),
               _h("targeted_explanation", "Reverse pushing mimics recursive order: A B D F C E, same as recursive DFS.")])

    # bfs_vs_dfs — free-form comparison
    uid = _unit("bfs_vs_dfs", "BFS vs DFS — practice", "Argue the choice between BFS and DFS", UnitType.PRACTICE, dims={R, T})
    _ex(uid, "bfs_vs_dfs", InteractionType.FREE_FORM,
        "Two tasks on the same unweighted city graph: (1) find whether the museum is reachable from the hotel; "
        "(2) find the route with the fewest streets. Which traversal for each, and why?",
        {"reference_points": [
            {"id": "p1", "keywords": ["bfs", "breadth"],
             "text": "Assigns BFS to the fewest-streets task."},
            {"id": "p2", "keywords": ["dfs", "depth", "either", "both"],
             "text": "Says reachability can be answered by DFS (or either traversal)."},
            {"id": "p3", "keywords": ["level", "layer", "distance", "fewest", "shortest", "first time", "unweighted"],
             "text": "Justifies BFS via level-by-level expansion."},
         ], "min_points": 2},
        d((4, 2, 4, 4)), requires_ai=True, ordering=1,
        hints=[_h("socratic_question", "What property does BFS's level order give you about the moment a vertex is first reached?"),
               _h("micro_question", "Does task (1) care about the route's length at all?"),
               _h("light_hint", "Reachability: any traversal works. Fewest streets: you need first-reach = optimal."),
               _h("targeted_explanation", "(1) DFS or BFS — only reachability matters. (2) BFS: expanding by distance means the first arrival at the museum uses the fewest streets.")])

    # traversal_application — write count_reachable
    uid = _unit("traversal_application", "Application — practice", "Apply traversal to count a component", UnitType.APPLY, dims={E, T})
    _ex(uid, "traversal_application", InteractionType.CODE_WRITING,
        "Write `count_reachable(graph, start)` returning how many vertices are reachable from `start` "
        "(including start itself). Use any traversal you like.",
        {"function_name": "count_reachable",
         "starter": "def count_reachable(graph, start):\n    # your code here\n",
         "tests": [{"graph": G1, "start": "A", "expected": 6},
                   {"graph": {"A": ["B"], "B": [], "C": []}, "start": "A", "expected": 2},
                   {"graph": {"A": []}, "start": "A", "expected": 1}],
         "solution": ("def count_reachable(graph, start):\n"
                      "    visited = {start}\n    stack = [start]\n"
                      "    while stack:\n        node = stack.pop()\n"
                      "        for nxt in graph[node]:\n"
                      "            if nxt not in visited:\n"
                      "                visited.add(nxt)\n                stack.append(nxt)\n"
                      "    return len(visited)\n")},
        d((4, 4, 4, 5)), language="python", ordering=1,
        hints=[_h("socratic_question", "Which part of a traversal run already contains exactly the reachable vertices?"),
               _h("micro_question", "Can you reuse your BFS or DFS almost unchanged here?"),
               _h("light_hint", "Run any traversal from start and return the size of the visited set."),
               _h("targeted_explanation", "Traverse from start collecting visited; the answer is len(visited) — BFS and DFS give the same count.")])

    # recognizing_traversal — free-form signal spotting
    uid = _unit("recognizing_traversal", "Recognition — practice", "Spot traversal problems in the wild", UnitType.PRACTICE, dims={T, R})
    _ex(uid, "recognizing_traversal", InteractionType.FREE_FORM,
        "For each situation, say whether BFS or DFS fits best and why: (a) checking whether a puzzle state can "
        "reach the solved state; (b) finding the minimum number of moves to solve it.",
        {"reference_points": [
            {"id": "p1", "keywords": ["dfs", "either", "both", "bfs"],
             "text": "Says (a) reachability is fine with DFS (or either)."},
            {"id": "p2", "keywords": ["bfs", "breadth"],
             "text": "Says (b) minimum moves needs BFS."},
            {"id": "p3", "keywords": ["level", "layer", "shortest", "fewest", "minimum", "first time", "unweighted"],
             "text": "Justifies (b) with level-by-level / first-reach optimality."},
         ], "min_points": 2},
        d((4, 1, 4, 4)), requires_ai=True, ordering=1,
        hints=[_h("socratic_question", "Does question (a) mention anything about the number of moves?"),
               _h("micro_question", "In (b), what does 'minimum number of moves' correspond to in graph language?"),
               _h("light_hint", "Moves are edges; minimum moves = fewest edges = a shortest path in an unweighted graph."),
               _h("targeted_explanation", "(a) Any traversal (DFS is natural) answers reachability. (b) BFS: states are vertices, moves are edges, and BFS's first arrival achieves the minimum.")])

    # v0_readiness — assess unit with mixed exercises
    uid = _unit("v0_readiness", "V0 readiness — assess", "Demonstrate the V0 outcomes independently", UnitType.ASSESS, dims={K, E, R, T})
    _ex(uid, "v0_readiness", InteractionType.CODE_WRITING,
        "Final check, part 1 (independent): write `bfs_levels(graph, start)` that returns a dict mapping each "
        "reachable vertex to its BFS distance level from start (start = 0).",
        {"function_name": "bfs_levels",
         "starter": "from collections import deque\n\ndef bfs_levels(graph, start):\n    # your code here\n",
         "tests": [{"graph": G1, "start": "A", "expected": {"A": 0, "B": 1, "C": 1, "D": 2, "E": 2, "F": 3}},
                   {"graph": {"A": ["B"], "B": []}, "start": "A", "expected": {"A": 0, "B": 1}}],
         "solution": ("from collections import deque\n\n"
                      "def bfs_levels(graph, start):\n"
                      "    levels = {start: 0}\n    queue = deque([start])\n"
                      "    while queue:\n        node = queue.popleft()\n"
                      "        for nxt in graph[node]:\n"
                      "            if nxt not in levels:\n"
                      "                levels[nxt] = levels[node] + 1\n"
                      "                queue.append(nxt)\n"
                      "    return levels\n")},
        d((4, 4, 4, 4)), language="python", ordering=1,
        hints=[_h("socratic_question", "When D is dequeued, what do you already know about its distance from A?"),
               _h("micro_question", "Which structure can hold vertex → distance instead of a separate visited set?"),
               _h("light_hint", "A dict of levels doubles as the visited check: membership means visited."),
               _h("targeted_explanation", "Replace visited with levels={start:0}; when enqueuing an unseen neighbor, its level = current level + 1.")])
    _ex(uid, "v0_readiness", InteractionType.FREE_FORM,
        "Final check, part 2 (independent): a friend's BFS sometimes visits the same vertex twice and occasionally "
        "runs forever on graphs with cycles. Diagnose the most likely bug and explain the fix.",
        {"reference_points": [
            {"id": "p1", "keywords": ["visited", "not marking", "missing", "no visited", "forgets"],
             "text": "Identifies missing or wrong visited handling."},
            {"id": "p2", "keywords": ["dequeue", "popleft", "enqueue", "when"],
             "text": "Locates marking at the wrong time (dequeue vs enqueue)."},
            {"id": "p3", "keywords": ["enqueue", "before appending", "on enqueue", "add before queue.append", "queue.append"],
             "text": "Prescribes marking at enqueue time."},
         ], "min_points": 2},
        d((4, 3, 4, 4)), requires_ai=True, ordering=2,
        hints=[_h("socratic_question", "Where does your friend add vertices to `visited` — before or after queue.append?"),
               _h("micro_question", "If marking happens at dequeue, how can one vertex be enqueued twice?"),
               _h("light_hint", "Two sources can enqueue the same vertex before either is dequeued."),
               _h("targeted_explanation", "Marking at dequeue lets a vertex be enqueued twice; mark it at enqueue time so it enters the queue at most once.")])

    # --- Layer 1: traversal_boundary ---
    uid = _unit("traversal_boundary", "Traversal boundary — practice",
                "Understand that one traversal explores exactly one component",
                UnitType.PRACTICE, dims={K, R})
    _ex(uid, "traversal_boundary", InteractionType.MCQ,
        "Graph: A-B-C and D-E (two separate components). BFS from A visits A, B, C and stops. "
        "Why does it stop?",
        *_mcq("", [("a", "BFS is broken"),
                   ("b", "All vertices reachable from A have been visited — it has finished A's component"),
                   ("c", "BFS only works on connected graphs"),
                   ("d", "It ran out of memory")], "b",
              "The visited set contains A's component {A,B,C}. The queue is empty because no more neighbors exist. D and E are in a different component — unreachable from A.", (3, 2, 3, 3)), ordering=1,
        hints=[_h("socratic_question", "After C is processed, which vertices are in the queue?"),
               _h("micro_question", "Are D and E adjacent to any vertex in {A, B, C}?"),
               _h("light_hint", "The queue empties when there are no more unvisited neighbors of visited vertices."),
               _h("targeted_explanation", "BFS from A visits exactly {A,B,C} because they are all reachable from A. The queue empties when the component is exhausted. D and E form a separate component.")])
    _ex(uid, "traversal_boundary", InteractionType.FREE_FORM,
        "Graph: 1-2-3 and 4-5 and 6 (three components). DFS from 1 finishes. What vertices are visited, and why does DFS stop? "
        "What does the visited set represent?",
        {"reference_points": [
            {"id": "p1", "keywords": ["1", "2", "3", "one", "two", "three"],
             "text": "Identifies visited set = {1,2,3} — the component containing 1."},
            {"id": "p2", "keywords": ["stop", "empty", "no more", "frontier", "queue", "stack", "neighbors"],
             "text": "Explains traversal stops when frontier is empty — no more unvisited neighbors."},
            {"id": "p3", "keywords": ["component", "reachable", "different", "separate", "unvisited"],
             "text": "Says unvisited vertices (4,5,6) are in different components."},
        ], "min_points": 2},
        d((3, 2, 3, 3)), requires_ai=True, ordering=2,
        hints=[_h("socratic_question", "After visiting 3, what neighbors does it have that are unvisited?"),
               _h("micro_question", "Can the traversal jump from 3 to 4 without an edge?"),
               _h("light_hint", "The visited set is exactly the component of the start vertex."),
               _h("targeted_explanation", "DFS from 1 visits 1,2,3. It stops because 3's neighbors (2) are already visited — the component is done. Vertices 4,5,6 are in other components.")])

    # --- Layer 1: component_discovery ---
    uid = _unit("component_discovery", "Component discovery — practice",
                "Recognize that an unvisited vertex after traversal signals a new component",
                UnitType.PRACTICE, dims={K, E, R})
    _ex(uid, "component_discovery", InteractionType.CODE_TRACING,
        "This code runs BFS from vertex 0, then checks for unvisited vertices.\n"
        "What does it print?\n\n"
        "graph = [[1], [0, 2], [1], [4], [3]]  # 0-1-2 and 3-4 are separate components\n"
        "n = 5\n"
        "visited = set()\n"
        "from collections import deque\n"
        "queue = deque([0])\n"
        "visited.add(0)\n"
        "while queue:\n"
        "    v = queue.popleft()\n"
        "    for nxt in graph[v]:\n"
        "        if nxt not in visited:\n"
        "            visited.add(nxt)\n"
        "            queue.append(nxt)\n"
        'print("visited:", sorted(visited))\n'
        "unvisited = [v for v in range(n) if v not in visited]\n"
        'print("unvisited:", unvisited)',
        {"code": "", "expected_output": "visited: [0, 1, 2]\nunvisited: [3, 4]"},
        d((3, 3, 3, 3)), ordering=1,
        hints=[_h("socratic_question", "Which vertices are reachable from 0 following the edges?"),
               _h("micro_question", "After the BFS loop ends, which vertices were never added to visited?"),
               _h("light_hint", "Edges are 0-1, 1-2 and 3-4. From 0 you can only reach 0,1,2."),
               _h("targeted_explanation", "BFS from 0 visits {0,1,2}. Vertices 3 and 4 are in a different component, so they remain unvisited — this is the signal to start a new traversal.")])
    _ex(uid, "component_discovery", InteractionType.FREE_FORM,
        "You run BFS from vertex A in a graph and the visited set is {A, B, C}. Vertex D is not in visited. "
        "Does this mean BFS failed? What does it tell you about D, and what should you do next?",
        {"reference_points": [
            {"id": "p1", "keywords": ["no", "not fail", "correct", "finished", "done"],
             "text": "Says BFS did not fail — it finished its component."},
            {"id": "p2", "keywords": ["different", "other", "another", "separate", "component"],
             "text": "Identifies D is in a different component."},
            {"id": "p3", "keywords": ["start", "run", "traversal", "again", "unvisited", "D"],
             "text": "Says to start a new traversal from D."},
        ], "min_points": 2},
        d((3, 3, 3, 3)), requires_ai=True, ordering=2,
        hints=[_h("socratic_question", "If BFS visited A, B, C and stopped, did it process all neighbors of those vertices?"),
               _h("micro_question", "Is there an edge between {A,B,C} and D?"),
               _h("light_hint", "No edge between the visited set and D means D is in another component."),
               _h("targeted_explanation", "BFS finished correctly — it visited exactly the component containing A. D is unvisited because no path exists from A to D. Start a new BFS from D to discover its component.")])

    # --- Layer 1: component_enumeration ---
    uid = _unit("component_enumeration", "Component enumeration — practice",
                "Implement the outer loop to count and label all components",
                UnitType.PRACTICE, dims={E, R})
    _ex(uid, "component_enumeration", InteractionType.CODE_TRACING,
        "This code counts connected components using the outer loop pattern. What does it print?\n\n"
        "graph = [[1], [0, 2], [1], [4], [3], []]  # components: {0,1,2}, {3,4}, {5}\n"
        "n = 6\n"
        "visited = set()\n"
        "components = 0\n"
        "from collections import deque\n"
        "for start in range(n):\n"
        "    if start not in visited:\n"
        "        components += 1\n"
        "        queue = deque([start])\n"
        "        visited.add(start)\n"
        "        while queue:\n"
        "            v = queue.popleft()\n"
        "            for nxt in graph[v]:\n"
        "                if nxt not in visited:\n"
        "                    visited.add(nxt)\n"
        "                    queue.append(nxt)\n"
        'print("components:", components)',
        {"code": "", "expected_output": "components: 3"},
        d((3, 4, 4, 4)), ordering=1,
        hints=[_h("socratic_question", "How many times does the `if start not in visited:` block execute?"),
               _h("micro_question", "When start=0, what happens? When start=3, what happens?"),
               _h("light_hint", "The outer loop runs for every vertex, but the inner BFS only runs for unvisited vertices."),
               _h("targeted_explanation", "start=0: BFS visits {0,1,2}, components=1. start=1,2: skipped (visited). start=3: BFS visits {3,4}, components=2. start=4: skipped. start=5: BFS visits {5}, components=3. Result: 3.")])
    _ex(uid, "component_enumeration", InteractionType.CODE_WRITING,
        "Write `count_components(graph)` that returns the number of connected components in an undirected graph. "
        "graph is an adjacency list: graph[v] is a list of neighbors of vertex v.",
        {"function_name": "count_components",
         "starter": "from collections import deque\n\ndef count_components(graph):\n    # your code here\n",
         "tests": [{"graph": [[1], [0, 2], [1], [4], [3], []], "expected": 3},
                   {"graph": [[1, 2], [0, 2], [0, 1]], "expected": 1},  # triangle
                   {"graph": [[], [], []], "expected": 3},  # three isolated vertices
                   {"graph": [[1], [0], [3], [2]], "expected": 2}],  # two pairs
         "solution": ("from collections import deque\n\n"
                      "def count_components(graph):\n"
                      "    n = len(graph)\n"
                      "    visited = set()\n"
                      "    components = 0\n"
                      "    for start in range(n):\n"
                      "        if start not in visited:\n"
                      "            components += 1\n"
                      "            queue = deque([start])\n"
                      "            visited.add(start)\n"
                      "            while queue:\n"
                      "                v = queue.popleft()\n"
                      "                for nxt in graph[v]:\n"
                      "                    if nxt not in visited:\n"
                      "                        visited.add(nxt)\n"
                      "                        queue.append(nxt)\n"
                      "    return components\n")},
        d((3, 4, 4, 4)), language="python", ordering=2,
        hints=[_h("socratic_question", "What does the visited set contain after the inner while loop finishes?"),
               _h("micro_question", "How many times should you increment the counter — once per vertex or once per BFS run?"),
               _h("light_hint", "Increment when you find an unvisited vertex and start a new BFS from it."),
               _h("targeted_explanation", "Outer loop over all vertices. If unvisited, start BFS, increment count. The BFS marks the whole component visited. Total O(V+E) because every vertex/edge processed once.")])
    _ex(uid, "component_enumeration", InteractionType.CODE_WRITING,
        "Write `label_components(graph)` that returns a list `comp` where `comp[v]` is the component ID "
        "(0, 1, 2, ...) of vertex v. Vertices in the same component get the same ID; different components get different IDs.",
        {"function_name": "label_components",
         "starter": "from collections import deque\n\ndef label_components(graph):\n    # your code here\n",
         "tests": [{"graph": [[1], [0, 2], [1], [4], [3], []], "expected": [0, 0, 0, 1, 1, 2]},
                   {"graph": [[1, 2], [0, 2], [0, 1]], "expected": [0, 0, 0]},
                   {"graph": [[], [], []], "expected": [0, 1, 2]},
                   {"graph": [[1], [0], [3], [2]], "expected": [0, 0, 1, 1]}],
         "solution": ("from collections import deque\n\n"
                      "def label_components(graph):\n"
                      "    n = len(graph)\n"
                      "    comp = [-1] * n\n"
                      "    cid = 0\n"
                      "    for start in range(n):\n"
                      "        if comp[start] == -1:\n"
                      "            queue = deque([start])\n"
                      "            comp[start] = cid\n"
                      "            while queue:\n"
                      "                v = queue.popleft()\n"
                      "                for nxt in graph[v]:\n"
                      "                    if comp[nxt] == -1:\n"
                      "                        comp[nxt] = cid\n"
                      "                        queue.append(nxt)\n"
                      "            cid += 1\n"
                      "    return comp\n")},
        d((3, 4, 4, 4)), language="python", ordering=3,
        hints=[_h("socratic_question", "Instead of a visited set, what can you use to track both 'visited' and 'which component'?"),
               _h("micro_question", "When you start a new BFS, what component ID should you assign to all vertices it visits?"),
               _h("light_hint", "Use a list initialized to -1. When you start a BFS, assign the current component ID to every vertex you visit."),
               _h("targeted_explanation", "comp[v] = -1 means unvisited. When starting BFS from start, set comp[start] = cid, and every vertex reached gets comp[v] = cid. After the BFS finishes, increment cid for the next component.")])

    # --- Layer 1: component_enumeration apply (transfer) ---
    uid = _unit("component_enumeration", "Component enumeration — apply",
                "Apply component counting to a simple real-world scenario",
                UnitType.APPLY, dims={T, R})
    _ex(uid, "component_enumeration", InteractionType.FREE_FORM,
        "A social network has 6 people. Friendships: Alice-Bob, Bob-Carol, Dave-Eve. Frank has no friends. "
        "How many disconnected friend groups exist? Explain how you know without drawing the graph.",
        {"reference_points": [
            {"id": "p1", "keywords": ["3", "three", "groups", "components"],
             "text": "Identifies 3 groups/components."},
            {"id": "p2", "keywords": ["alice", "bob", "carol", "dave", "eve", "frank"],
             "text": "Names the three groups: {Alice,Bob,Carol}, {Dave,Eve}, {Frank}."},
            {"id": "p3", "keywords": ["traversal", "bfs", "dfs", "visited", "unvisited", "outer", "loop", "count"],
             "text": "Mentions running traversal from each unvisited person / outer loop counting."},
        ], "min_points": 2},
        d((3, 4, 4, 4)), requires_ai=True, ordering=4,
        hints=[_h("socratic_question", "Which people are connected to Alice through friendships?"),
               _h("micro_question", "After exploring Alice's group, who is left unvisited?"),
               _h("light_hint", "Three groups: Alice-Bob-Carol, Dave-Eve, Frank alone."),
               _h("targeted_explanation", "Model people as vertices, friendships as edges. Run traversal from Alice → visits {Alice,Bob,Carol}. Next unvisited is Dave → visits {Dave,Eve}. Next unvisited is Frank → visits {Frank}. Count = 3.")])

    # --- Layer 2: bfs_distance ---
    uid = _unit("bfs_distance", "BFS distance — practice",
                "Track distances during BFS and read unreachable as -1",
                UnitType.PRACTICE, dims={K, E, R})
    _ex(uid, "bfs_distance", InteractionType.OUTPUT_PREDICTION,
        "What does this code print?\n\n"
        "graph = [[1, 2], [3], [3, 4], [5], [5], []]\n"
        "distance = [-1] * 6\n"
        "distance[0] = 0\n"
        "from collections import deque\n"
        "queue = deque([0])\n"
        "while queue:\n"
        "    v = queue.popleft()\n"
        "    for nxt in graph[v]:\n"
        "        if distance[nxt] == -1:\n"
        "            distance[nxt] = distance[v] + 1\n"
        "            queue.append(nxt)\n"
        "print(distance)",
        {"code": "", "expected_output": "[0, 1, 1, 2, 2, 3]"},
        d((3, 3, 3, 3)), ordering=1,
        hints=[_h("socratic_question", "The source is wave 0. Which vertices are wave 1 — and which wave are 3 and 4 in?"),
               _h("micro_question", "When vertex 3 is discovered, what is distance[3]'s current value, and what is distance[1] + 1?"),
               _h("light_hint", "Vertex 5 is first discovered from vertex 3, which has distance 2."),
               _h("targeted_explanation", "Waves: {0} | {1,2} | {3,4} | {5} → distance = [0, 1, 1, 2, 2, 3]. Vertex 5 gets distance[3] + 1 = 3.")])
    _ex(uid, "bfs_distance", InteractionType.MCQ,
        "From A, two routes reach T: A → B → D → T (3 edges) and A → C → E → F → T (4 edges). "
        "When BFS from A discovers T via the first route, what distance does T get — and could a "
        "later discovery have been shorter?",
        *_mcq("", [("a", "3 — and no: BFS discovers vertices in nondecreasing distance order, so the first discovery is minimal"),
                  ("b", "3 — but a later discovery might have found a shorter route"),
                  ("c", "4 — BFS records the longest route"),
                  ("d", "7 — distances add up across all routes")], "a",
             "BFS processes vertices wave by wave; when T is first discovered from a distance-2 vertex, no shorter route could exist yet — the first discovery is final.", (3, 2, 4, 3)), ordering=2,
        hints=[_h("socratic_question", "In what order does BFS dequeue vertices — by distance, or arbitrarily?"),
               _h("micro_question", "T is discovered while processing a distance-2 vertex. Could a distance-1 vertex still discover it later?"),
               _h("light_hint", "Neighbors of distance-2 vertices get distance 3 at first discovery."),
               _h("targeted_explanation", "First discovery happens from the closest possible frontier, so distance[T] = 3 immediately — and it is final. 'Shortest' means fewest edges, and BFS achieves that at first discovery.")])
    _ex(uid, "bfs_distance", InteractionType.CODE_TRACING,
        "This BFS computes distances on a disconnected graph. What does it print?\n\n"
        "graph = [[1], [0, 2], [1], [4], [3], []]\n"
        "distance = [-1] * 6\n"
        "distance[0] = 0\n"
        "from collections import deque\n"
        "queue = deque([0])\n"
        "while queue:\n"
        "    v = queue.popleft()\n"
        "    for nxt in graph[v]:\n"
        "        if distance[nxt] == -1:\n"
        "            distance[nxt] = distance[v] + 1\n"
        "            queue.append(nxt)\n"
        'print(distance[2], distance[5])',
        {"code": "", "expected_output": "2 -1"},
        d((3, 3, 4, 3)), ordering=3,
        hints=[_h("socratic_question", "Which vertices can be reached from 0 at all?"),
               _h("micro_question", "Vertex 5 has no edges. Does anything ever set distance[5] away from -1?"),
               _h("light_hint", "Components {0,1,2} and {3,4} and {5}: only 0's component gets finite distances."),
               _h("targeted_explanation", "From 0: distance = [0,1,2,-1,-1,-1]. Vertex 2 is at distance 2; vertex 5 is unreachable and keeps -1 — our convention for 'no path exists'.")])
    _ex(uid, "bfs_distance", InteractionType.CODE_WRITING,
        "Complete the distance-tracking BFS below: fill in the two marked lines so that `distance` "
        "holds, for every vertex, its distance from `start`, with -1 for vertices BFS never reaches. "
        "Do not change anything else.",
        {"function_name": "bfs_distances_completed",
         "starter": ("from collections import deque\n\n"
                     "def bfs_distances_completed(graph, start):\n"
                     "    n = len(graph)\n"
                     "    distance = [-1] * n\n"
                     "    distance[start] = 0\n"
                     "    queue = deque([start])\n"
                     "    while queue:\n"
                     "        v = queue.popleft()\n"
                     "        for nxt in graph[v]:\n"
                     "            if distance[nxt] == -1:\n"
                     "                # line 1: record the distance of nxt\n"
                     "                # line 2: put nxt on the queue\n"
                     "                pass\n"
                     "    return distance\n"),
         "tests": [{"graph": [[1, 2], [3], [3, 4], [5], [5], []], "start": 0,
                    "expected": [0, 1, 1, 2, 2, 3]},
                   {"graph": [[1], [0, 2], [1], [4], [3], []], "start": 0,
                    "expected": [0, 1, 2, -1, -1, -1]},
                   {"graph": [[]], "start": 0, "expected": [0]}],
         "solution": ("from collections import deque\n\n"
                      "def bfs_distances_completed(graph, start):\n"
                      "    n = len(graph)\n"
                      "    distance = [-1] * n\n"
                      "    distance[start] = 0\n"
                      "    queue = deque([start])\n"
                      "    while queue:\n"
                      "        v = queue.popleft()\n"
                      "        for nxt in graph[v]:\n"
                      "            if distance[nxt] == -1:\n"
                      "                distance[nxt] = distance[v] + 1\n"
                      "                queue.append(nxt)\n"
                      "    return distance\n")},
        d((3, 3, 3, 3)), language="python", ordering=4,
        hints=[_h("socratic_question", "The new vertex's distance is one more than whose distance?"),
               _h("micro_question", "What role does the `distance[nxt] == -1` check play — is a separate visited set still needed?"),
               _h("light_hint", "Line 1: distance[nxt] = distance[v] + 1. Line 2: queue.append(nxt)."),
               _h("targeted_explanation", "Inside the -1 check: distance[nxt] = distance[v] + 1, then queue.append(nxt). The -1 check IS the visited check.")])
    _ex(uid, "bfs_distance", InteractionType.CODE_WRITING,
        "Write `bfs_distances(graph, start)` that runs BFS from `start` and returns a list `distance` "
        "with one entry per vertex: the minimum number of edges from `start`, or -1 if the vertex is "
        "unreachable. graph is an adjacency list of integer vertices.",
        {"function_name": "bfs_distances",
         "starter": "from collections import deque\n\ndef bfs_distances(graph, start):\n    # your code here\n",
         "tests": [{"graph": [[1, 2], [3], [3, 4], [5], [5], []], "start": 0,
                    "expected": [0, 1, 1, 2, 2, 3]},
                   {"graph": [[1], [0, 2], [1], [4], [3], []], "start": 0,
                    "expected": [0, 1, 2, -1, -1, -1]},
                   {"graph": [[1], [0], [3], [2]], "start": 2,
                    "expected": [-1, -1, 0, 1]},
                   {"graph": [[]], "start": 0, "expected": [0]}],
         "solution": ("from collections import deque\n\n"
                      "def bfs_distances(graph, start):\n"
                      "    n = len(graph)\n"
                      "    distance = [-1] * n\n"
                      "    distance[start] = 0\n"
                      "    queue = deque([start])\n"
                      "    while queue:\n"
                      "        v = queue.popleft()\n"
                      "        for nxt in graph[v]:\n"
                      "            if distance[nxt] == -1:\n"
                      "                distance[nxt] = distance[v] + 1\n"
                      "                queue.append(nxt)\n"
                      "    return distance\n")},
        d((3, 4, 4, 3)), language="python", ordering=5,
        hints=[_h("socratic_question", "What does distance[v] == -1 mean before a vertex is discovered — and how does that replace the visited set?"),
               _h("micro_question", "What must be true about the vertex you just dequeued when you assign a neighbor's distance?"),
               _h("light_hint", "Seed distance[start] = 0; every newly discovered neighbor gets distance[v] + 1."),
               _h("targeted_explanation", "distance = [-1]*n; distance[start] = 0; BFS with the distance array as the visited check: distance[nxt] = distance[v] + 1 on discovery. Vertices never discovered keep -1.")])

    # --- Layer 2: path_reconstruction ---
    uid = _unit("path_reconstruction", "Path reconstruction — practice",
                "Track parents during BFS and rebuild the actual shortest path",
                UnitType.PRACTICE, dims={K, E, R})
    _ex(uid, "path_reconstruction", InteractionType.OUTPUT_PREDICTION,
        "What does this code print?\n\n"
        "graph = [[1, 2], [3], [3, 4], [5], [5], []]\n"
        "parent = [-1] * 6\n"
        "from collections import deque\n"
        "queue = deque([0])\n"
        "seen = {0}\n"
        "while queue:\n"
        "    v = queue.popleft()\n"
        "    for nxt in graph[v]:\n"
        "        if nxt not in seen:\n"
        "            seen.add(nxt)\n"
        "            parent[nxt] = v\n"
        "            queue.append(nxt)\n"
        "print(parent)",
        {"code": "", "expected_output": "[-1, 0, 0, 1, 2, 3]"},
        d((3, 3, 3, 3)), ordering=1,
        hints=[_h("socratic_question", "Who discovers vertex 3 first — 1 or 2, and why?"),
               _h("micro_question", "Vertex 1 is dequeued before vertex 2, so whose loop iteration sets parent[3]?"),
               _h("light_hint", "Each vertex's parent is the vertex that first enqueued it."),
               _h("targeted_explanation", "1 and 2 are discovered by 0; 3 is discovered by 1 (dequeued first), 4 by 2, 5 by 3 → parent = [-1, 0, 0, 1, 2, 3].")])
    _ex(uid, "path_reconstruction", InteractionType.MCQ,
        "graph = [[1, 2], [3], [3, 4], [5], [5], []], BFS from 0 with parent tracking. "
        "Which path does BFS's parent tree give for 0 → 5?",
        *_mcq("", [("a", "0 → 1 → 3 → 5"),
                  ("b", "0 → 2 → 4 → 5 — equally short, so BFS must return both"),
                  ("c", "0 → 2 → 3 → 5"),
                  ("d", "No path exists from 0 to 5")], "a",
             "Vertex 5 is first discovered from 3, and 3 from 1: the parent tree stores ONE valid shortest path (0-2-4-5 is equally short but was not the discovery route).", (3, 3, 4, 3)), ordering=2,
        hints=[_h("socratic_question", "Dequeue order is 0, 1, 2, 3, 4. When 3 is dequeued, who discovers 5?"),
               _h("micro_question", "Does the parent of 5 ever get overwritten after it is first set?"),
               _h("light_hint", "parent[5] = 3, parent[3] = 1, parent[1] = 0."),
               _h("targeted_explanation", "Following parents from 5: 5 ← 3 ← 1 ← 0. The 0-2-4-5 route is also shortest, but BFS returns one valid shortest path — the discovery route.")])
    _ex(uid, "path_reconstruction", InteractionType.CODE_TRACING,
        "What does this code print?\n\n"
        "def reconstruct(parent, target):\n"
        "    path = []\n"
        "    v = target\n"
        "    while v != -1:\n"
        "        path.append(v)\n"
        "        v = parent[v]\n"
        "    path.reverse()\n"
        "    return path\n\n"
        "parent = [-1, 0, 0, 1, 2, 3]\n"
        "print(reconstruct(parent, 4))",
        {"code": "", "expected_output": "[0, 2, 4]"},
        d((3, 3, 4, 3)), ordering=3,
        hints=[_h("socratic_question", "The walk starts at the target and follows parents — in which direction does the list grow?"),
               _h("micro_question", "Before reverse(), what does path contain? Why is parent[0] = -1 the stopping point?"),
               _h("light_hint", "Collect 4, 2, 0, then reverse."),
               _h("targeted_explanation", "Backward walk collects [4, 2, 0]; reversing gives [0, 2, 4] — the forward path from the source.")])
    _ex(uid, "path_reconstruction", InteractionType.CODE_WRITING,
        "Complete `reconstruct_path_completed(parent, source, target)` below: fill in the two marked "
        "lines of the backward walk so it returns the path from source to target as a list, or [] if "
        "the target was never discovered (parent[target] == -1 with target != source). Do not change "
        "anything else.",
        {"function_name": "reconstruct_path_completed",
         "starter": ("def reconstruct_path_completed(parent, source, target):\n"
                     "    if target != source and parent[target] == -1:\n"
                     "        return []\n"
                     "    path = []\n"
                     "    v = target\n"
                     "    while True:\n"
                     "        # line 1: add v to the path\n"
                     "        # line 2: stop the walk when the source is reached\n"
                     "        v = parent[v]\n"
                     "    path.reverse()\n"
                     "    return path\n"),
         "tests": [{"args": ["parent", "source", "target"],
                    "parent": [-1, 0, 0, 1, 2, 3], "source": 0, "target": 5,
                    "expected": [0, 1, 3, 5]},
                   {"args": ["parent", "source", "target"],
                    "parent": [-1, 0, 0, 1, 2, 3], "source": 0, "target": 0,
                    "expected": [0]},
                   {"args": ["parent", "source", "target"],
                    "parent": [-1, 0, -1, -1], "source": 0, "target": 3,
                    "expected": []}],
         "solution": ("def reconstruct_path_completed(parent, source, target):\n"
                      "    if target != source and parent[target] == -1:\n"
                      "        return []\n"
                      "    path = []\n"
                      "    v = target\n"
                      "    while True:\n"
                      "        path.append(v)\n"
                      "        if v == source:\n"
                      "            break\n"
                      "        v = parent[v]\n"
                      "    path.reverse()\n"
                      "    return path\n")},
        d((3, 3, 4, 3)), language="python", ordering=4,
        hints=[_h("socratic_question", "The walk starts at the target — where must it stop for the reversed list to begin at the source?"),
               _h("micro_question", "If you append v and only then check v == source, what happens on the source == target call?"),
               _h("light_hint", "Line 1: path.append(v). Line 2: if v == source: break."),
               _h("targeted_explanation", "Append v, break when v is the source, otherwise step to parent[v]; reversing the collected sequence yields the forward path. The early return [] handles the unreachable target.")])
    _ex(uid, "path_reconstruction", InteractionType.CODE_WRITING,
        "Write `shortest_path(graph, source, target)` for an unweighted graph: run ONE BFS from "
        "`source` that also records parents, and return the shortest path from source to target as a "
        "list of vertices. Return [] when no path exists; return [source] when source == target. "
        "graph is an adjacency list of integer vertices.",
        {"function_name": "shortest_path",
         "starter": "from collections import deque\n\ndef shortest_path(graph, source, target):\n    # your code here\n",
         "tests": [{"args": ["graph", "source", "target"],
                    "graph": [[1, 2], [3], [3, 4], [5], [5], []],
                    "source": 0, "target": 5, "expected": [0, 1, 3, 5]},
                   {"args": ["graph", "source", "target"],
                    "graph": [[1], [2], [3], []], "source": 0, "target": 3,
                    "expected": [0, 1, 2, 3]},
                   {"args": ["graph", "source", "target"],
                    "graph": [[1], [0], [], []], "source": 0, "target": 3,
                    "expected": []},
                   {"args": ["graph", "source", "target"],
                    "graph": [[1, 2], [0], [0]], "source": 1, "target": 1,
                    "expected": [1]}],
         "solution": ("from collections import deque\n\n"
                      "def shortest_path(graph, source, target):\n"
                      "    if source == target:\n"
                      "        return [source]\n"
                      "    n = len(graph)\n"
                      "    parent = [-1] * n\n"
                      "    parent[source] = source\n"
                      "    queue = deque([source])\n"
                      "    while queue:\n"
                      "        v = queue.popleft()\n"
                      "        for nxt in graph[v]:\n"
                      "            if parent[nxt] == -1:\n"
                      "                parent[nxt] = v\n"
                      "                queue.append(nxt)\n"
                      "    if parent[target] == -1:\n"
                      "        return []\n"
                      "    path = []\n"
                      "    v = target\n"
                      "    while v != source:\n"
                      "        path.append(v)\n"
                      "        v = parent[v]\n"
                      "    path.append(source)\n"
                      "    path.reverse()\n"
                      "    return path\n")},
        d((3, 4, 4, 4)), language="python", ordering=5,
        hints=[_h("socratic_question", "Which single array can do double duty as 'visited' and 'who discovered me'?"),
               _h("micro_question", "After the BFS ends, how do you detect that target was never discovered?"),
               _h("light_hint", "Mark the source in parent (e.g. parent[source] = source); discover neighbors with parent[nxt] = v; walk back from target and reverse."),
               _h("targeted_explanation", "parent = [-1]*n doubles as the visited check. BFS sets parent[nxt] = v at first discovery. If parent[target] stays -1 return []; otherwise follow parents back to source and reverse the collected vertices. Still one BFS: O(V+E), reconstruction at most O(V).")])

    # --- Layer 2: path_reconstruction apply (transfer) ---
    uid = _unit("path_reconstruction", "Path reconstruction — apply",
                "Recognize a shortest-path situation in an unfamiliar context",
                UnitType.APPLY, dims={T, R})
    _ex(uid, "path_reconstruction", InteractionType.FREE_FORM,
        "A professional network: connections are mutual, and 'one introduction' means one edge. "
        "You must tell a user the minimum number of introductions between Priya and Marco AND the "
        "actual chain of people connecting them. You were not told which algorithm to use. "
        "Which traversal do you choose, what state do you track during it, and how do you get the "
        "chain of people at the end?",
        {"reference_points": [
            {"id": "p1", "keywords": ["bfs", "breadth"],
             "text": "Chooses BFS without being told."},
            {"id": "p2", "keywords": ["level", "layer", "distance", "fewest", "minimum", "unweighted", "first time", "first discovery"],
             "text": "Justifies BFS: levels = fewest introductions because every connection costs one step."},
            {"id": "p3", "keywords": ["parent", "predecessor", "who discovered", "remember", "track"],
             "text": "Tracks parent/predecessor during the BFS."},
            {"id": "p4", "keywords": ["reverse", "backward", "back from", "walk back", "follow parent"],
             "text": "Reconstructs the chain by walking parents back from Marco and reversing."},
         ], "min_points": 3},
        d((3, 4, 4, 4)), requires_ai=True, ordering=6,
        hints=[_h("socratic_question", "Does any connection 'cost' more than another — what does that tell you about the graph?"),
               _h("micro_question", "Once BFS knows the distance to Marco, what extra per-vertex memory turns that number into an actual chain of names?"),
               _h("light_hint", "Track who discovered each person; then walk backward from Marco to Priya and reverse the sequence."),
               _h("targeted_explanation", "Unweighted graph + fewest edges → BFS. During the BFS record parent[person] = discoverer. Afterward walk parents from Marco back to Priya and reverse: the chain of people and its length both fall out of one BFS — still O(V+E).")])

    # --- Layer 3: cycle_encounter_reasoning ---
    uid = _unit("cycle_encounter_reasoning", "Cycle encounter reasoning — practice",
                "Observe what traversal sees when it meets a visited neighbor in an undirected graph",
                UnitType.PRACTICE, dims={K, E, R})
    _ex(uid, "cycle_encounter_reasoning", InteractionType.CODE_TRACING,
        "This DFS prints a line every time it meets an already-visited neighbor, tagged with "
        "whether that neighbor is the vertex it came from. The graph is the TREE A—B—C stored as "
        "an undirected adjacency list. What does it print?\n\n"
        'graph = {"A": ["B"], "B": ["A", "C"], "C": ["B"]}\n'
        "visited = set()\n\n"
        "def dfs(v, came_from):\n"
        "    visited.add(v)\n"
        "    for nbr in graph[v]:\n"
        "        if nbr not in visited:\n"
        "            dfs(nbr, v)\n"
        "        elif nbr == came_from:\n"
        '            print(v, "sees", nbr, "(parent)")\n'
        "        else:\n"
        '            print(v, "sees", nbr, "(not parent)")\n\n'
        'dfs("A", None)\n'
        'print("finished")',
        {"code": "", "expected_output": "B sees A (parent)\nC sees B (parent)\nfinished"},
        d((3, 2, 3, 3)), ordering=1,
        hints=[_h("socratic_question", "Which neighbor lists contain A — and from which call is A the vertex the traversal came from?"),
               _h("micro_question", "When dfs('C', 'B') scans graph['C'], is 'B' already visited? Is it the came_from?"),
               _h("light_hint", "On a tree the only visited neighbor any vertex can possibly meet is its own parent."),
               _h("targeted_explanation", "dfs('B','A') meets A: visited, and A is the came_from → '(parent)'. dfs('C','B') meets B: visited, and B is the came_from → '(parent)'. A tree produces parent meetings only — '(not parent)' never appears.")])
    _ex(uid, "cycle_encounter_reasoning", InteractionType.FREE_FORM,
        "In an undirected graph stored as an adjacency list, every vertex DFS enters will see at "
        "least one visited neighbor: its parent. So 'my neighbor is visited' alone cannot "
        "distinguish a tree from a graph full of cycles. Explain in your own words (a) why the "
        "parent always shows up as visited, and (b) what extra information turns this observation "
        "into something meaningful.",
        {"reference_points": [
            {"id": "p1", "keywords": ["both", "two directions", "both directions", "twice", "reverse", "other side", "same edge", "back"],
             "text": "The arrival edge is stored in both adjacency lists, so the parent appears in the current vertex's neighbor list."},
            {"id": "p2", "keywords": ["visited", "marked", "mark", "entry", "earlier", "before"],
             "text": "The parent was marked visited when the traversal entered it earlier."},
            {"id": "p3", "keywords": ["parent", "came from", "came_from", "arrival", "arrived", "where i came", "previous", "which edge"],
             "text": "The missing information is WHERE the traversal came from — the parent identifies the arrival edge."},
            {"id": "p4", "keywords": ["not the parent", "non-parent", "not parent", "second route", "two routes", "another route", "other"],
             "text": "A visited neighbor that is NOT the parent means a second route reached it — genuine cycle evidence."},
         ], "min_points": 2},
        d((3, 2, 4, 3)), requires_ai=True, ordering=2,
        hints=[_h("socratic_question", "The edge A—B is stored as A→B and B→A. When you stand at B, what does B's list say about A?"),
               _h("micro_question", "Was the parent marked visited before or after you entered the current vertex?"),
               _h("light_hint", "The extra information is the vertex you just came from — the parent."),
               _h("targeted_explanation", "(a) Each edge sits in both endpoint lists, so the arrival edge points back at the parent, which was already marked visited on entry. (b) Record where the traversal came from: meeting that parent is the same edge re-read; meeting any OTHER visited vertex is a second route — cycle evidence.")])
    _ex(uid, "cycle_encounter_reasoning", InteractionType.CODE_TRACING,
        "The same recording DFS, but the graph now has one extra edge C—A that closes the triangle "
        "A—B—C. What does it print?\n\n"
        'graph = {"A": ["B", "C"], "B": ["A", "C"], "C": ["B", "A"]}\n'
        "visited = set()\n\n"
        "def dfs(v, came_from):\n"
        "    visited.add(v)\n"
        "    for nbr in graph[v]:\n"
        "        if nbr not in visited:\n"
        "            dfs(nbr, v)\n"
        "        elif nbr == came_from:\n"
        '            print(v, "sees", nbr, "(parent)")\n'
        "        else:\n"
        '            print(v, "sees", nbr, "(not parent)")\n\n'
        'dfs("A", None)\n'
        'print("finished")',
        {"code": "",
         "expected_output": "B sees A (parent)\nC sees B (parent)\nC sees A (not parent)\nA sees C (not parent)\nfinished"},
        d((3, 3, 4, 3)), ordering=3,
        hints=[_h("socratic_question", "After dfs('C','B') returns, control is back inside dfs('A', None) — which neighbor of A is scanned next, and has it become visited in the meantime?"),
               _h("micro_question", "Which meetings happen while C's call is still running — and which only after it returns?"),
               _h("light_hint", "The triangle is closed the moment C sees A; back at the start, A re-reads the same loop from its side."),
               _h("targeted_explanation", "B meets its parent A; C meets its parent B, then sees A — visited and NOT its parent: the cycle, found. Back at A, neighbor C is now visited and not A's came_from: the same loop seen from the other endpoint. A tree can never produce a '(not parent)' line.")])

    # --- Layer 3: parent_aware_traversal ---
    uid = _unit("parent_aware_traversal", "Parent-aware traversal — practice",
                "Record the parent and use it to separate arrival edges from cycle evidence",
                UnitType.PRACTICE, dims={K, E, R})
    _ex(uid, "parent_aware_traversal", InteractionType.CODE_TRACING,
        "This DFS records, for every vertex it enters, the vertex it was entered from. What does "
        "it print?\n\n"
        'graph = {"A": ["B", "D"], "B": ["A", "C"], "C": ["B", "D"], "D": ["A", "C"]}\n'
        "parent = {}\n"
        "visited = set()\n\n"
        "def dfs(v, came_from):\n"
        "    visited.add(v)\n"
        "    parent[v] = came_from\n"
        "    for nbr in graph[v]:\n"
        "        if nbr not in visited:\n"
        "            dfs(nbr, v)\n\n"
        'dfs("A", None)\n'
        'print(parent["B"], parent["C"], parent["D"])',
        {"code": "", "expected_output": "A B C"},
        d((3, 3, 3, 3)), ordering=1,
        hints=[_h("socratic_question", "parent[v] is set the moment the traversal ENTERS v — who entered D, and from where?"),
               _h("micro_question", "Does parent['C'] ever change after it is first set?"),
               _h("light_hint", "A enters B; B enters C; C enters D."),
               _h("targeted_explanation", "Each vertex records the vertex it was entered from: parent = {A: None, B: A, C: B, D: C} → printed 'A B C'. (The edge D—A exists, but D was entered from C, so A is NOT D's parent — that observation is the next exercise's cycle evidence.)")])
    _ex(uid, "parent_aware_traversal", InteractionType.MCQ,
        "That graph is the 4-cycle A—B—C—D—A, and DFS from A produced parent = {A: none, B: A, "
        "C: B, D: C}. The recursion now stands at D and scans D's neighbors [A, C]. What does it "
        "observe — and what should it conclude?",
        *_mcq("", [("a", "A and C are both visited → two cycles exist"),
                   ("b", "C is the parent — normal; A is visited but is NOT D's parent → genuine cycle evidence"),
                   ("c", "Both neighbors are visited, so the traversal must stop with an error"),
                   ("d", "Nothing — visited neighbors are always ignored")], "b",
              "The parent edge (C) is the arrival edge seen from the other side — normal. A is visited but not D's parent: a second route already reached A — cycle evidence.", (3, 3, 4, 3)), ordering=2,
        hints=[_h("socratic_question", "Which of A and C did the traversal pass as came_from when it entered D?"),
               _h("micro_question", "How many routes from A to A does the edge D—A create that do not reuse an edge?"),
               _h("light_hint", "Skip the parent; count every other visited neighbor as evidence."),
               _h("targeted_explanation", "C is D's parent: the D—C edge read backwards — normal. A is visited and not D's parent: the walk A→B→C→D→A returns to its start without reusing an edge — a cycle. Exactly one cycle, found once.")])
    _ex(uid, "parent_aware_traversal", InteractionType.FREE_FORM,
        "A friend removed the parent check from your undirected DFS 'to keep it simple': the code "
        "now reports a cycle the very first time any vertex sees a visited neighbor. On the plain "
        "tree A—B—C, walk through what that code reports and explain why passing the parent into "
        "the recursive call (and ignoring exactly that one neighbor) is the minimal fix.",
        {"reference_points": [
            {"id": "p1", "keywords": ["b", "reports a cycle", "reports", "false alarm", "immediately", "already"],
             "text": "On the tree the code already 'finds a cycle' at B (B sees A visited) — a false alarm."},
            {"id": "p2", "keywords": ["both", "two", "both directions", "twice", "reverse", "other side", "same edge"],
             "text": "Identifies the cause: the undirected edge is stored in both lists, so the arrival edge looks like a visited encounter."},
            {"id": "p3", "keywords": ["parent", "came from", "came_from", "parameter", "pass", "skip", "ignore"],
             "text": "The fix: thread the parent through the calls and skip exactly that one neighbor."},
            {"id": "p4", "keywords": ["only", "one", "exactly", "other", "still", "rest"],
             "text": "The skip is minimal: every OTHER visited neighbor still counts — no cycle evidence is lost."},
         ], "min_points": 2},
        d((3, 2, 4, 3)), requires_ai=True, ordering=3,
        hints=[_h("socratic_question", "At B, which neighbor is already visited — and is that a cycle?"),
               _h("micro_question", "If B skips the visited neighbor it came from, does any other visited neighbor remain at B?"),
               _h("light_hint", "Pass came_from = v into each recursive call and ignore exactly the neighbor equal to it."),
               _h("targeted_explanation", "On the tree: dfs('B','A') sees A visited and (without the check) reports a cycle — wrong, the tree has none. The arrival edge is stored both ways, so this meeting is guaranteed at every vertex. Passing the parent down and skipping exactly that neighbor silences the false alarm while every other visited neighbor still counts: minimal, and no evidence lost.")])

    # --- Layer 3: undirected_cycle_detection ---
    uid = _unit("undirected_cycle_detection", "Undirected cycle detection — practice",
                "Implement DFS and BFS cycle detection; handle disconnected graphs and self-loops",
                UnitType.PRACTICE, dims={E, R})
    _ex(uid, "undirected_cycle_detection", InteractionType.CODE_TRACING,
        "This is the complete detection: DFS with a parent check, plus the outer loop for "
        "disconnected graphs. What does it print?\n\n"
        "graph = [[1], [0], [3, 4], [2, 4], [2, 3], []]\n"
        "visited = [False] * 6\n\n"
        "def dfs(v, parent):\n"
        "    visited[v] = True\n"
        "    for nbr in graph[v]:\n"
        "        if nbr == parent:\n"
        "            continue\n"
        "        if visited[nbr]:\n"
        "            return True\n"
        "        if dfs(nbr, v):\n"
        "            return True\n"
        "    return False\n\n"
        "answer = False\n"
        "for start in range(6):\n"
        "    if not visited[start] and dfs(start, -1):\n"
        "        answer = True\n"
        'print("cycle" if answer else "no cycle")',
        {"code": "", "expected_output": "cycle"},
        d((3, 3, 4, 3)), ordering=1,
        hints=[_h("socratic_question", "The outer loop starts a new dfs at every still-unvisited vertex — which starts actually run?"),
               _h("micro_question", "Inside dfs(4, 3): neighbor 2 — is it visited, and is it 4's parent?"),
               _h("light_hint", "Component {2,3,4} is the triangle 2-3-4-2; vertex 5 is isolated."),
               _h("targeted_explanation", "start=0 covers the tree {0,1}: no cycle. start=2 dives 2→3→4; at 4 the neighbor 2 is visited and NOT the parent (3) → True. start=5 runs on an empty neighbor list → False. Any component finding a cycle decides the answer: 'cycle'.")])
    _ex(uid, "undirected_cycle_detection", InteractionType.CODE_WRITING,
        "Complete the detection below: fill in the three marked lines inside dfs so the function "
        "returns True exactly when the undirected graph contains a cycle. The outer loop is "
        "already written for you. Do not change anything else.",
        {"function_name": "detect_cycle_completed",
         "starter": ("def detect_cycle_completed(graph):\n"
                     "    n = len(graph)\n"
                     "    visited = [False] * n\n"
                     "\n"
                     "    def dfs(v, parent):\n"
                     "        visited[v] = True\n"
                     "        for nbr in graph[v]:\n"
                     "            # line 1: ignore the edge you arrived on\n"
                     "            # line 2: a visited neighbor that is not the parent proves a cycle\n"
                     "            # line 3: otherwise dive into the unvisited neighbor\n"
                     "            pass\n"
                     "        return False\n"
                     "\n"
                     "    for start in range(n):\n"
                     "        if not visited[start] and dfs(start, -1):\n"
                     "            return True\n"
                     "    return False\n"),
         "tests": [{"graph": [[1], [0]], "expected": False},
                   {"graph": [[1, 2], [0, 2], [0, 1]], "expected": True},
                   {"graph": [[1], [0], [3, 4], [2, 4], [2, 3], []], "expected": True},
                   {"graph": [[], [], []], "expected": False}],
         "solution": ("def detect_cycle_completed(graph):\n"
                      "    n = len(graph)\n"
                      "    visited = [False] * n\n"
                      "\n"
                      "    def dfs(v, parent):\n"
                      "        visited[v] = True\n"
                      "        for nbr in graph[v]:\n"
                      "            if nbr == parent:\n"
                      "                continue\n"
                      "            if visited[nbr]:\n"
                      "                return True\n"
                      "            if dfs(nbr, v):\n"
                      "                return True\n"
                      "        return False\n"
                      "\n"
                      "    for start in range(n):\n"
                      "        if not visited[start] and dfs(start, -1):\n"
                      "            return True\n"
                      "    return False\n")},
        d((3, 3, 4, 3)), language="python", ordering=2,
        hints=[_h("socratic_question", "Which single neighbor must never count as cycle evidence — and how do you recognise it inside dfs?"),
               _h("micro_question", "Order matters: what must you check BEFORE treating a visited neighbor as evidence?"),
               _h("light_hint", "Line 1: skip nbr when it equals parent. Line 2: return True when visited[nbr]. Line 3: recurse with dfs(nbr, v) and pass its answer up."),
               _h("targeted_explanation", "Inside the loop: if nbr == parent: continue — the arrival edge; if visited[nbr]: return True — a visited non-parent is the cycle; otherwise if dfs(nbr, v): return True — propagate whatever the deeper call found. The skeleton's outer loop covers disconnected graphs.")])
    _ex(uid, "undirected_cycle_detection", InteractionType.CODE_WRITING,
        "Write `has_cycle_undirected(graph)` for an UNDIRECTED graph given as an adjacency list "
        "(every edge appears in both endpoint lists). Return True if the graph contains any cycle, "
        "False otherwise. The graph may be disconnected and may contain isolated vertices; a "
        "self-loop (a vertex listed in its own neighbors) counts as a cycle.",
        {"function_name": "has_cycle_undirected",
         "starter": "def has_cycle_undirected(graph):\n    # your code here\n",
         "tests": [{"graph": [[1], [0]], "expected": False},
                   {"graph": [[1, 2], [0, 2], [0, 1]], "expected": True},
                   {"graph": [[1], [0, 2], [1], [4], [3], []], "expected": False},
                   {"graph": [[1], [0], [3, 4], [2, 4], [2, 3], []], "expected": True},
                   {"graph": [[], [], []], "expected": False},
                   {"graph": [[0]], "expected": True},
                   {"graph": [[1, 2, 3], [0], [0], [0]], "expected": False}],
         "solution": ("def has_cycle_undirected(graph):\n"
                      "    n = len(graph)\n"
                      "    visited = [False] * n\n"
                      "\n"
                      "    def dfs(v, parent):\n"
                      "        visited[v] = True\n"
                      "        for nbr in graph[v]:\n"
                      "            if nbr == parent:\n"
                      "                continue\n"
                      "            if visited[nbr]:\n"
                      "                return True\n"
                      "            if dfs(nbr, v):\n"
                      "                return True\n"
                      "        return False\n"
                      "\n"
                      "    for start in range(n):\n"
                      "        if not visited[start]:\n"
                      "            if dfs(start, -1):\n"
                      "                return True\n"
                      "    return False\n")},
        d((4, 4, 4, 4)), language="python", ordering=3,
        hints=[_h("socratic_question", "Your dfs from the completion already answers 'does THIS component have a cycle?' — what is missing for the whole graph?"),
               _h("micro_question", "For the self-loop [[0]]: is the neighbor 0 visited when it is scanned, and is it the parent (-1)?"),
               _h("light_hint", "dfs(v, parent) with visited marked on entry, parent skipped, visited non-parent → True; then an outer loop over all unvisited starts."),
               _h("targeted_explanation", "Recursive dfs with the parent parameter: skip the parent, report a visited non-parent, recurse otherwise. Wrap it in the outer loop 'for start, if not visited, dfs(start, -1)' so every component is checked. The self-loop works with no extra code: the vertex is visited and not its own parent. Still O(V+E).")])
    _ex(uid, "undirected_cycle_detection", InteractionType.CODE_WRITING,
        "Translate the same invariant to BFS: the queue carries (vertex, parent) PAIRS, and while "
        "scanning a dequeued vertex's neighbors you apply the identical test — skip the parent, "
        "and a visited non-parent neighbor proves a cycle. Mark neighbors visited when ENQUEUING "
        "them (the BFS convention), and remember the graph may be disconnected.",
        {"function_name": "has_cycle_bfs",
         "starter": "from collections import deque\n\ndef has_cycle_bfs(graph):\n    # your code here\n",
         "tests": [{"graph": [[1], [0]], "expected": False},
                   {"graph": [[1, 2], [0, 2], [0, 1]], "expected": True},
                   {"graph": [[1], [0], [3, 4], [2, 4], [2, 3], []], "expected": True},
                   {"graph": [[], [], []], "expected": False},
                   {"graph": [[0]], "expected": True},
                   {"graph": [[1, 2, 3], [0], [0], [0]], "expected": False}],
         "solution": ("from collections import deque\n"
                      "\n"
                      "def has_cycle_bfs(graph):\n"
                      "    n = len(graph)\n"
                      "    visited = [False] * n\n"
                      "    for start in range(n):\n"
                      "        if visited[start]:\n"
                      "            continue\n"
                      "        visited[start] = True\n"
                      "        queue = deque([(start, -1)])\n"
                      "        while queue:\n"
                      "            v, parent = queue.popleft()\n"
                      "            for nbr in graph[v]:\n"
                      "                if nbr == parent:\n"
                      "                    continue\n"
                      "                if visited[nbr]:\n"
                      "                    return True\n"
                      "                visited[nbr] = True\n"
                      "                queue.append((nbr, v))\n"
                      "    return False\n")},
        d((4, 4, 4, 4)), language="python", ordering=4,
        hints=[_h("socratic_question", "In the DFS version, where does each recursive call learn its parent from — and where does a BFS vertex learn it instead?"),
               _h("micro_question", "Why must a neighbor be marked visited at enqueue time and not at dequeue time here?"),
               _h("light_hint", "Seed the queue with (start, -1); on discovery enqueue (nbr, v); on scan, skip nbr == parent and report any other visited neighbor."),
               _h("targeted_explanation", "BFS with (vertex, parent) queue entries: mark the start visited, enqueue (start, -1); per dequeued v, skip the parent, return True on any other visited neighbor, otherwise mark-and-enqueue (nbr, v). Enqueue-time marking keeps every vertex in the queue once — a dequeue-time mark could fake cycle evidence. Outer loop over unvisited starts; still O(V+E).")])
    uid = _unit("undirected_cycle_detection", "Undirected cycle detection — apply",
                "Recognize an undirected cycle-check situation in an unfamiliar context",
                UnitType.APPLY, dims={T, R})
    _ex(uid, "undirected_cycle_detection", InteractionType.FREE_FORM,
        "A teammate hands you the office LAN map: 12 computers and a list of which pairs are "
        "directly cabled. A cable is a physical link with no direction. The cabling contractor "
        "promised 'no redundant links, ever', and she asks you to check the map for any redundant "
        "loop. Which traversal do you use, what state do you carry during it, which single "
        "observation flags a redundant loop, and what must you do about the possibility that the "
        "LAN is split into separate sections?",
        {"reference_points": [
            {"id": "p1", "keywords": ["undirected", "both", "mutual", "two-way", "bidirectional", "no direction"],
             "text": "Recognizes the graph as undirected — cables work both ways, so both endpoint lists hold the edge."},
            {"id": "p2", "keywords": ["dfs", "bfs", "traversal", "parent", "came from", "came_from"],
             "text": "Runs DFS (or BFS) while carrying the parent / where it came from."},
            {"id": "p3", "keywords": ["visited", "not the parent", "non-parent", "not parent"],
             "text": "A visited neighbor that is not the parent is the redundant-loop evidence."},
            {"id": "p4", "keywords": ["outer", "loop", "every", "unvisited", "component", "section", "disconnected", "each"],
             "text": "Loops over all unvisited computers — separate sections each need their own traversal."},
         ], "min_points": 3},
        d((4, 4, 4, 4)), requires_ai=True, ordering=5,
        hints=[_h("socratic_question", "Is a cable one-way? What does that make the adjacency list look like — and which trap does that create for a plain visited check?"),
               _h("micro_question", "When the scan meets the computer the traversal just came from, is that a loop?"),
               _h("light_hint", "DFS with a parent parameter; a visited non-parent neighbor is the redundant loop; run it from every unvisited computer."),
               _h("targeted_explanation", "Model computers as vertices, cables as undirected edges. Run DFS carrying (vertex, parent): skip the parent, and any OTHER visited neighbor proves a redundant loop. Because the LAN may be split into sections, wrap it in the outer loop over unvisited vertices — a loop in ANY section fails the check. Still O(V+E); BFS with (vertex, parent) entries works identically.")])


def _build_variations():
    """A second, differently-angled exercise for every skill that would otherwise repeat
    the identical question twice (mastery requires 2 evidence pieces — spec 03 §6). The
    engine's variation step then always serves a NEW question."""
    VARIATIONS = {
        "graph_definition": (
            "Which of these is BEST modeled as a graph?",
            _mcq("", [("a", "A delivery network: cities as points, roads as connections between them"),
                       ("b", "A shopping list of items to buy"),
                       ("c", "A single phone number"),
                       ("d", "An alphabetical list of student names")], "a",
                  "Entities plus meaningful connections = graph territory.", (1, 1, 1, 1))),
        "vertices_edges": (
            "In a course-prerequisite diagram (CS101 requires CS100), what are the vertices and edges?",
            _mcq("", [("a", "Vertices = courses; edges = prerequisite relations between them"),
                       ("b", "Vertices = prerequisites; edges = courses"),
                       ("c", "Vertices = students; edges = grades"),
                       ("d", "Vertices = semesters; edges = credits")], "a",
                  "The entities are courses; the 'requires' relation connects them.", (1, 1, 1, 1))),
        "directed_vs_undirected": (
            "On Facebook, friendship is mutual: if A is friends with B, B is friends with A. Which model fits?",
            _mcq("", [("a", "Directed graph"), ("b", "Undirected graph"),
                       ("c", "Weighted graph"), ("d", "Multigraph with loops")], "b",
                  "Mutual relationships need no arrow direction: undirected.", (2, 1, 2, 2))),
        "weighted_vs_unweighted": (
            "Which graph treats EVERY connection as costing exactly one step?",
            _mcq("", [("a", "A weighted graph with equal weights"), ("b", "An unweighted graph"),
                       ("c", "A directed graph"), ("d", "A disconnected graph")], "b",
                  "Unweighted = every edge is one uniform step; weights attach per-edge numbers.", (1, 1, 1, 2))),
        "path": (
            "Edges: A-B, B-C, D-E. Is there a path from A to E?",
            _mcq("", [("a", "Yes, via B and C"), ("b", "Yes, directly"),
                       ("c", "No — C and D are not connected"), ("d", "Only if the graph is weighted")], "c",
                  "C and D have no edge between them, so the chain breaks: A and E are in different components.", (2, 1, 2, 2))),
        "cycle": (
            "A tree has edges A-B and B-C. Adding which single edge creates a cycle?",
            _mcq("", [("a", "A-C"), ("b", "A-D"), ("c", "B-D"), ("d", "None can")], "a",
                  "A → B → C → A returns to its start: a cycle. Any edge touching a new vertex D stays acyclic.", (2, 1, 2, 2))),
        "connectedness": (
            "Edges: A-B, B-C and X-Y. The graph has two separate pieces. How many connected components does it have?",
            _mcq("", [("a", "1"), ("b", "2"), ("c", "3"), ("d", "5")], "b",
                  "{A,B,C} and {X,Y} are each connected with no path between them: 2 components.", (2, 1, 2, 2))),
        "edge_list": (
            "When is an edge list the RIGHT representation choice?",
            _mcq("", [("a", "When you constantly ask 'who are the neighbors of X?'"),
                       ("b", "When you receive and process edges one by one (e.g. a plain input file)"),
                       ("c", "When you need O(1) edge lookups"),
                       ("d", "Never — it is always wrong")], "b",
                  "Edge lists shine as a compact input format; neighbor queries need an adjacency list instead.", (1, 2, 1, 1))),
        "why_traversal": (
            "Which question can plain BFS/DFS traversal NOT answer on its own?",
            _mcq("", [("a", "Which vertices are reachable from S?"),
                       ("b", "How many vertices are in S's component?"),
                       ("c", "The cheapest route when roads have different tolls (weighted costs)"),
                       ("d", "Is there any path from S to T?")], "c",
                  "Weighted shortest paths need more than plain traversal (that is Dijkstra, a later version).", (2, 1, 2, 2))),
        "traversal_state": (
            "Which three pieces of state does every BFS/DFS carry while running?",
            _mcq("", [("a", "The current vertex, the visited set, and the frontier (queue/stack)"),
                       ("b", "The sorted vertex list, the edge weights, and the matrix"),
                       ("c", "Only the answer"),
                       ("d", "The adjacency matrix, the degree table, and the cycle count")], "a",
                  "Current + visited + frontier is the complete working memory of a traversal.", (2, 2, 2, 2))),
        "bfs_intuition": (
            "Star graph: A→[B,C,D,E,F], all others→[]. BFS starts at A. What is the visit order?",
            _mcq("", [("a", "A, then B C D E F in listed order"),
                       ("b", "F E D C B A"), ("c", "B D F A C E"), ("d", "A only")], "a",
                  "Level 0 = A; every other vertex is level 1 and leaves the queue in listed order.", (3, 1, 3, 3))),
        "dfs_intuition": (
            "graph: A→[B,C], B→[D], C→[], D→[]. Recursive DFS from A (listed neighbor order) visits...",
            _mcq("", [("a", "A, B, D, C — it dives B's branch to D before touching C"),
                       ("b", "A, B, C, D — it sweeps level by level"),
                       ("c", "A, C, B, D"), ("d", "D, B, C, A")], "a",
                  "Depth-first: finish the whole B→D route before backtracking to C.", (3, 1, 3, 3))),

        # Layer 1 variations
        "traversal_boundary": (
            "Graph: 1-2 and 3-4 and 5 (three components). DFS from 1 visits 1,2 and stops. "
            "What does the visited set represent?",
            _mcq("", [("a", "All vertices in the graph"),
                       ("b", "Exactly the component containing vertex 1"),
                       ("c", "Vertices 1 and 2 only, by coincidence"),
                       ("d", "The vertices in level order")], "b",
                  "One traversal = one component. DFS from 1 visits exactly {1,2}.", (3, 2, 3, 3))),
        "component_discovery": (
            "After BFS from A visits {A,B,C}, vertex D is unvisited. What does this mean?",
            _mcq("", [("a", "BFS failed to reach D"),
                       ("b", "D is in a different component — start a new traversal from D"),
                       ("c", "The graph is disconnected so BFS cannot continue"),
                       ("d", "D is an isolated vertex with no edges")], "b",
                  "Unvisited after traversal = different component. Start a new traversal from D.", (3, 3, 3, 3))),
        "component_enumeration": (
            "The outer loop `for v in range(n): if not visited[v]: bfs(v)` counts components. "
            "Why is it O(V+E) and not O(V(V+E))?",
            _mcq("", [("a", "Because V is small"),
                       ("b", "The visited set prevents any vertex from being processed twice across all BFS runs"),
                       ("c", "Because BFS is fast"),
                       ("d", "It is actually O(V(V+E))")], "b",
                  "Each vertex/edge is processed at most once total — visited set prevents re-processing.", (3, 4, 4, 4))),
        # Layer 2 variations
        "bfs_distance": (
            "After a BFS run finishes, distance[v] is still -1. In OUR implementation, what does that mean?",
            _mcq("", [("a", "v is at distance -1, one step before the source"),
                       ("b", "v is unreachable from the start — our convention for 'no path exists' (not mathematical infinity)"),
                       ("c", "The BFS had a bug — distances are never negative"),
                       ("d", "v sits in the queue but has not been processed")], "b",
                  "-1 is the chosen implementation convention: it doubles as 'not yet discovered' during the run and as 'unreachable' after it.", (3, 2, 4, 3))),
        "path_reconstruction": (
            "Two equally short routes from S to T exist, and adjacency order makes BFS discover T via the second one. What does BFS's parent array contain?",
            _mcq("", [("a", "Both routes — BFS stores all shortest paths"),
                       ("b", "One valid shortest path: the route along which T was first discovered"),
                       ("c", "The longer route — parents record the last discovery"),
                       ("d", "No route — equal distances cancel out")], "b",
                  "First discovery fixes the parent permanently: BFS returns one valid shortest path, and adjacency order decides which one.", (3, 3, 4, 4))),
        # Layer 3 variations
        "cycle_encounter_reasoning": (
            "Tree A—B—C as an undirected adjacency list, DFS starting at A. When the walk reaches C, "
            "C finds B already visited. Is this a cycle?",
            _mcq("", [("a", "Yes — B is visited, so a cycle exists"),
                       ("b", "No — B is C's parent: this is the arrival edge seen from the other side"),
                       ("c", "Only if C has another neighbor besides B"),
                       ("d", "DFS cannot be used on trees")], "b",
                  "C was entered from B, so B in C's list is the same edge C—B stored in reverse — normal on every undirected graph, trees included.", (3, 2, 3, 2))),
        "parent_aware_traversal": (
            "What does the parent parameter add to plain recursive DFS on an undirected graph?",
            _mcq("", [("a", "It makes DFS run faster"),
                       ("b", "It identifies the arrival edge so the traversal can ignore it — and treat every OTHER visited neighbor as cycle evidence"),
                       ("c", "It replaces the visited set entirely"),
                       ("d", "It sorts the neighbors into visit order")], "b",
                  "The parent names the edge the traversal arrived on; skipping exactly that one neighbor turns raw visited-encounters into meaningful cycle evidence.", (3, 3, 4, 3))),
        "undirected_cycle_detection": (
            "Vertex 5 is isolated (empty neighbor list) in a graph where DFS-with-parent already "
            "found no cycle in the components it covered. What does the outer loop conclude about 5?",
            _mcq("", [("a", "A cycle exists at 5"),
                       ("b", "5 must be skipped — isolated vertices crash DFS"),
                       ("c", "5 is its own component and trivially cycle-free: dfs(5, -1) just returns False"),
                       ("d", "The graph must be re-modeled before it can be checked")], "c",
                  "An isolated vertex is a one-vertex component with no edges, hence no cycle; the outer loop visits it, dfs returns False immediately.", (3, 3, 4, 3))),
    }
    for skill_id, (prompt, (payload, difficulty)) in VARIATIONS.items():
        teach = [u for u in UNITS if u.skill_id == skill_id and u.unit_type == UnitType.TEACH]
        if not teach:
            continue
        _ex(teach[0].id, skill_id, InteractionType.MCQ, prompt, payload, difficulty, ordering=2)


def _apply_amendments():
    """Review amendments: modules (RC-07), skill descriptions + evidence requirements
    (RC-08/RC-09), activity roles/scopes (RC-06), optional explicit-stack DFS."""
    modules = {
        "Module A - Graph Mental Model": ["graph_definition", "vertices_edges", "adjacency",
            "directed_vs_undirected", "weighted_vs_unweighted", "degree", "path", "cycle", "connectedness"],
        "Module B - Graph Representation": ["edge_list", "adjacency_matrix", "adjacency_list",
            "conversion_between_representations", "choosing_representation"],
        "Module C - Traversal Fundamentals": ["why_traversal", "traversal_state", "visited_state",
            "traversal_order", "manual_tracing"],
        "Module D - BFS": ["bfs_intuition", "queue_mechanism", "bfs_visited_handling",
            "bfs_manual_tracing", "bfs_implementation", "bfs_time_complexity", "bfs_space_complexity"],
        "Module E - DFS": ["dfs_intuition", "recursion_mechanism", "dfs_visited_handling",
            "dfs_manual_tracing", "dfs_implementation", "dfs_time_complexity", "dfs_space_complexity",
            "explicit_stack_dfs"],
        "Module F - Integration & Application": ["bfs_vs_dfs", "recognizing_traversal",
            "traversal_application", "v0_readiness",
            "traversal_boundary", "component_discovery", "component_enumeration",
            "bfs_distance", "path_reconstruction",
            "cycle_encounter_reasoning", "parent_aware_traversal", "undirected_cycle_detection"],
    }
    descriptions = {
        "graph_definition": "Understand a graph as a model of entities and relationships.",
        "vertices_edges": "Identify vertices and edges in a modeled situation.",
        "adjacency": "Determine which vertices are direct neighbors of a vertex.",
        "directed_vs_undirected": "Distinguish one-way relationships from mutual ones.",
        "weighted_vs_unweighted": "Recognize when edges carry costs and what unweighted means.",
        "degree": "Count the edges attached to a vertex.",
        "path": "Determine whether a route of existing edges connects two vertices.",
        "cycle": "Recognize routes that return to their start without reusing edges.",
        "connectedness": "Decide whether every vertex can reach every other.",
        "edge_list": "Represent a graph as a list of edge pairs and know when that is enough.",
        "adjacency_matrix": "Represent a graph as a V×V grid and read neighbor rows.",
        "adjacency_list": "Represent a graph as per-vertex neighbor lists and trace their construction.",
        "conversion_between_representations": "Rebuild one representation from another.",
        "choosing_representation": "Justify a representation choice from operations and graph shape.",
        "why_traversal": "Explain what systematic exploration of a graph is for.",
        "traversal_state": "Track current vertex, visited set, and frontier during traversal.",
        "visited_state": "Explain and apply the visited mechanism that prevents re-processing and infinite loops.",
        "traversal_order": "Predict how queue/stack choice changes visit order.",
        "manual_tracing": "Trace traversal state evolution by hand, step by step.",
        "bfs_intuition": "Explain BFS's level-by-level expansion and its shortest-by-edges guarantee.",
        "queue_mechanism": "Apply FIFO queue mechanics and explain why BFS needs them.",
        "bfs_visited_handling": "Apply mark-on-enqueue and explain duplicate prevention.",
        "bfs_manual_tracing": "Trace BFS on a concrete graph, including queue states.",
        "bfs_implementation": "Write plain BFS from an adjacency list without assistance.",
        "bfs_time_complexity": "Derive and justify BFS's O(V+E) time bound.",
        "bfs_space_complexity": "Derive and justify BFS's O(V) space bound.",
        "dfs_intuition": "Explain DFS's depth-first exploration and backtracking.",
        "recursion_mechanism": "Predict recursive call flow and identify base cases.",
        "dfs_visited_handling": "Apply mark-on-entry and explain its role in termination.",
        "dfs_manual_tracing": "Trace recursive DFS on a concrete graph, including backtracking.",
        "dfs_implementation": "Write plain recursive DFS without assistance.",
        "dfs_time_complexity": "Derive and justify DFS's O(V+E) time bound.",
        "dfs_space_complexity": "Derive and justify DFS's O(V) recursion-depth bound.",
        "explicit_stack_dfs": "Trace and explain the explicit-stack variant of DFS (optional extension).",
        "bfs_vs_dfs": "Choose between BFS and DFS and justify the choice.",
        "recognizing_traversal": "Recognize problem situations where plain traversal applies.",
        "traversal_application": "Apply traversal independently to count reachable vertices.",
        "v0_readiness": "Demonstrate the full V0 outcome list independently.",
        # Layer 1 descriptions
        "traversal_boundary": "Understand that one traversal explores exactly one connected component.",
        "component_discovery": "Recognize that an unvisited vertex after traversal signals a new component.",
        "component_enumeration": "Implement the outer loop to count and label all connected components.",
        # Layer 2 descriptions
        "bfs_distance": "Read BFS levels as distances, track a distance array, and treat -1 as unreachable.",
        "path_reconstruction": "Track parents during BFS and reconstruct the actual shortest path between two vertices.",
        # Layer 3 descriptions
        "cycle_encounter_reasoning": "Interpret what traversal observes when it meets a visited neighbor in an undirected graph.",
        "parent_aware_traversal": "Distinguish the parent edge from genuine cycle evidence while traversing an undirected graph.",
        "undirected_cycle_detection": "Implement undirected cycle detection with DFS and BFS, handle disconnected graphs, and recognize the situation independently.",
    }
    evidence = {
        "degree": {EvidenceType.RECOGNITION, EvidenceType.CONSTRUCTION},
        "adjacency_matrix": {EvidenceType.RECOGNITION, EvidenceType.TRACE},
        "adjacency_list": {EvidenceType.RECOGNITION, EvidenceType.TRACE},
        "choosing_representation": {EvidenceType.RECOGNITION, EvidenceType.EXPLANATION},
        "visited_state": {EvidenceType.RECOGNITION, EvidenceType.EXPLANATION},
        "traversal_order": {EvidenceType.RECOGNITION, EvidenceType.TRACE},
        "manual_tracing": {EvidenceType.RECOGNITION, EvidenceType.EXPLANATION},
        "queue_mechanism": {EvidenceType.RECOGNITION, EvidenceType.TRACE},
        "bfs_visited_handling": {EvidenceType.RECOGNITION, EvidenceType.TRACE},
        "bfs_manual_tracing": {EvidenceType.RECOGNITION, EvidenceType.TRACE},
        "bfs_implementation": {EvidenceType.RECOGNITION, EvidenceType.IMPLEMENTATION},
        "bfs_time_complexity": {EvidenceType.RECOGNITION, EvidenceType.EXPLANATION},
        "bfs_space_complexity": {EvidenceType.RECOGNITION, EvidenceType.EXPLANATION},
        "recursion_mechanism": {EvidenceType.RECOGNITION, EvidenceType.TRACE},
        "dfs_visited_handling": {EvidenceType.RECOGNITION, EvidenceType.TRACE},
        "dfs_manual_tracing": {EvidenceType.RECOGNITION, EvidenceType.TRACE},
        "dfs_implementation": {EvidenceType.RECOGNITION, EvidenceType.IMPLEMENTATION},
        "dfs_time_complexity": {EvidenceType.RECOGNITION, EvidenceType.EXPLANATION},
        "dfs_space_complexity": {EvidenceType.RECOGNITION, EvidenceType.EXPLANATION},
        "explicit_stack_dfs": {EvidenceType.RECOGNITION, EvidenceType.TRACE},
        "bfs_vs_dfs": {EvidenceType.RECOGNITION, EvidenceType.EXPLANATION},
        "recognizing_traversal": {EvidenceType.RECOGNITION, EvidenceType.EXPLANATION},
        "traversal_application": {EvidenceType.RECOGNITION, EvidenceType.APPLICATION},
        "v0_readiness": {EvidenceType.RECOGNITION, EvidenceType.APPLICATION,
                         EvidenceType.EXPLANATION},
        # Layer 1 evidence requirements
        "traversal_boundary": {EvidenceType.RECOGNITION, EvidenceType.EXPLANATION},
        "component_discovery": {EvidenceType.RECOGNITION, EvidenceType.TRACE, EvidenceType.EXPLANATION},
        "component_enumeration": {EvidenceType.RECOGNITION, EvidenceType.IMPLEMENTATION, EvidenceType.APPLICATION},
        # Layer 2 evidence requirements
        "bfs_distance": {EvidenceType.RECOGNITION, EvidenceType.TRACE, EvidenceType.IMPLEMENTATION},
        "path_reconstruction": {EvidenceType.RECOGNITION, EvidenceType.TRACE, EvidenceType.IMPLEMENTATION},
        # Layer 3 evidence requirements
        "cycle_encounter_reasoning": {EvidenceType.RECOGNITION, EvidenceType.TRACE, EvidenceType.EXPLANATION},
        "parent_aware_traversal": {EvidenceType.RECOGNITION, EvidenceType.TRACE, EvidenceType.EXPLANATION},
        "undirected_cycle_detection": {EvidenceType.RECOGNITION, EvidenceType.TRACE,
                                       EvidenceType.IMPLEMENTATION, EvidenceType.APPLICATION},
    }
    module_order = list(modules.keys())
    skill_order = {sid: i for i, m in enumerate(module_order) for sid in modules[m]}
    for s in SKILLS:
        s.module = next((m for m, ids in modules.items() if s.id in ids), s.section)
        s.section = s.module
        s.description = descriptions.get(s.id, "")
        s.evidence_requirements = frozenset(evidence.get(s.id, {EvidenceType.RECOGNITION}))
        s.is_optional = s.id == "explicit_stack_dfs"
    for i, s in enumerate(sorted(SKILLS, key=lambda s: (skill_order.get(s.id, 99), s.ordering)), 1):
        s.ordering = i
    role_by_type = {
        InteractionType.MCQ: ActivityRole.RECOGNITION,
        InteractionType.FREE_FORM: ActivityRole.EXPLANATION,
        InteractionType.OUTPUT_PREDICTION: ActivityRole.TRACE,
        InteractionType.CODE_TRACING: ActivityRole.TRACE,
        InteractionType.GRAPH_CONSTRUCTION: ActivityRole.CONSTRUCTION,
        InteractionType.CODE_WRITING: ActivityRole.IMPLEMENTATION,
        InteractionType.COMPLEXITY_QUESTION: ActivityRole.EXPLANATION,
        InteractionType.REFLECTION: ActivityRole.REFLECTION,
    }
    role_overrides = {
        ("traversal_application", InteractionType.CODE_WRITING): ActivityRole.APPLICATION,
        ("v0_readiness", InteractionType.CODE_WRITING): ActivityRole.APPLICATION,
        ("component_enumeration", InteractionType.FREE_FORM): ActivityRole.APPLICATION,
        ("path_reconstruction", InteractionType.FREE_FORM): ActivityRole.APPLICATION,
        ("undirected_cycle_detection", InteractionType.FREE_FORM): ActivityRole.APPLICATION,
    }
    problem_keys = {("bfs_implementation", InteractionType.CODE_WRITING),
                    ("dfs_implementation", InteractionType.CODE_WRITING),
                    ("traversal_application", InteractionType.CODE_WRITING),
                    ("v0_readiness", InteractionType.CODE_WRITING),
                    ("component_enumeration", InteractionType.CODE_WRITING),
                    ("bfs_distance", InteractionType.CODE_WRITING),
                    ("path_reconstruction", InteractionType.CODE_WRITING),
                    ("undirected_cycle_detection", InteractionType.CODE_WRITING)}
    capabilities = {
        ("bfs_implementation", InteractionType.CODE_WRITING): {EvidenceType.TRACE, EvidenceType.RECOGNITION},
        ("dfs_implementation", InteractionType.CODE_WRITING): {EvidenceType.TRACE, EvidenceType.RECOGNITION},
        ("traversal_application", InteractionType.CODE_WRITING): {EvidenceType.IMPLEMENTATION, EvidenceType.RECOGNITION},
        ("v0_readiness", InteractionType.CODE_WRITING): {EvidenceType.IMPLEMENTATION, EvidenceType.EXPLANATION},
        ("component_enumeration", InteractionType.CODE_WRITING): {EvidenceType.IMPLEMENTATION, EvidenceType.APPLICATION},
        # IMPLEMENTATION is demonstrated by bfs_implementation's code-writing (prerequisite
        # closure); TRACE by each skill's own tracing activities
        ("bfs_distance", InteractionType.CODE_WRITING): {EvidenceType.IMPLEMENTATION, EvidenceType.TRACE},
        ("path_reconstruction", InteractionType.CODE_WRITING): {EvidenceType.IMPLEMENTATION, EvidenceType.TRACE},
        # IMPLEMENTATION via dfs_implementation's code-writing (prerequisite closure);
        # TRACE by this skill's own tracing activities
        ("undirected_cycle_detection", InteractionType.CODE_WRITING): {EvidenceType.IMPLEMENTATION, EvidenceType.TRACE},
    }
    for e in EXERCISES:
        role = role_by_type[e.interaction_type]
        override = role_overrides.get((e.skill_id, e.interaction_type))
        if override:
            role = override
        e.role = role
        e.scope = ActivityScope.PROBLEM if (e.skill_id, e.interaction_type) in problem_keys \
            else ActivityScope.MICRO
        e.required_capabilities = frozenset(capabilities.get((e.skill_id, e.interaction_type), set()))


_build()
_apply_amendments()
