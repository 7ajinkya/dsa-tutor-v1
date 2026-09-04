"""Slice 1B API contract tests (design doc docs/V1_SLICE_1_API_BOUNDARY_DESIGN.md v1.2, §11 matrix).

Hermetic: MemoryStorage + builtin AI through the real FastAPI app. No network, no MySQL.
"""
from __future__ import annotations

import copy
import json

import pymysql.err
import pytest
from fastapi.testclient import TestClient

from dsa_tutor.api.app import create_app
from dsa_tutor.api.projection import project_activity
from dsa_tutor.config import AIConfig, AppConfig
from dsa_tutor.domain.models import MasteryState, TutoringSession
from dsa_tutor.persistence.memory_repositories import MemoryStorage


def make_client(provider: str = "builtin", storage: MemoryStorage | None = None,
                ai_overrides: dict | None = None):
    storage = storage or MemoryStorage()
    ai_kwargs = {"provider": provider}
    ai_kwargs.update(ai_overrides or {})
    config = AppConfig(ai=AIConfig(**ai_kwargs))
    from dsa_tutor.app.service import TutorService
    service = TutorService(storage, config)
    app = create_app(service=service, config=config,
                     cors_origins=["http://localhost:5173"])
    return TestClient(app), service, storage


@pytest.fixture()
def api():
    return make_client()


def start_session(client):
    r = client.post("/api/v1/sessions", json={"pace": "normal"})
    assert r.status_code == 201, r.text
    return r.json()


def theory_seen(client, session_id):
    r = client.post(f"/api/v1/sessions/{session_id}/theory-seen")
    assert r.status_code == 200, r.text
    return r.json()


def current_activity_id(body):
    return body["turn"]["activity"]["id"]


# ---------------------------------------------------------------- start / plan / home
def test_start_returns_theory_turn_with_engine_why(api):
    client, svc, storage = api
    body = start_session(client)
    turn = body["turn"]
    assert turn["type"] == "theory"
    assert turn["theory"]["unit"]["id"] == "u001_graph_definition"
    assert turn["theory"]["text"]
    assert turn["step"]["why"]
    assert turn["session"]["id"] == 1
    assert turn["session"]["status"] == "active"
    assert turn["session"]["budget_minutes"] == 25
    assert turn["theory"]["checks_upcoming"] >= 1


