"""Local structured logging (spec 06 §12): JSON lines to logs/tutor.log + console echo."""
from __future__ import annotations

import json
import logging
from pathlib import Path


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)[:2000]
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str = "INFO", log_dir: str = "logs") -> Path:
    base = Path(log_dir)
    base.mkdir(parents=True, exist_ok=True)
    logfile = base / "tutor.log"
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    file_handler = logging.FileHandler(logfile, encoding="utf-8")
    file_handler.setFormatter(JsonLineFormatter())
    root.addHandler(file_handler)
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    root.addHandler(console)
    return logfile
