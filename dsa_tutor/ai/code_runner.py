"""Learner-code execution — PROCESS ISOLATION WITH STATIC RESTRICTIONS AND TIMEOUT
PROTECTION. This is NOT a secure sandbox and NOT a security boundary. It is appropriate
only for a local, single-user V0 executing the learner's own code; it must not be used
to execute hostile/untrusted code in a production environment (review RC-19 amendment).

Protections provided:
- subprocess isolation (separate interpreter, `-I` isolated mode: no user site, isolated env)
- wall-clock timeout with process kill (default 5s)
- static AST restrictions before execution (import allowlist, no dunders/eval/exec/open)
- stdout/stderr capture, per-test pass/fail results
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path

_ALLOWED_IMPORTS = {"collections"}
TIMEOUT_SECONDS = 5


def static_restrictions_problem(code: str) -> str | None:
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


def _harness_source(fn_name: str, tests_json: str) -> str:
    return (
        "import json, sys\n"
        "spec = json.loads(r'''%s''')\n"
        "namespace = {}\n"
        "exec(compile(open(sys.argv[1], encoding='utf-8').read(), '<learner>', 'exec'), namespace)\n"
        "fn = namespace.get(%r)\n"
        "results = []\n"
        "for t in spec:\n"
        "    try:\n"
        "        got = fn(t['graph'], t['start'])\n"
        "        results.append({'ok': got == t['expected'],\n"
        "                        'got': repr(got), 'expected': repr(t['expected'])})\n"
        "    except Exception as exc:\n"
        "        results.append({'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)})\n"
        "print('===RESULTS===' + json.dumps(results))\n" % (tests_json, fn_name)
    )


def run_tests(code: str, fn_name: str, tests: list[dict]) -> dict:
    """Execute learner code against tests in an isolated subprocess.

    Returns {'passed': int, 'total': int, 'failure': str, 'timeout': bool}.
    """
    problem = static_restrictions_problem(code)
    if problem:
        return {"passed": 0, "total": len(tests), "failure": f"static check: {problem}",
                "timeout": False, "error": True}
    with tempfile.TemporaryDirectory() as tmp:
        solution_path = Path(tmp) / "learner_solution.py"
        solution_path.write_text(code, encoding="utf-8")
        harness_path = Path(tmp) / "harness.py"
        harness_path.write_text(
            _harness_source(fn_name, json.dumps(tests, default=str)), encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(harness_path), str(solution_path)],
                capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
                cwd=tmp, encoding="utf-8", errors="replace",
            )
        except subprocess.TimeoutExpired:
            return {"passed": 0, "total": len(tests),
                    "failure": f"timeout: code did not finish within {TIMEOUT_SECONDS}s",
                    "timeout": True, "error": False}
        except Exception as exc:  # noqa: BLE001 - runner must never crash the tutor
            return {"passed": 0, "total": len(tests),
                    "failure": f"runner error: {exc}", "timeout": False, "error": True}
    marker = "===RESULTS==="
    if marker not in proc.stdout:
        err = (proc.stderr or proc.stdout or "").strip()[:300]
        return {"passed": 0, "total": len(tests),
                "failure": err or "no harness output", "timeout": False, "error": True}
    results = json.loads(proc.stdout.split(marker, 1)[1])
    passed = sum(1 for r in results if r.get("ok"))
    first_failure = next((f"Test case failed: got {r['got']}, expected {r['expected']}."
                          for r in results if not r.get("ok") and "got" in r),
                         next((f"Runtime {r['error']}" for r in results if "error" in r), ""))
    return {"passed": passed, "total": len(results),
            "failure": first_failure or (f"{passed}/{len(results)} tests pass."),
            "timeout": False, "error": False}
