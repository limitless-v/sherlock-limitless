"""Agent Reach adapter — CLI wrapper.

Wraps the installed `agent-reach` CLI (github.com/Panniantong/Agent-Reach)
behind a narrow interface:

    agent-reach doctor --json            -> capability probe
    agent-reach get <channel.query> ...  -> reads (with --json)

The CLI is optional: when it is not installed the client reports
`is_available() == False` and every public operation raises
`AgentReachUnavailableError` — this must never be a fatal application error.

Agent Reach is a web-access/discovery provider, not the identity engine.
Returned data is normalized into app.discovery.schemas.Candidate by
`normalizer.py`; Agent Reach-specific structures stay inside this package.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.osint.agent_reach.normalizer import normalize_records
from app.osint.agent_reach.parser import extract_records, parse_json

_TIMEOUT_SECONDS = 30


class AgentReachError(RuntimeError):
    """The agent-reach CLI ran but failed/returned unusable output."""


class AgentReachUnavailableError(AgentReachError):
    """The agent-reach CLI is not installed / not usable."""


def _which_cli(candidate: str | None) -> str | None:
    if candidate:
        return candidate if Path(candidate).is_file() else None
    return shutil.which("agent-reach")


class AgentReachClient:
    """Thin subprocess wrapper around the `agent-reach` CLI."""

    def __init__(
        self,
        cmd: str | None = None,
        timeout_seconds: float = _TIMEOUT_SECONDS,
        search_channel: str = "exa.search",
    ) -> None:
        self._cmd = cmd
        self._timeout = timeout_seconds
        self._search_channel = search_channel
        self._cli: str | None = None

    @property
    def cli_path(self) -> str | None:
        """Resolved CLI path (cached); None when the CLI is not installed."""
        if self._cli is None:
            self._cli = _which_cli(self._cmd)
        return self._cli

    def is_available(self) -> bool:
        """True when the `agent-reach` CLI binary is on PATH (or configured)."""
        return self.cli_path is not None

    def run(self, args: list[str]) -> str:
        """Run `agent-reach <args>` and return stdout; raise when unusable."""
        cli = self.cli_path
        if cli is None:
            raise AgentReachUnavailableError("agent-reach CLI is not installed.")
        try:
            proc = subprocess.run(
                [cli, *args],
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AgentReachError(f"agent-reach invocation failed: {exc}") from exc
        return proc.stdout

    def doctor_json(self) -> dict:
        """Return the parsed `agent-reach doctor --json` output."""
        return parse_json(self.run(["doctor", "--json"]))

    def discover(self, query: str, sources: list[str] | None = None) -> list[dict]:
        """Run a `get` read for `query` and return normalized candidates.

        URL queries read through the `web.<url>` channel; keyword queries use
        the configured search channel (`AGENT_REACH_SEARCH_CHANNEL`). The
        CLI's JSON shape varies per channel; records are extracted tolerantly
        and normalized to `Candidate` by the normalizer.
        """
        url = query.strip() if query.startswith(("http://", "https://")) else None
        channel = f"web.{url}" if url else self._search_channel
        out = self.run(["get", channel, query, "--json"])
        return normalize_records(extract_records(out))