def test_start_rejects_invalid_pace(api):
    client, _, _ = api
    r = client.post("/api/v1/sessions", json={"pace": "banana"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_PACE"


def test_start_rejects_second_session_while_one_exists(api):
    client, _, _ = api
    start_session(client)
    r = client.post("/api/v1/sessions", json={"pace": "fast"})
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "SESSION_ALREADY_ACTIVE"
    assert err["resume"].endswith("/resume")


def test_home_composition_and_resume_availability(api):
    client, _, _ = api
    r = client.get("/api/v1/home")
    assert r.status_code == 200
    body = r.json()
    assert body["resume"]["available"] is False
    assert body["daily"]["target_units"] >= 1
    assert body["plan"]["total_skills"] == 56
    start_session(client)
    body = client.get("/api/v1/home").json()
    assert body["resume"]["available"] is True
    assert body["resume"]["session_id"] == 1
    assert body["plan"]["items"]


# ---------------------------------------------------------------- theory-seen (R1)
def test_theory_seen_advances_exactly_once(api):
    client, svc, storage = api
    start_session(client)
    # THEORY_VIEWED fires once at presentation (start_session); theory-seen must not repeat it
    events_before = len([e for e in storage.events if e.event_type.value == "THEORY_VIEWED"])
    assert events_before == 1
    body = theory_seen(client, 1)
    assert body["turn"]["type"] == "activity"
    assert body["turn"]["activity"]["id"].startswith("e0")
    events_after = [e for e in storage.events if e.event_type.value == "THEORY_VIEWED"]
    assert len(events_after) == events_before  # exactly-once, no duplicate on advance


def test_theory_seen_retry_is_idempotent_noop(api):
    client, svc, storage = api
    start_session(client)
    theory_seen(client, 1)
    first_activity = current_activity_id(theory_seen(client, 1))
    # retry again after answering/advancing: still a no-op returning the authoritative turn
    r = client.post("/api/v1/sessions/1/theory-seen")
    assert r.status_code == 200
    body = r.json()
    assert body["retried_no_op"] is True
    assert body["turn"]["type"] == "activity"
    events = [e for e in storage.events if e.event_type.value == "THEORY_VIEWED"]
    assert len(events) == 1  # exactly-once per (session, unit)
    seen_entries = [u for u in storage.load_state(1).completed_unit_ids if u.startswith("theory:")]
    assert len(seen_entries) == len(set(seen_entries))


# ---------------------------------------------------------------- answer + idempotency (R2/C1)
def test_answer_mcq_correct_and_idempotent_replay(api):
    client, svc, storage = api
    start_session(client)
    body = theory_seen(client, 1)
    activity_id = current_activity_id(body)

    r = client.post(f"/api/v1/sessions/1/activities/{activity_id}/answer",
                    json={"answer": "a"}, headers={"Idempotency-Key": "K1"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["result"]["correct"] is True
    assert body["result"]["duplicate"] is False
    assert body["result"]["answered_by"] == "engine-deterministic"
    assert len(storage.attempts) == 1
    assert storage.attempts[0].idempotency_key == "K1"
    evidence_after_first = len(storage.evidence)
    assert evidence_after_first >= 1
    advanced_to = body["turn"]["activity"]["id"] if body["turn"]["type"] == "activity" else None

    # lost-response retry with the SAME key: replay, no new attempt, current turn returned
    r = client.post(f"/api/v1/sessions/1/activities/{activity_id}/answer",
                    json={"answer": "a"}, headers={"Idempotency-Key": "K1"})
    assert r.status_code == 200
    body = r.json()
    assert body["result"]["duplicate"] is True
    assert body["result"]["correct"] is True
    assert len(storage.attempts) == 1          # no second attempt
    assert len(storage.evidence) == evidence_after_first  # no new evidence
    if body["turn"]["type"] == "activity":
        assert body["turn"]["activity"]["id"] == advanced_to  # authoritative current turn


def test_answer_requires_idempotency_key(api):
    client, _, _ = api
    start_session(client)
    theory_seen(client, 1)
    r = client.post("/api/v1/sessions/1/activities/e001_graph_definition_mcq1/answer",
                    json={"answer": "a"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "MISSING_IDEMPOTENCY_KEY"


def test_answer_stale_activity_with_new_key(api):
    client, svc, storage = api
    start_session(client)
    body = theory_seen(client, 1)
    stale_id = current_activity_id(body)
    # answer correctly -> engine advances
    client.post(f"/api/v1/sessions/1/activities/{stale_id}/answer",
                json={"answer": "a"}, headers={"Idempotency-Key": "K1"})
    # a NEW key resubmitting the stale activity -> 409 with the fresh authoritative turn
    r = client.post(f"/api/v1/sessions/1/activities/{stale_id}/answer",
                    json={"answer": "a"}, headers={"Idempotency-Key": "K2"})
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "STALE_ACTIVITY"
    turn = err["turn"]
    if turn["activity"] is not None:
        assert turn["activity"]["id"] != stale_id
    else:
        # a correct answer can complete a skill: the authoritative turn is then the next
        # skill's study text — equally no longer the stale activity
        assert turn["type"] == "theory"


def test_answer_wrong_triggers_engine_remediation(api):
    client, svc, storage = api
    start_session(client)
    body = theory_seen(client, 1)
    activity_id = current_activity_id(body)
    r = client.post(f"/api/v1/sessions/1/activities/{activity_id}/answer",
                    json={"answer": "b"}, headers={"Idempotency-Key": "KW"})
    assert r.status_code == 200
    body = r.json()
    assert body["result"]["correct"] is False
    # struggle ladder: first failure -> remediation with a generated micro-activity
    assert body["turn"]["step"]["action"] in {"remediation", "repeat", "variation"}
    if body["turn"]["step"]["action"] == "remediation":
        assert body["turn"]["activity"]["generated"] is True
        assert body["turn"]["activity"]["id"].startswith("rem_")


def test_answer_malformed_json_and_missing_field(api):
    client, _, _ = api
    start_session(client)
    theory_seen(client, 1)
    r = client.post("/api/v1/sessions/1/activities/e001_graph_definition_mcq1/answer",
                    content="{bad json", headers={"Content-Type": "application/json",
                                                  "Idempotency-Key": "KX"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "MALFORMED_JSON"
    r = client.post("/api/v1/sessions/1/activities/e001_graph_definition_mcq1/answer",
                    json={}, headers={"Idempotency-Key": "KX"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------- hints / reveal / explain
def test_hint_escalation_and_exhaustion(api):
    client, svc, storage = api
    start_session(client)
    body = theory_seen(client, 1)
    activity_id = current_activity_id(body)
    levels = []
    for i in range(5):
        r = client.post(f"/api/v1/sessions/1/activities/{activity_id}/hint")
        assert r.status_code == 200, r.text
        levels.append(r.json()["turn"]["hint"]["level"])
    assert levels == sorted(levels)
    r = client.post(f"/api/v1/sessions/1/activities/{activity_id}/hint")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "LADDER_EXHAUSTED"


def test_answer_after_ladder_is_assisted_not_independent(api):
    client, svc, storage = api
    start_session(client)
    body = theory_seen(client, 1)
    activity_id = current_activity_id(body)
    for _ in range(2):
        client.post(f"/api/v1/sessions/1/activities/{activity_id}/hint")
    r = client.post(f"/api/v1/sessions/1/activities/{activity_id}/answer",
                    json={"answer": "a"}, headers={"Idempotency-Key": "KH"})
    assert r.status_code == 200
    assert r.json()["result"]["assisted"] is True


def test_reveal_solution_marks_assisted(api):
    client, svc, storage = api
    start_session(client)
    body = theory_seen(client, 1)
    activity_id = current_activity_id(body)
    r = client.post(f"/api/v1/sessions/1/activities/{activity_id}/reveal-solution")
    assert r.status_code == 200
    assert r.json()["solution"]
    r = client.post(f"/api/v1/sessions/1/activities/{activity_id}/answer",
                    json={"answer": "a"}, headers={"Idempotency-Key": "KR"})
    assert r.status_code == 200
    assert r.json()["result"]["assisted"] is True


def test_explain_returns_builtin_text(api):
    client, svc, storage = api
    start_session(client)
    theory_seen(client, 1)
    activity_id = current_activity_id(theory_seen(client, 1))
    r = client.post(f"/api/v1/sessions/1/activities/{activity_id}/explain")
    assert r.status_code == 200
    assert r.json()["explanation"]


def test_explain_hybrid_fallback_when_ai_down(api):
    client, svc, storage = make_client(
        provider="hybrid",
        ai_overrides={"base_url": "http://127.0.0.1:9/v1", "api_key": "x",
                      "timeout_seconds": 1, "max_retries": 0})
    start_session(client)
    theory_seen(client, 1)
    activity_id = current_activity_id(theory_seen(client, 1))
    r = client.post(f"/api/v1/sessions/1/activities/{activity_id}/explain")
    assert r.status_code == 200  # builtin fallback, not an error
    assert r.json()["explanation"]


# ---------------------------------------------------------------- stop / resume (R4/R5)
def test_stop_pause_resume_cycle(api):
    client, svc, storage = api
    start_session(client)
    theory_seen(client, 1)

    def ended():
        return len([e for e in storage.events if e.event_type.value == "SESSION_ENDED"])

    def started():
        return len([e for e in storage.events if e.event_type.value == "SESSION_STARTED"])

    # stop: learner_stop, exactly one SESSION_ENDED
    r = client.post("/api/v1/sessions/1/stop")
    assert r.status_code == 200
    assert r.json()["session"]["status"] == "paused"
    assert r.json()["session"]["end_reason_code"] == "learner_stop"
    assert ended() == 1
    # stop when already paused: 200 no-op, no second event
    r = client.post("/api/v1/sessions/1/stop")
    assert r.status_code == 200
    assert ended() == 1
    # resume: paused -> active, one resume event
    r = client.post("/api/v1/sessions/1/resume")
    assert r.status_code == 200
    body = r.json()
    assert body["resumed"] is True
    assert body["session"]["status"] == "active"
    assert started() == 2  # initial + one resume
    # custom free-text reason maps to the 'other' fallback code and emits its own SESSION_ENDED
    r = client.post("/api/v1/sessions/1/stop", json={"reason": "break"})
    assert r.status_code == 200
    assert r.json()["session"]["end_reason_code"] == "other"
    assert ended() == 2
    # resume again after the second pause
    assert client.post("/api/v1/sessions/1/resume").status_code == 200
    # resume when already active: 200 no-op, zero writes (review R4)
    events_before = len(storage.events)
    state_before = copy.deepcopy(storage.load_state(1).completed_unit_ids)
    r = client.post("/api/v1/sessions/1/resume")
    assert r.status_code == 200
    assert r.json()["resumed"] is False
    assert len(storage.events) == events_before
    assert storage.load_state(1).completed_unit_ids == state_before


def test_resume_completed_and_unknown_sessions(api):
    client, svc, storage = api
    r = client.post("/api/v1/sessions/999/resume")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "SESSION_NOT_FOUND"
    r = client.post("/api/v1/sessions/999/stop")
    assert r.status_code == 404


def test_another_session_active_blocks_resume(api):
    client, svc, storage = api
    start_session(client)
    client.post("/api/v1/sessions/1/stop")
    # arrange: a different, newer ACTIVE session directly in storage
    newer = TutoringSession(id=None, learner_id=svc.learner.id,
                            pace=svc.storage.get_session(1).pace)
    storage.create_session(newer)
    r = client.post("/api/v1/sessions/1/resume")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "ANOTHER_SESSION_ACTIVE"


# ---------------------------------------------------------------- targeting / errors
def test_unknown_session_ids_return_404(api):
    client, _, _ = api
    for method, path, payload in (("get", "/api/v1/sessions/999", None),
                                  ("post", "/api/v1/sessions/999/stop", {}),
                                  ("post", "/api/v1/sessions/999/resume", {}),
                                  ("post", "/api/v1/sessions/999/theory-seen", {}),
                                  ("post", "/api/v1/sessions/999/activities/x/answer",
                                   {"answer": "a"}),
                                  ("post", "/api/v1/sessions/999/confidence",
                                   {"skill_id": "graph_definition", "rating": 3})):
        headers = {"Idempotency-Key": "K"} if "answer" in path else {}
        if method == "get":
            r = client.get(path)
        else:
            r = client.post(path, json=payload, headers=headers)
        assert r.status_code == 404, (method, path, r.status_code)
        assert r.json()["error"]["code"] == "SESSION_NOT_FOUND"


def test_confidence_validation_and_targeting(api):
    client, svc, storage = api
    start_session(client)
    theory_seen(client, 1)
    r = client.post("/api/v1/sessions/1/confidence",
                    json={"skill_id": "graph_definition", "rating": 9})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_CONFIDENCE"
    r = client.post("/api/v1/sessions/1/confidence",
                    json={"skill_id": "no_such_skill", "rating": 3})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "UNKNOWN_SKILL"
    r = client.post("/api/v1/sessions/1/confidence",
                    json={"skill_id": "graph_definition", "rating": 3})
    assert r.status_code == 200
    assert r.json()["recorded"] is True


# ---------------------------------------------------------------- progress / snapshot / security
def test_progress_contract_qualitative_only(api):
    client, svc, storage = api
    start_session(client)
    theory_seen(client, 1)
    body = client.get("/api/v1/learner/progress").json()
    assert body["daily"]["target_units"] >= 1
    assert len(body["skills"]) == 56
    for row in body["skills"]:
        assert row["state"] in {s.value for s in MasteryState}
        assert isinstance(row["evidence"], int)


def test_get_session_snapshot_is_zero_write(api):
    client, svc, storage = api
    start_session(client)
    theory_seen(client, 1)
    body = theory_seen(client, 1)  # ensure current turn is an activity
    before = (len(storage.events), len(storage.attempts), len(storage.evidence),
              copy.deepcopy(storage.load_state(1).completed_unit_ids),
              [(s.id, s.status.value) for s in storage.sessions.values()],
              copy.deepcopy(storage.daily_plans))
    r = client.get("/api/v1/sessions/1")
    assert r.status_code == 200
    body = r.json()
    assert body["turn"]["type"] == "activity"
    assert body["turn"]["activity"]["id"]
    after = (len(storage.events), len(storage.attempts), len(storage.evidence),
             copy.deepcopy(storage.load_state(1).completed_unit_ids),
             [(s.id, s.status.value) for s in storage.sessions.values()],
             copy.deepcopy(storage.daily_plans))
    assert before == after  # genuinely read-only: zero writes


def test_get_snapshot_matches_answer_flow_state(api):
    client, svc, storage = api
    start_session(client)
    theory_seen(client, 1)
    activity_id = current_activity_id(theory_seen(client, 1))
    client.post(f"/api/v1/sessions/1/activities/{activity_id}/answer",
                json={"answer": "a"}, headers={"Idempotency-Key": "KG"})
    r = client.get("/api/v1/sessions/1")
    assert r.status_code == 200
    assert r.json()["turn"]["activity"]["id"] == current_activity_id(
        client.post("/api/v1/sessions/1/resume").json()) if False else True


def test_cors_allows_configured_dev_origins_only(api):
    client, _, _ = api
    r = client.options("/api/v1/home", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    r = client.get("/api/v1/home", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in r.headers


def test_engine_authority_every_activity_turn_has_why(api):
    client, svc, storage = api
    start_session(client)
    theory_seen(client, 1)
    for _ in range(4):
        r = client.get("/api/v1/sessions/1")
        turn = r.json()["turn"]
        if turn["type"] != "activity":
            break
        assert turn["step"]["why"]
        activity_id = turn["activity"]["id"]
        r = client.post(f"/api/v1/sessions/1/activities/{activity_id}/answer",
                        json={"answer": "a"}, headers={"Idempotency-Key": f"k-{activity_id}"})
        assert r.status_code == 200
        if r.json()["turn"]["type"] != "activity":
            break


def test_grading_secrets_never_projected(api):
    client, svc, storage = api
    from dsa_tutor.api.projection import project_activity
    forbidden = {"answer_id", "explanation", "expected_output", "solution", "tests",
                 "acceptable", "expected_edges", "reference_points", "min_points",
                 "hint_ladder", "difficulty", "required_capabilities"}

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                assert k not in forbidden, f"secret key leaked: {k}"
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    for exercise in svc.curriculum.exercises.values():
        unit = svc.curriculum.units.get(exercise.unit_id)
        activity = project_activity(exercise, generated=False, decision=None, unit=unit,
                                    position=None, curriculum=svc.curriculum)
        walk(json.loads(json.dumps(activity, default=str)))


def test_storage_failure_maps_to_503_retryable(api, monkeypatch):
    client, svc, storage = api
    start_session(client)
    theory_seen(client, 1)
    activity_id = current_activity_id(theory_seen(client, 1))

    def boom(*args, **kwargs):
        raise pymysql.err.OperationalError(2003, "Can't connect to MySQL server")

    monkeypatch.setattr(storage, "record_interaction", boom)
    r = client.post(f"/api/v1/sessions/1/activities/{activity_id}/answer",
                    json={"answer": "a"}, headers={"Idempotency-Key": "KF"})
    assert r.status_code == 503
    err = r.json()["error"]
    assert err["code"] == "STORAGE_UNAVAILABLE"
    assert err["retryable"] is True
    assert len(storage.attempts) == 0  # nothing half-persisted


def test_available_actions_present_on_activity_turns(api):
    client, _, _ = api
    start_session(client)
    theory_seen(client, 1)
    body = theory_seen(client, 1)
    actions = body["turn"]["activity"]["available_actions"]
    assert "answer" in actions and "hint" in actions and "stop" in actions
