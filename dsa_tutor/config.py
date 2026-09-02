"""Central configuration. Loads .env, exposes frozen dataclasses. No hard-coded secrets."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # dotenv optional; env vars still work
    def load_dotenv(*args, **kwargs):  # type: ignore[misc]
        return False

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class DatabaseConfig:
    host: str = field(default_factory=lambda: _env("DB_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: _env_int("DB_PORT", 3306))
    user: str = field(default_factory=lambda: _env("DB_USER", "root"))
    password: str = field(default_factory=lambda: _env("DB_PASSWORD", ""))
    name: str = field(default_factory=lambda: _env("DB_NAME", "dsa_tutor_v1"))

    def as_dict(self) -> dict:
        return dict(host=self.host, port=self.port, user=self.user,
                    password=self.password, database=self.name, charset="utf8mb4",
                    autocommit=False)


@dataclass(frozen=True)
class AIConfig:
    provider: str = field(default_factory=lambda: _env("AI_PROVIDER", "builtin").strip().lower())
    model: str = field(default_factory=lambda: _env("AI_MODEL", "gpt-4o-mini"))
    base_url: str = field(default_factory=lambda: _env("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    api_key: str = field(default_factory=lambda: _env("OPENAI_API_KEY", ""))
    timeout_seconds: int = field(default_factory=lambda: _env_int("AI_TIMEOUT_SECONDS", 30))
    max_retries: int = field(default_factory=lambda: _env_int("AI_MAX_RETRIES", 2))
    max_calls_per_session: int = field(default_factory=lambda: _env_int("AI_MAX_CALLS_PER_SESSION", 60))
    temperature: float = field(default_factory=lambda: _env_float("AI_TEMPERATURE", 0.2))
    max_tokens: int = field(default_factory=lambda: _env_int("AI_MAX_TOKENS", 700))
    # free-tier safeguard: max external LLM HTTP requests per calendar day (0 = unlimited)
    # Groq free tier = 1,000 req/day for gpt-oss-120b (per console.groq.com rate-limits page)
    daily_request_limit: int = field(default_factory=lambda: _env_int("AI_DAILY_REQUEST_LIMIT", 1000))
    usage_file: str = field(default_factory=lambda: _env("AI_USAGE_FILE") or str(
        PROJECT_ROOT / "logs" / "ai_usage.json"))
    # amendment RC-25: raw request/response bodies are logged only when explicitly enabled;
    # structured observations are always retained in ai_interactions
    log_raw_requests: bool = field(default_factory=lambda: _env("AI_LOG_RAW_REQUESTS", "false").lower() == "true")

    def validate(self) -> list[str]:
        errors = []
        if self.provider not in {"builtin", "openai", "hybrid"}:
            errors.append(f"AI_PROVIDER must be builtin|openai|hybrid, got '{self.provider}'")
        if self.provider in {"openai", "hybrid"} and not self.api_key:
            errors.append("OPENAI_API_KEY is required when AI_PROVIDER is openai or hybrid")
        return errors


@dataclass(frozen=True)
class EngineConfig:
    hint_limit: int = field(default_factory=lambda: _env_int("HINT_LIMIT", 4))
    daily_target_units: int = field(default_factory=lambda: _env_int("DAILY_TARGET_UNITS", 4))
    # pace -> approximate session budget in minutes (spec: slow 10-15, normal ~25, fast ~45)
    pace_budget_minutes: dict = field(default_factory=lambda: {"slow": 12, "normal": 25, "fast": 45})
    # when remaining minutes drop below this, prefer short checks / natural stopping point
    short_window_minutes: float = 5.0


@dataclass(frozen=True)
class AppConfig:
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    engine: EngineConfig = field(default_factory=EngineConfig)
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))
    log_dir: str = field(default_factory=lambda: _env("LOG_DIR", "logs"))

    def validate(self) -> list[str]:
        errs = []
        errs.extend(self.ai.validate())
        return errs


def load_config() -> AppConfig:
    return AppConfig()
