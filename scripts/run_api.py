#!/usr/bin/env python3
"""Development API server launcher for Windows.

Async psycopg requires a SelectorEventLoop, but uvicorn's normal CLI path
creates a Proactor loop before the app import. Set the Selector policy at
the top of this module (the reloader re-imports this script in its child
processes, so the policy is preserved) and then run uvicorn normally.

Run from the repository root or backend/:
    python scripts/run_api.py
"""

import argparse
import asyncio
import sys
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import uvicorn  # noqa: E402

from app.config.settings import get_settings  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", help="Override HOST from settings")
    parser.add_argument("--port", type=int, help="Override PORT from settings")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    args = parser.parse_args()

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=args.host or settings.host,
        port=args.port or settings.port,
        reload=not args.no_reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()