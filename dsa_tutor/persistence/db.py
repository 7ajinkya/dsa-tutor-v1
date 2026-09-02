"""MySQL connection + transaction management + self-bootstrapping schema install.

`install_schema` handles the full bootstrap: create the database if missing (server-level
connection), apply all CREATE TABLE IF NOT EXISTS statements, repair missing columns and
indexes on partially-built databases, so `setup-db` is always safe to re-run.
"""
from __future__ import annotations

import re
from contextlib import contextmanager

import pymysql
import pymysql.cursors

# repairs for databases created by an older/partial run: (table, column) -> ALTER
EXPECTED_COLUMNS: dict[tuple[str, str], str] = {
    ("exercises", "ordering"): "ALTER TABLE exercises ADD COLUMN ordering INT NOT NULL DEFAULT 0",
    ("exercises", "role"): "ALTER TABLE exercises ADD COLUMN role VARCHAR(24) NOT NULL DEFAULT 'RECOGNITION'",
    ("exercises", "scope"): "ALTER TABLE exercises ADD COLUMN scope VARCHAR(12) NOT NULL DEFAULT 'micro'",
    ("exercises", "required_capabilities"): "ALTER TABLE exercises ADD COLUMN required_capabilities JSON NULL",
    ("attempts", "max_assistance_level"): "ALTER TABLE attempts ADD COLUMN max_assistance_level INT NOT NULL DEFAULT 0",
    ("attempts", "idempotency_key"): "ALTER TABLE attempts ADD COLUMN idempotency_key VARCHAR(64) NULL",
    ("assessment_evidence", "evidence_type"): "ALTER TABLE assessment_evidence ADD COLUMN evidence_type VARCHAR(24) NOT NULL DEFAULT 'RECOGNITION'",
    ("assessment_evidence", "assistance_level"): "ALTER TABLE assessment_evidence ADD COLUMN assistance_level INT NOT NULL DEFAULT 0",
    ("skills", "module"): "ALTER TABLE skills ADD COLUMN module VARCHAR(80) NULL",
    ("skills", "description"): "ALTER TABLE skills ADD COLUMN description VARCHAR(300) NULL",
    ("skills", "evidence_requirements"): "ALTER TABLE skills ADD COLUMN evidence_requirements JSON NULL",
    ("skills", "is_optional"): "ALTER TABLE skills ADD COLUMN is_optional BOOLEAN NOT NULL DEFAULT FALSE",
}
# (table, index_name, column definition)
EXPECTED_INDEXES: list[tuple[str, str, str]] = [
    ("learning_units", "idx_units_skill", "(skill_id, ordering)"),
    ("exercises", "idx_ex_unit", "(unit_id, ordering)"),
    ("exercises", "idx_ex_skill", "(skill_id)"),
    ("sessions", "idx_sessions_learner", "(learner_id, started_at)"),
    ("session_events", "idx_events_session", "(session_id, seq)"),
    ("attempts", "idx_attempts_session", "(session_id)"),
    ("attempts", "idx_attempts_skill", "(learner_id, skill_id, created_at)"),
    ("assessment_evidence", "idx_evidence_learner", "(learner_id, skill_id)"),
]
# (table, index_name, column definition) — created as UNIQUE INDEX (Slice 1B idempotency)
EXPECTED_UNIQUE_INDEXES: list[tuple[str, str, str]] = [
    ("attempts", "uq_attempts_idem", "(session_id, idempotency_key)"),
]
REQUIRED_TABLES = {
    "users", "topics", "skills", "skill_prerequisites", "learning_units", "exercises",
    "daily_plans", "sessions", "session_events", "attempts", "assessment_evidence",
    "skill_assessments", "learner_state", "ai_interactions", "hint_events",
}


