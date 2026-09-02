"""CLI entrypoint: python -m dsa_tutor <command>"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .app.service import TutorService
from .config import PROJECT_ROOT, load_config
from .domain.models import Pace
from .logging_conf import setup_logging


def _build_service(offline: bool, require_schema: bool = True):
    config = load_config()
    logfile = setup_logging(config.log_level, str(PROJECT_ROOT / config.log_dir))
    if offline:
        from .persistence.memory_repositories import MemoryStorage
        return TutorService(MemoryStorage(), config), config, logfile
    from .persistence.db import Database
    from .persistence.repositories import MySQLStorage
    database = Database(config.database)
    ok, detail = database.healthcheck()
    if not ok:
        print(f"MySQL unavailable: {detail}")
        print("Run 'python -m dsa_tutor setup-db' after configuring .env "
              "(see .env.example), or use --offline for a non-persistent demo session.")
        sys.exit(2)
    if require_schema:
        report = database.schema_report()
        if not report["complete"]:
            print(f"Schema incomplete — missing: {report['missing_tables'] + report['missing_columns']}")
            print("Run: python -m dsa_tutor setup-db")
            sys.exit(2)
    return TutorService(MySQLStorage(database), config), config, logfile


def cmd_setup_db(args) -> int:
    config = load_config()
    setup_logging(config.log_level, str(PROJECT_ROOT / config.log_dir))
    from pathlib import Path
    from .persistence.db import Database
    from .persistence.seed import seed_curriculum
    database = Database(config.database)
    schema_path = Path(__file__).parent / "persistence" / "schema.sql"
    print(f"Installing schema on {config.database.host}:{config.database.port} "
          f"(database '{config.database.name}' created if missing) ...")
    report = database.install_schema(schema_path.read_text(encoding="utf-8"))
    if report["complete"]:
        print(f"Schema ready: {report['tables']} expected tables present, no missing columns")
    else:
        print(f"Schema INCOMPLETE: missing tables={report['missing_tables']} "
              f"columns={report['missing_columns']}")
        return 2
    counts = seed_curriculum(database)
    print("Curriculum seeded:", counts)
    ok, detail = database.healthcheck()
    print(f"Healthcheck: {detail}" if ok else f"FAILED: {detail}")
    return 0 if ok and report["complete"] else 2


def cmd_check(args) -> int:
    config = load_config()
    errors = config.validate()
    print("Configuration:", "OK" if not errors else "INVALID")
    for e in errors:
        print(f"  - {e}")
    service, _, logfile = _build_service(offline=args.offline, require_schema=False)
    print(f"Curriculum: {len(service.curriculum.skills)} skills, {len(service.curriculum.units)} units, "
          f"{len(service.curriculum.exercises)} exercises — valid")
    if not args.offline:
        report = service.storage.db.schema_report()
        print(f"MySQL schema: {report['tables']} expected tables, "
              f"{'complete' if report['complete'] else 'INCOMPLETE — run setup-db'}")
    external = getattr(service.ai, "external", service.ai)
    usage = getattr(external, "usage", None)
    if usage is not None:
        s = usage.status()
        state = "LIMIT REACHED — offline tutor active until reset" if usage.exhausted() \
            else "within budget"
        print(f"External AI usage today: {s['used']}/{s['limit']} requests ({state})")
    print(f"AI provider: {config.ai.provider}"
          + (f" (model {config.ai.model})" if config.ai.provider != "builtin" else " (offline, AutoClaw-authored)"))
    print(f"Logs: {logfile}")
    return 1 if errors else 0


def cmd_start(args) -> int:
    service, config, _ = _build_service(offline=args.offline, require_schema=not args.offline)
    pace = Pace(args.pace)
    from .app.interactive import run_session
    run_session(service, pace, resume=args.resume)
    return 0


def cmd_progress(args) -> int:
    service, _, _ = _build_service(offline=args.offline, require_schema=not args.offline)
    from .app.interactive import render_progress
    print(render_progress(service.progress_report()))
    return 0


def cmd_reset_progress(args) -> int:
    config = load_config()
    setup_logging(config.log_level, str(PROJECT_ROOT / config.log_dir))
    from .persistence.db import Database
    from .persistence.repositories import MySQLStorage
    database = Database(config.database)
    storage = MySQLStorage(database)
    learner = storage.get_or_create_learner("local_learner")
    with database.transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM assessment_evidence WHERE learner_id=%s", (learner.id,))
            cur.execute("DELETE FROM attempts WHERE learner_id=%s", (learner.id,))
            cur.execute("DELETE FROM session_events WHERE session_id IN "
                        "(SELECT id FROM sessions WHERE learner_id=%s)", (learner.id,))
            cur.execute("DELETE FROM sessions WHERE learner_id=%s", (learner.id,))
            cur.execute("DELETE FROM skill_assessments WHERE learner_id=%s", (learner.id,))
            cur.execute("DELETE FROM learner_state WHERE learner_id=%s", (learner.id,))
            cur.execute("DELETE FROM daily_plans WHERE learner_id=%s", (learner.id,))
    print(f"Progress wiped for learner '{learner.name}' — next session starts fresh. "
          "Curriculum content is untouched.")
    return 0


def cmd_export_session(args) -> int:
    service, _, _ = _build_service(offline=args.offline, require_schema=not args.offline)
    try:
        path = service.export_last_session()
    except RuntimeError as exc:
        print(exc)
        return 1
    print(f"Session transcript written: {path}")
    print("Drop this file into a chat with AutoClaw for a rich human-style review "
          "— reasoning, misconceptions, hint usage.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="dsa_tutor",
                                     description="Local adaptive DSA tutor (V0: Graphs, BFS, DFS)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="start (or resume) a learning session")
    p_start.add_argument("--pace", choices=[p.value for p in Pace], default="normal")
    p_start.add_argument("--resume", action="store_true", help="resume the persisted session")
    p_start.add_argument("--offline", action="store_true",
                         help="in-memory demo mode (no MySQL persistence)")
    p_start.set_defaults(func=cmd_start)

    p_progress = sub.add_parser("progress", help="show mastery report")
    p_progress.add_argument("--offline", action="store_true")
    p_progress.set_defaults(func=cmd_progress)

    sub.add_parser("setup-db", help="create schema and seed the V0 curriculum").set_defaults(func=cmd_setup_db)

    sub.add_parser("reset-progress", help="wipe learner progress (keeps curriculum)").set_defaults(func=cmd_reset_progress)

    p_export = sub.add_parser("export-session", help="write the latest session as a markdown transcript for AutoClaw review")
    p_export.add_argument("--offline", action="store_true")
    p_export.set_defaults(func=cmd_export_session)

    p_check = sub.add_parser("check", help="verify configuration, DB, curriculum, AI provider")
    p_check.add_argument("--offline", action="store_true")
    p_check.set_defaults(func=cmd_check)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
