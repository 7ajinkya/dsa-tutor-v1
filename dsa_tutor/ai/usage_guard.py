"""Daily external-AI usage guard (free-tier safeguard).

Tracks every external LLM HTTP request per calendar day in a local JSON file and
refuses external calls once the configured daily budget is spent. The hybrid layer
then falls back to the offline builtin engine automatically, so a learner never sees
a failure - external service simply resumes the next day (or whenever the counter
resets / the limit is raised).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path


class UsageGuard:
    def __init__(self, limit: int, path: str):
        self.limit = max(0, int(limit))
        self.path = Path(path)
        self._state: dict = {"date": None, "count": 0}
        self._load()

    # ---------------------------------------------------------- persistence
    def _load(self) -> None:
        try:
            if self.path.exists():
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and raw.get("date") == date.today().isoformat():
                    self._state = {"date": raw["date"], "count": int(raw.get("count", 0))}
                else:
                    self._state = {"date": date.today().isoformat(), "count": 0}
        except Exception:  # noqa: BLE001 - the guard must never break the tutor
            self._state = {"date": date.today().isoformat(), "count": 0}

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._state), encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    # ---------------------------------------------------------- api
    def reset_if_new_day(self) -> None:
        today = date.today().isoformat()
        if self._state.get("date") != today:
            self._state = {"date": today, "count": 0}
            self._save()

    def record(self, n: int = 1) -> None:
        self.reset_if_new_day()
        self._state["count"] = int(self._state.get("count", 0)) + n
        self._save()

    def exhausted(self) -> bool:
        self.reset_if_new_day()
        return self.limit > 0 and int(self._state.get("count", 0)) >= self.limit

    def status(self) -> dict:
        self.reset_if_new_day()
        return {"date": self._state["date"], "used": int(self._state.get("count", 0)),
                "limit": self.limit, "remaining": max(0, self.limit - int(self._state.get("count", 0)))}

    @property
    def exhausted_message(self) -> str:
        s = self.status()
        return (f"daily external AI limit reached ({s['used']}/{s['limit']} requests). "
                f"The built-in offline tutor has taken over - external calls resume "
                f"automatically after the daily reset (limit resets every day, {s['limit']} requests/day).")
