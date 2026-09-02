"""Builtin AI provider — the offline semantic engine authored by AutoClaw.

Instead of calling an external LLM API at runtime, the semantic judgments V0 needs
(evaluation rubrics, misconception patterns, progressive hint ladders, micro-question
and remediation generators, targeted explanations) are authored here at build time.
Deterministic, schema-valid, zero network. This is the default provider so the whole
system runs without any API key; the OpenAI-compatible provider remains available
for backward compatibility (config AI_PROVIDER=openai|hybrid).
"""
from __future__ import annotations

import ast
import json
import re
from typing import Any, Optional

from . import code_runner
from .interface import AITutor
from .schemas import (
    EvaluationResult, GeneratedExercise, HintResult, normalize_hint_level,
)
from ..domain.models import Exercise, InteractionType

PROMPT_VERSION = "builtin-ac-v0-1"

# --------------------------------------------------------------------------
# text helpers
# --------------------------------------------------------------------------
_WS = re.compile(r"\s+")


def norm_text(value: str) -> str:
    return _WS.sub(" ", (value or "").strip()).lower()


def norm_output(value: str) -> str:
    """Normalize printed output: collapse whitespace, strip quotes/brackets noise."""
    lines = [ln.strip() for ln in (value or "").strip().splitlines() if ln.strip()]
    cleaned = []
    for ln in lines:
        ln = ln.replace("'", "").replace('"', "")
        ln = re.sub(r"\s*,\s*", ",", ln)
        ln = re.sub(r"\s+", " ", ln)
        ln = ln.strip("[]() ")
        cleaned.append(ln)
    return " | ".join(cleaned).lower()


def norm_bigoh(value: str) -> str:
    v = norm_text(value)
    v = v.replace(" ", "")
    v = v.replace("n", "v").replace("m", "e")
    v = v.replace("²", "^2").replace("*", "")
    return v


# --------------------------------------------------------------------------
# misconception pattern library (authored): (regex, misconception, missing_skill)
# applied to free-form / explanation-style responses
# --------------------------------------------------------------------------
MISCONCEPTION_PATTERNS: list[tuple[str, str, str]] = [
    (r"\bvisit(ed)?\b[^.]{0,40}\b(process|dequeue|pop)\b|\bprocess[^.]{0,30}\bvisit",
     "confuses visited with fully processed", "visited_state"),
    (r"\bstack\b[^.]{0,60}\bbfs\b|\bbfs\b[^.]{0,60}\bstack\b",
     "pairs BFS with a stack instead of a queue", "queue_mechanism"),
    (r"\bqueue\b[^.]{0,60}\bdfs\b|\bdfs\b[^.]{0,60}\bqueue\b",
     "pairs DFS with a queue instead of a stack/recursion", "recursion_mechanism"),
    (r"\bvisited\b[^.]{0,40}\b(when dequeue|after dequeu|dequeued)\b",
     "marks visited too late (at dequeue)", "bfs_visited_handling"),
    (r"\bo\(v ?\* ?e\)|\bo\(v2\)|\bo\(v\^2\)\b[^.]{0,30}\blist\b",
     "claims O(V^2) for adjacency-list traversal", "bfs_time_complexity"),
    (r"\bmatrix\b[^.]{0,40}\bo\(v ?\+ ?e\)",
     "claims O(V+E) for adjacency-matrix neighbor scans", "bfs_time_complexity"),
    (r"\bdegree\b[^.]{0,40}\b(number of vertices|size of graph)\b",
     "confuses degree with vertex count", "degree"),
    (r"\bcycle\b[^.]{0,50}\bany loop\b|\bany loop\b[^.]{0,50}\bcycle\b",
     "equates any repetition with a graph cycle", "cycle"),
    (r"\bshortest\b[^.]{0,40}\bdfs\b|\bdfs\b[^.]{0,40}\bshortest\b",
     "believes DFS finds shortest paths", "bfs_vs_dfs"),
    (r"\brecursion\b[^.]{0,50}\bwithout base case is fine\b",
     "missing base-case awareness", "recursion_mechanism"),
]

SOLUTION_COPY_THRESHOLD = 0.85


