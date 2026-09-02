# V0.1 Curriculum & Skill Graph (revised)

Status: Implementation baseline V0.1 — modules per review RC-07, amended curriculum (38 skills).

## Modules

**Module A — Graph Mental Model:** graph_definition, vertices_edges, adjacency (new), directed_vs_undirected, weighted_vs_unweighted (conceptual recognition only — shortest-path is out of scope), degree, path, cycle, connectedness.

**Module B — Graph Representation:** edge_list, adjacency_matrix, adjacency_list, conversion_between_representations (new), choosing_representation.

**Module C — Traversal Fundamentals:** why_traversal, traversal_state, visited_state, traversal_order, manual_tracing.

**Module D — BFS:** bfs_intuition, queue_mechanism, bfs_visited_handling, bfs_manual_tracing, bfs_implementation, bfs_time_complexity, bfs_space_complexity.

**Module E — DFS:** dfs_intuition, recursion_mechanism, dfs_visited_handling, dfs_manual_tracing, dfs_implementation, dfs_time_complexity, dfs_space_complexity, explicit_stack_dfs (**optional** — served only when every core skill is mastered).

**Module F — Integration & Application:** bfs_vs_dfs, recognizing_traversal, traversal_application, v0_readiness (boundary).

## Per-skill definition

Each skill carries: id, title, module, description, prerequisites (core/supporting), evidence requirements (the activity roles/types that must be demonstrated), 4-axis complexity descriptors, remediation policy (engine ladder), and dependents (`Curriculum.dependents()`).

## Evidence requirements (highlights)

- Implementation skills (bfs/dfs_implementation): RECOGNITION + IMPLEMENTATION.
- Tracing skills: RECOGNITION + TRACE.
- Concept skills: RECOGNITION (single-check) or RECOGNITION + EXPLANATION.
- traversal_application: RECOGNITION + IMPLEMENTATION + APPLICATION.
- v0_readiness: RECOGNITION + IMPLEMENTATION + APPLICATION + EXPLANATION.

## Exclusions (unchanged)

Dijkstra, Bellman-Ford, Floyd-Warshall, MST, DSU, topological sort, SCC, bridges, articulation points, advanced cycle detection. The curriculum validator rejects any skill depending on the `v0_readiness` boundary.
