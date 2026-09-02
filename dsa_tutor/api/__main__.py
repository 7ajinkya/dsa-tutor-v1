"""Run the Slice 1B HTTP API: python -m dsa_tutor.api [--offline] [--host H] [--port P]."""
from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="dsa_tutor.api", description="DSA Tutor HTTP API (Slice 1B)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--offline", action="store_true",
                        help="in-memory storage demo server (no MySQL persistence)")
    parser.add_argument("--cors-origins", default=None,
                        help="comma-separated allowed origins (default: local Vite dev origins)")
    args = parser.parse_args()

    from dsa_tutor.api.app import create_app
    from dsa_tutor.config import load_config
    from dsa_tutor.persistence.memory_repositories import MemoryStorage

    if args.offline:
        config = load_config()
        service = __import__("dsa_tutor.app.service", fromlist=["TutorService"]).TutorService(
            MemoryStorage(), config)
        app = create_app(service=service, config=config)
    else:
        app = create_app()

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
