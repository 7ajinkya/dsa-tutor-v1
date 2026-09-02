"""End-to-end CLI test (review RC-27): full learner session through the real entrypoint."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def run_cli(args, input_text, env_extra=None):
    import os
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "dsa_tutor", *args],
        input=input_text, capture_output=True, text=True, cwd=str(ROOT),
        timeout=120, env=env,
    )


def test_cli_e2e_offline_session_start_answer_stop():
    result = run_cli(["start", "--offline", "--pace", "normal"],
                     "\na\na\nstop\n")
    out = result.stdout
    assert "SESSION PLAN" in out, "session plan must be shown at start"
    assert "STUDY:" in out, "theory/study section must be rendered"
    assert "correct" in out
    assert "paused" in out or "Session paused" in out
    assert result.returncode == 0


def test_cli_e2e_check_and_progress_offline():
    check = run_cli(["check", "--offline"], "")
    assert "Configuration: OK" in check.stdout
    assert "valid" in check.stdout
    progress = run_cli(["progress", "--offline"], "")
    assert "Mastery states" in progress.stdout


def test_cli_e2e_resume_flow(tmp_path):
    usage_file = tmp_path / "ai_usage.json"
    env = {"AI_USAGE_FILE": str(usage_file), "AI_DAILY_REQUEST_LIMIT": "1000"}
    first = run_cli(["start", "--offline"], "\na\nstop\n", env_extra=env)
    assert "paused" in first.stdout or "Session paused" in first.stdout
    # offline mode is non-persistent by design; with MySQL the same flow resumes via --resume
    # (covered by tests/test_persistence_mysql.py::test_state_survives_restart_and_resume)
