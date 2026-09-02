"""V1 baseline evidence: AI-outage fallback demo (hybrid provider, unreachable endpoint).

Run:  .venv\\Scripts\\python.exe reports\\ai_fallback_demo.py   (from the v1 root)
Demonstrates: external AI unreachable -> builtin tutor takes over (degraded=True),
session continues, failure reason is visible, no crash. Output saved next to this file
as ai_fallback_demo.txt during the 2026-09-02 baseline run.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conftest import drive_to_exercise  # noqa: E402
from dsa_tutor.app.service import TutorService  # noqa: E402
from dsa_tutor.config import AIConfig, AppConfig  # noqa: E402
from dsa_tutor.persistence.memory_repositories import MemoryStorage  # noqa: E402

cfg = AppConfig(ai=AIConfig(
    provider="hybrid", base_url="http://127.0.0.1:9/v1", api_key="demo-key-not-real",
    model="demo-model", timeout_seconds=2, max_retries=0,
    usage_file=str(ROOT / "reports" / "tmp_ai_usage.json")))
svc = TutorService(MemoryStorage(), cfg)
view, ex = drive_to_exercise(svc, target_type="free_form")
print("walked to exercise:", ex.id, "|", ex.interaction_type.value, "| skill:", ex.skill_id)
res = svc.submit_response("A graph is a set of vertices connected by edges; BFS visits "
                          "level by level using a queue and marks nodes visited when enqueued.")
ev = res.evaluation
print("after submit -> evaluation.provider =", ev.provider, "| degraded =", ev.degraded,
      "| correct =", ev.correct, "| score =", round(ev.score, 2))
print("feedback:", ev.feedback[:180])
print("view.extra['ai_degraded'] =", res.extra.get("ai_degraded"))
print("hybrid.last_fallback_reason =", getattr(svc.ai, "last_fallback_reason", None))
h = svc.request_hint()
print("hint -> provider =", h.hint.provider, "| level =", h.hint.level, "| kind =", h.hint.kind)
print("hybrid.last_fallback_reason =", getattr(svc.ai, "last_fallback_reason", None))
print("session status after fallbacks:", svc.session.status.value if svc.session else None)
print("RESULT: external AI unreachable -> session continued on the builtin tutor, no crash.")