def _looks_like_copied(response: str, solution: str | None) -> bool:
    if not solution:
        return False
    a = re.sub(r"\s+", " ", response.strip().lower())
    b = re.sub(r"\s+", " ", solution.strip().lower())
    if not b:
        return False
    if b in a:
        return True
    b_tokens = [t for t in re.split(r"\W+", b) if t]
    a_tokens = set(re.split(r"\W+", a))
    if len(b_tokens) < 6:
        return False
    hit = sum(1 for t in b_tokens if t in a_tokens) / len(b_tokens)
    return hit >= SOLUTION_COPY_THRESHOLD


# --------------------------------------------------------------------------
# per-type deterministic graders
# --------------------------------------------------------------------------
def grade_mcq(exercise: Exercise, response: str) -> tuple[bool, float, str]:
    payload = exercise.payload
    answer = norm_text(response)
    chosen = None
    m = re.match(r"^\s*([a-d])\b", answer)
    if m:
        chosen = m.group(1)
    else:
        for choice in payload["choices"]:
            if norm_text(choice["text"]) == answer:
                chosen = choice["id"]
                break
    correct = chosen == payload["answer_id"]
    explanation = payload.get("explanation", "")
    if correct:
        return True, 1.0, f"Correct. {explanation}".strip()
    return False, 0.0, f"Not quite. {explanation}".strip()


def grade_prediction(exercise: Exercise, response: str) -> tuple[bool | None, float, str, Optional[str]]:
    expected = norm_output(exercise.payload["expected_output"])
    got = norm_output(response)
    if got == expected:
        return True, 1.0, "Exactly right — the trace matches.", None
    exp_tokens = [t for t in expected.replace("|", " ").split() if t]
    got_tokens = [t for t in got.replace("|", " ").split() if t]
    if exp_tokens and got_tokens and got_tokens == exp_tokens[::-1] and len(exp_tokens) > 2:
        return False, 0.25, ("Your order is the reverse of the expected trace — check which end "
                             "of the queue/stack you take from."), "traversal_order"
    if len(got_tokens) != len(set(got_tokens)):
        return False, 0.2, ("Some vertices appear more than once in your trace — that is the "
                            "missing (or misplaced) visited check."), "visited_state"
    if got_tokens and got_tokens == sorted(set(exp_tokens)):
        return False, 0.2, ("You listed vertices in sorted order, not traversal order — follow the "
                            "data structure, not the alphabet."), "traversal_order"
    if got_tokens[:1] == exp_tokens[:1] and len(got_tokens) < len(exp_tokens):
        return False, 0.3, ("Right start, but the exploration stopped early — keep expanding "
                            "neighbors until the queue/stack is empty."), "manual_tracing"
    if got_tokens and set(got_tokens) == set(exp_tokens):
        return False, 0.4, ("Right vertex set, wrong order. Re-trace: which vertex leaves the "
                            "structure next, and why?"), "traversal_order"
    return False, 0.0, ("The trace does not match. Walk it step by step: current vertex, "
                        "queue/stack contents, visited set."), None


def grade_complexity(exercise: Exercise, response: str) -> tuple[bool | None, float, str, Optional[str]]:
    acceptable = {norm_bigoh(a) for a in exercise.payload.get("acceptable", [])}
    got = norm_bigoh(response)
    if got in acceptable:
        return True, 1.0, "Correct — and you could justify it from vertex work + edge work.", None
    kind = exercise.payload.get("kind", "sum")
    if kind == "sum" and got in {"o(v)", "o(e)"}:
        return False, 0.4, ("Half right: traversal pays for vertices AND edges — add the two "
                            "work buckets together."), "bfs_time_complexity"
    if kind == "space" and got in {"o(e)", "o(v^2)"}:
        return False, 0.3, ("The extra memory only ever holds vertices (visited + queue/stack), "
                            "not edges."), "bfs_space_complexity"
    if got.startswith("o(v*e)"):
        return False, 0.2, "That would be for nested scans — BFS/DFS scan each edge a bounded number of times.", None
    return False, 0.0, "Not the standard bound for this setup. Count vertex work and edge work separately.", None


