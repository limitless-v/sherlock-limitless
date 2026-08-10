"""Event loop configuration for Windows.

psycopg (async) cannot run on the default Windows ProactorEventLoop,
so the app forces the SelectorEventLoop policy on win32. Without this,
any async DB access raises:
  Psycopg cannot use the 'ProactorEventLoop' to run in async mode.
"""

import asyncio
import sys


def configure_event_loop() -> None:
    """Install the SelectorEventLoop policy when running on Windows."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())