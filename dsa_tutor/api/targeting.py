"""Session targeting (design doc §4.13): the path {session_id} is authoritative.

TutorService methods operate on the service's current session context and take no session id,
so the API layer verifies targeting before every session-scoped mutation. Application/API-layer
only — no engine change, no schema change.
"""
from __future__ import annotations

from dsa_tutor.api.errors import ApiError


def ensure_session_target(service, session_id: int, *, require_active: bool = True):
    """Resolve the path session and make it the service's current context for mutations.

    - 404 SESSION_NOT_FOUND   : path id does not exist
    - 409 SESSION_NOT_ACTIVE  : require_active and the session is completed/abandoned/paused
    - 409 SESSION_MISMATCH    : another active session is the service's current context
    Attaching a persisted active session to the service is an in-memory operation only
    (no writes) — it restores context after a server restart.
    """
    session = service.storage.get_session(int(session_id))
    if session is None:
        raise ApiError(404, "SESSION_NOT_FOUND", f"No session with id {session_id}.")
    if require_active:
        if session.status.value != "active":
            raise ApiError(409, "SESSION_NOT_ACTIVE",
                           f"Session {session_id} is {session.status.value}, not active.")
        current = service.session
        if current is not None and current.id == session.id:
            return session
        if current is not None and current.status.value == "active":
            raise ApiError(409, "SESSION_MISMATCH",
                           f"Current service session is {current.id}, not {session_id}.")
        service.session = session  # in-memory context attach; nothing persisted
    return session


def ensure_snapshot_target(service, session_id: int):
    """Read-only snapshot targeting (design §4.2): no writes, active/paused only."""
    session = service.storage.get_session(int(session_id))
    if session is None:
        raise ApiError(404, "SESSION_NOT_FOUND", f"No session with id {session_id}.")
    if session.status.value not in {"active", "paused"}:
        raise ApiError(409, "SESSION_NOT_ACTIVE",
                       f"Session {session_id} is {session.status.value}.")
    latest = service.storage.latest_active_session(service.learner.id)
    if latest is None or latest.id != session.id:
        raise ApiError(409, "SESSION_MISMATCH",
                       f"Session {session_id} is not the latest active/paused session.")
    return session