def grade_graph_construction(exercise: Exercise, response: str) -> tuple[bool | None, float, str, Optional[str]]:
    pairs = set()
    for raw in re.split(r"[,;\n]+", response or ""):
        raw = raw.strip().lower().replace(" ", "")
        m = re.match(r"^(?:\(?)([a-z0-9]+)[-–—,]?([a-z0-9]+)(\)?)$", raw)
        if m and m.group(1) != m.group(2):
            u, v = sorted([m.group(1), m.group(2)])
            pairs.add((u, v))
    expected = {tuple(sorted([u.lower(), v.lower()])) for u, v in exercise.payload["expected_edges"]}
    if not pairs:
        return False, 0.0, "I could not parse any edges — use pairs like 'A-B, A-C'.", None
    if pairs == expected:
        return True, 1.0, "Exactly the right edge set — every degree constraint holds.", None
    missing = expected - pairs
    extra = pairs - expected
    if not missing and extra:
        return False, 0.5, f"The required edges are all there, but {sorted(extra)} would break a degree constraint.", None
    if missing and not extra:
        return False, 0.5, f"You are missing edges: {sorted(missing)}. Recheck each vertex's degree.", None
    return False, 0.25, (f"Missing {sorted(missing)} and {sorted(extra)} should not be there. "
                         "Count every vertex's degree one by one."), None


_ALLOWED_IMPORTS = {"collections"}