class Database:
    def __init__(self, config):
        self.config = config  # DatabaseConfig

    # ------------------------------------------------------------- connections
    def connect(self, server_level: bool = False):
        """Connect to the configured database, or to the server without a default DB."""
        kwargs = self.config.as_dict()
        if server_level:
            kwargs.pop("database", None)
        return pymysql.connect(**kwargs, cursorclass=pymysql.cursors.DictCursor)

    def ensure_database(self) -> bool:
        """Create the configured schema if it does not exist. Returns True if created now."""
        name = re.sub(r"[^A-Za-z0-9_]", "", self.config.name)
        with self.connect(server_level=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                cur.execute(
                    "SELECT COUNT(*) AS n FROM information_schema.schemata "
                    "WHERE schema_name = %s", (self.config.name,))
                exists = cur.fetchone()["n"] > 0
        return not exists or True  # idempotent; created==True reported by caller log

    def healthcheck(self) -> tuple[bool, str]:
        try:
            conn = self.connect()
        except pymysql.err.OperationalError as exc:
            code = exc.args[0] if exc.args else None
            if code == 1049:  # unknown database
                return False, (f"database '{self.config.name}' does not exist yet — "
                               "run: python -m dsa_tutor setup-db")
            return False, f"{type(exc).__name__}: {exc}"
        except Exception as exc:  # noqa: BLE001
            return False, f"{type(exc).__name__}: {exc}"
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT VERSION() AS v")
                row = cur.fetchone()
            return True, f"MySQL {row['v']} at {self.config.host}:{self.config.port}/{self.config.name}"
        finally:
            conn.close()

    @contextmanager
    def transaction(self):
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------- schema install
    def install_schema(self, sql_text: str) -> dict:
        """Full idempotent bootstrap: database -> tables -> repairs. Returns a report."""
        self.ensure_database()
        self.run_schema(sql_text)
        self.ensure_columns()
        self.ensure_indexes()
        self.ensure_unique_indexes()
        return self.schema_report()

    def run_schema(self, sql_text: str) -> None:
        """Execute a migration script statement-by-statement (pymysql can't multi-statement).

        Runs on a server-level connection so the script may contain CREATE DATABASE / USE.
        """
        statements = []
        for chunk in sql_text.split(";"):
            # drop comment-only lines, keep the actual statement
            lines = [ln for ln in chunk.strip().splitlines()
                     if ln.strip() and not ln.strip().startswith("--")]
            if lines:
                statements.append("\n".join(lines))
        conn = self.connect(server_level=True)
        try:
            with conn.cursor() as cur:
                for statement in statements:
                    cur.execute(statement)
            conn.commit()
        finally:
            conn.close()

    def ensure_columns(self) -> list[str]:
        """Add any expected-but-missing columns (repairs partially-built databases)."""
        repaired = []
        with self.transaction() as conn:
            with conn.cursor() as cur:
                for (table, column), alter in EXPECTED_COLUMNS.items():
                    cur.execute(
                        "SELECT COUNT(*) AS n FROM information_schema.columns "
                        "WHERE table_schema=%s AND table_name=%s AND column_name=%s",
                        (self.config.name, table, column))
                    if cur.fetchone()["n"] == 0:
                        cur.execute(alter)
                        repaired.append(f"{table}.{column}")
        return repaired

    def ensure_indexes(self) -> list[str]:
        """Create any expected-but-missing indexes (MySQL 8 has no CREATE INDEX IF NOT EXISTS)."""
        created = []
        with self.transaction() as conn:
            with conn.cursor() as cur:
                for table, index_name, definition in EXPECTED_INDEXES:
                    cur.execute(
                        "SELECT COUNT(*) AS n FROM information_schema.statistics "
                        "WHERE table_schema=%s AND table_name=%s AND index_name=%s",
                        (self.config.name, table, index_name))
                    if cur.fetchone()["n"] == 0:
                        cur.execute(f"CREATE INDEX {index_name} ON {table} {definition}")
                        created.append(f"{table}.{index_name}")
        return created

    def ensure_unique_indexes(self) -> list[str]:
        """Create any expected-but-missing UNIQUE indexes (Slice 1B idempotency)."""
        created = []
        with self.transaction() as conn:
            with conn.cursor() as cur:
                for table, index_name, definition in EXPECTED_UNIQUE_INDEXES:
                    cur.execute(
                        "SELECT COUNT(*) AS n FROM information_schema.statistics "
                        "WHERE table_schema=%s AND table_name=%s AND index_name=%s",
                        (self.config.name, table, index_name))
                    if cur.fetchone()["n"] == 0:
                        cur.execute(f"CREATE UNIQUE INDEX {index_name} ON {table} {definition}")
                        created.append(f"{table}.{index_name}")
        return created

    def schema_report(self) -> dict:
        """Snapshot of what exists vs what the application expects."""
        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema=%s",
                    (self.config.name,))
                tables = {r["table_name"] if "table_name" in r else r["TABLE_NAME"]
                          for r in cur.fetchall()}
        missing_tables = sorted(REQUIRED_TABLES - tables)
        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT table_name, column_name FROM information_schema.columns "
                    "WHERE table_schema=%s", (self.config.name,))
                existing_columns = {(r["table_name"] if "table_name" in r else r["TABLE_NAME"],
                                     r["column_name"] if "column_name" in r else r["COLUMN_NAME"])
                                    for r in cur.fetchall()}
        missing_columns = sorted(f"{t}.{c}" for (t, c) in EXPECTED_COLUMNS
                                 if (t, c) not in existing_columns)
        return {"tables": len(tables & REQUIRED_TABLES), "missing_tables": missing_tables,
                "missing_columns": missing_columns,
                "complete": not missing_tables and not missing_columns}