def _safe_ast(code: str) -> str | None:
    """Return a rejection reason, or None when the AST only uses safe constructs."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return f"SyntaxError: {exc.msg} (line {exc.lineno})"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in _ALLOWED_IMPORTS:
                    return f"import of '{alias.name}' is not allowed here"
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root not in _ALLOWED_IMPORTS:
                return f"import from '{node.module}' is not allowed here"
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                return "dunder attributes are not allowed"
        elif isinstance(node, ast.Name) and node.id in {"eval", "exec", "open", "compile", "__import__"}:
            return f"'{node.id}' is not allowed here"
    return None


def grade_code_writing(exercise: Exercise, response: str) -> tuple[bool | None, float, str, Optional[str]]:
    payload = exercise.payload
    fn_name = payload["function_name"]
    tests = payload.get("tests", [])
    if _looks_like_copied(response, payload.get("solution")):
        return False, 0.0, ("This matches the reference solution verbatim — reproduce it from your own "
                            "understanding instead; copying does not build mastery."), fn_name
    outcome = code_runner.run_tests(response, fn_name, tests)
    ratio = outcome["passed"] / outcome["total"] if outcome["total"] else 0.0
    if ratio == 1.0:
        return True, 1.0, f"All {outcome['total']} test cases pass. Clean, correct {fn_name}.", None
    if ratio >= 0.5:
        return False, round(ratio, 3), f"{outcome['passed']}/{outcome['total']} tests pass. {outcome['failure']}", None
    diagnosis = _diagnose_code(fn_name, outcome["failure"])
    return False, round(ratio, 3), f"{outcome['passed']}/{outcome['total']} tests pass. {outcome['failure']}", diagnosis


def _diagnose_code(fn_name: str, failure: str) -> Optional[str]:
    f = failure.lower()
    if "recursionerror" in f:
        return "dfs_implementation"
    if "deque" in f and fn_name.startswith("bfs"):
        return "queue_mechanism"
    if "{" in failure and fn_name.startswith("bfs_levels"):
        return "bfs_visited_handling"
    if "got none" in f:
        return fn_name
    return None


def grade_free_form(exercise: Exercise, response: str) -> tuple[bool | None, float, str, Optional[str]]:
    payload = exercise.payload
    points = payload.get("reference_points", [])
    if payload.get("open_ended"):
        return True, 0.8, "Thanks — noted for the learning record.", None
    min_points = int(payload.get("min_points", 2))
    text = norm_text(response)
    matched: list[str] = []
    for point in points:
        for kw in point.get("keywords", []):
            if norm_text(kw) in text:
                matched.append(point["id"])
                break
    total = len(points) or 1
    ratio = len(matched) / total
    if len(matched) >= min_points:
        return True, max(0.8, ratio), (f"Good reasoning — it covers {len(matched)}/{total} key ideas "
                                       "I look for in this explanation."), None
    if matched:
        missing = [p["text"] for p in points if p["id"] not in matched]
        return False, round(0.4 * ratio, 3), (f"Partly there: one key idea is present, but I still miss "
                                              f"{' and '.join(missing)}. Try adding it."), None
    return False, 0.0, ("This does not yet hit the key ideas of the explanation. "
                        "Re-read the mechanism and answer in your own words."), None


GRADERS = {
    # every grader returns the uniform contract: (correct, score, feedback, missing_skill|None)
    InteractionType.MCQ: lambda ex, r: grade_mcq(ex, r) + (None,),
    InteractionType.OUTPUT_PREDICTION: grade_prediction,
    InteractionType.CODE_TRACING: grade_prediction,
    InteractionType.COMPLEXITY_QUESTION: grade_complexity,
    InteractionType.GRAPH_CONSTRUCTION: grade_graph_construction,
    InteractionType.CODE_WRITING: grade_code_writing,
    InteractionType.FREE_FORM: grade_free_form,
}


# --------------------------------------------------------------------------
# provider
# --------------------------------------------------------------------------
GENERIC_LADDERS: dict[str, list[dict[str, str]]] = {
    "default": [
        {"kind": "socratic_question", "text": "What is the exercise really asking you to produce, in one sentence?"},
        {"kind": "micro_question", "text": "Which single part of the task are you least sure about?"},
        {"kind": "light_hint", "text": "Work one concrete step on paper before answering."},
        {"kind": "targeted_explanation", "text": "Break the task into: model it, traverse it, then read the answer from the traversal."},
    ],
    "code": [
        {"kind": "socratic_question", "text": "What must be true at the top of each loop iteration for this to be correct?"},
        {"kind": "micro_question", "text": "Which data structure does this traversal use, and what leaves it first?"},
        {"kind": "light_hint", "text": "Write the visited check before any enqueue/recursive call, not after."},
        {"kind": "targeted_explanation", "text": "Structure: seed the structure with the start, mark it, loop until empty, expand unvisited neighbors only."},
    ],
    "complexity": [
        {"kind": "socratic_question", "text": "What work happens once per vertex, and what happens per edge?"},
        {"kind": "micro_question", "text": "Can one vertex enter the queue/call stack twice here?"},
        {"kind": "light_hint", "text": "Total = vertex work + edge work."},
        {"kind": "targeted_explanation", "text": "Each vertex is processed at most once and each edge examined a bounded number of times — add the two terms."},
    ],
}

MICRO_QUESTIONS: dict[str, list[dict[str, Any]]] = {
    "visited_state": [
        {"interaction_type": "mcq", "prompt": "Micro-check: when should a vertex be added to the visited set in BFS?",
         "payload": {"choices": [{"id": "a", "text": "When it is enqueued"}, {"id": "b", "text": "When it is dequeued"},
                                 {"id": "c", "text": "After the queue empties"}, {"id": "d", "text": "Never"}],
                     "answer_id": "a", "explanation": "Enqueue-time marking keeps every vertex in the queue at most once."}},
    ],
    "queue_mechanism": [
        {"interaction_type": "mcq", "prompt": "Micro-check: a queue processes elements in which order?",
         "payload": {"choices": [{"id": "a", "text": "First in, first out (FIFO)"}, {"id": "b", "text": "Last in, first out (LIFO)"},
                                 {"id": "c", "text": "Sorted order"}, {"id": "d", "text": "Random order"}],
                     "answer_id": "a", "explanation": "FIFO is what makes BFS sweep level by level."}},
    ],
    "recursion_mechanism": [
        {"interaction_type": "mcq", "prompt": "Micro-check: what stops a recursive function from calling itself forever?",
         "payload": {"choices": [{"id": "a", "text": "A base case"}, {"id": "b", "text": "The queue emptying"},
                                 {"id": "c", "text": "The visited set of BFS"}, {"id": "d", "text": "Python's sorter"}],
                     "answer_id": "a", "explanation": "Base case + guaranteed progress (visited) terminate recursion."}},
    ],
    "traversal_order": [
        {"interaction_type": "mcq", "prompt": "Micro-check: pop() from a stack takes the element that was added...",
         "payload": {"choices": [{"id": "a", "text": "First"}, {"id": "b", "text": "Last"},
                                 {"id": "c", "text": "Smallest"}, {"id": "d", "text": "Randomly"}],
                     "answer_id": "b", "explanation": "LIFO = newest first = depth-first behavior."}},
    ],
    "bfs_time_complexity": [
        {"interaction_type": "mcq", "prompt": "Micro-check: with enqueue-time marking, how many times can one vertex be enqueued?",
         "payload": {"choices": [{"id": "a", "text": "At most once"}, {"id": "b", "text": "Once per edge"},
                                 {"id": "c", "text": "Unbounded"}, {"id": "d", "text": "Twice"}],
                     "answer_id": "a", "explanation": "That single-entry fact is why BFS is O(V) on the vertex side."}},
    ],
    "dfs_space_complexity": [
        {"interaction_type": "mcq", "prompt": "Micro-check: what stores 'where to backtrack to' in recursive DFS?",
         "payload": {"choices": [{"id": "a", "text": "The call stack"}, {"id": "b", "text": "The queue"},
                                 {"id": "c", "text": "The adjacency matrix"}, {"id": "d", "text": "The sorted order"}],
                     "answer_id": "a", "explanation": "Call-stack depth can reach O(V) on a path graph."}},
    ],
    "degree": [
        {"interaction_type": "mcq", "prompt": "Micro-check: the degree of a vertex counts...",
         "payload": {"choices": [{"id": "a", "text": "Edges attached to it"}, {"id": "b", "text": "Vertices in the graph"},
                                 {"id": "c", "text": "Cycles through it"}, {"id": "d", "text": "Its weight"}],
                     "answer_id": "a", "explanation": "Degree = number of incident edges."}},
    ],
}

FALLBACK_MICRO: dict[str, Any] = {
    "interaction_type": "free_form",
    "prompt": "Micro-question: explain {skill} in one sentence, in your own words.",
    "payload": {"reference_points": [], "min_points": 1, "open_ended": True},
}


class BuiltinAITutor(AITutor):
    """Offline semantic provider authored by AutoClaw. Deterministic and schema-valid."""

    name = "builtin"
    model = None

    def __init__(self):
        self.calls = 0

    # ---------------------------------------------------------- evaluation
    def evaluate(self, exercise: Exercise, response: str, context: dict) -> EvaluationResult:
        self.calls += 1
        itype = exercise.interaction_type
        misconception: Optional[str] = None
        missing: Optional[str] = None
        understood: Optional[bool] = None
        hint_level: Optional[int] = None

        grader = GRADERS.get(itype)
        if grader is None:
            correct, score, feedback, missing = True, 0.0, "This interaction type is recorded without grading.", None
        else:
            correct, score, feedback, missing = grader(exercise, response or "")
            if itype == InteractionType.FREE_FORM:
                understood = bool(correct)

        if not correct:
            for pattern, misc, skill in MISCONCEPTION_PATTERNS:
                if re.search(pattern, norm_text(response or "")):
                    misconception = misc
                    missing = missing or skill
                    break
            hint_level = 1 if score >= 0.4 else 2
        else:
            understood = True if understood is None else understood

        recommended = self._recommended_action(correct, score, itype)
        confidence_signal = self._confidence_signal(context, correct)
        # builtin is deterministic: full confidence in its own interpretation except
        # rubric-matched free-form grading, which is heuristic
        ai_confidence = 0.85 if itype == InteractionType.FREE_FORM else 1.0

        return EvaluationResult(
            correct=correct, score=score, understood_concept=understood,
            identified_misconception=misconception, missing_skill=missing,
            recommended_action=recommended, hint_level=hint_level,
            feedback=feedback, confidence_signal=confidence_signal,
            ai_confidence=ai_confidence,
            provider=self.name, model=None, prompt_version=PROMPT_VERSION,
            raw={"builtin_grader": itype.value},
        )

    @staticmethod
    def _recommended_action(correct, score, itype) -> str:
        if correct and score >= 0.8:
            return "acknowledge_advance"
        if correct:
            return "retry" if itype == InteractionType.CODE_WRITING else "acknowledge_advance"
        if score >= 0.4:
            return "light_hint_needed"
        if itype == InteractionType.CODE_WRITING:
            return "micro_question"
        return "micro_question"

    @staticmethod
    def _confidence_signal(context: dict, correct) -> Optional[str]:
        confidence = context.get("confidence")
        if confidence is None or correct is None:
            return None
        try:
            confidence = int(confidence)
        except (TypeError, ValueError):
            return None
        if confidence >= 4 and correct is False:
            return "overconfident"
        if confidence <= 2 and correct is True:
            return "underconfident"
        return "calibrated"

    # ---------------------------------------------------------- hints
    def generate_hint(self, exercise: Exercise, response: str, hints_used: int,
                      context: dict) -> HintResult:
        self.calls += 1
        ladder = exercise.hint_ladder or self._generic_ladder(exercise)
        idx = min(max(hints_used, 0), len(ladder) - 1)
        entry = ladder[idx]
        level = normalize_hint_level(entry["kind"])
        text = self._mask_solution(entry["text"], exercise)
        # L5 (partial solution): beyond the authored ladder, reveal the approach
        # skeleton for code exercises — never the complete solution (L6 is the reveal)
        if hints_used >= len(ladder) and exercise.interaction_type == InteractionType.CODE_WRITING \
                and exercise.payload.get("solution"):
            skeleton = self._partial_solution(exercise.payload["solution"])
            text = f"Partial solution skeleton (fill in the logic yourself):\n{skeleton}"
            level = 5
            entry_kind = "partial_solution"
        else:
            entry_kind = entry["kind"]
        return HintResult(level=level, kind=entry_kind, text=text, is_solution=False,
                          provider=self.name, model=None, prompt_version=PROMPT_VERSION)

    @staticmethod
    def _partial_solution(solution: str) -> str:
        """L5: keep the structure, strip the bodies — the learner fills the logic."""
        lines = solution.splitlines()
        out = []
        for line in lines[:4]:
            out.append(line)
        if len(lines) > 4:
            out.append("    # ... (rest of the logic is yours)")
        return "\n".join(out)

    @staticmethod
    def _generic_ladder(exercise: Exercise) -> list[dict[str, str]]:
        if exercise.interaction_type == InteractionType.CODE_WRITING:
            return GENERIC_LADDERS["code"]
        if exercise.interaction_type == InteractionType.COMPLEXITY_QUESTION:
            return GENERIC_LADDERS["complexity"]
        return GENERIC_LADDERS["default"]

    @staticmethod
    def _mask_solution(text: str, exercise: Exercise) -> str:
        solution = exercise.payload.get("solution") if isinstance(exercise.payload, dict) else None
        if solution and solution.strip() and solution.strip() in text:
            return text.replace(solution.strip(),
                                "<approach only — write the exact code yourself>")
        return text

    # ---------------------------------------------------------- generation
    def generate_controlled_remediation(self, skill_id: str, context: dict) -> GeneratedExercise:
        self.calls += 1
        bank = MICRO_QUESTIONS.get(skill_id)
        if bank:
            item = bank[context.get("micro_index", 0) % len(bank)]
        else:
            item = {"interaction_type": FALLBACK_MICRO["interaction_type"],
                    "prompt": FALLBACK_MICRO["prompt"].format(skill=context.get("skill_title", skill_id)),
                    "payload": dict(FALLBACK_MICRO["payload"])}
        return GeneratedExercise(skill_id=skill_id, interaction_type=item["interaction_type"],
                                 prompt=item["prompt"], payload=item["payload"],
                                 difficulty={"conceptual": 1, "implementation": 1, "reasoning": 1, "transfer": 1},
                                 source="ai", provider=self.name, model=None, prompt_version=PROMPT_VERSION)

    generate_micro_question = generate_controlled_remediation  # legacy alias

    def detect_misconception(self, exercise: Exercise, response: str, context: dict) -> EvaluationResult:
        """Misconception-only observation: same deterministic machinery, explicitly named."""
        return self.evaluate(exercise, response, context)

    def hint(self, exercise: Exercise, response: str, hints_used: int, context: dict) -> HintResult:
        return self.generate_hint(exercise, response, hints_used, context)

    def generate_micro_question(self, skill_id: str, context: dict) -> GeneratedExercise:
        return self.generate_controlled_remediation(skill_id, context)

    # ---------------------------------------------------------- explanation
    def explain(self, theory: str | None, connect_back: str) -> "ExplainResult":
        self.calls += 1
        parts = [p for p in [theory, connect_back] if p]
        text = "\n\n".join(parts) if parts else "Let's re-read the current step together."
        from .schemas import ExplainResult
        return ExplainResult(text=text, provider=self.name, model=None,
                             prompt_version=PROMPT_VERSION, ai_confidence=1.0)
