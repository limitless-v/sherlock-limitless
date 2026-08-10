"""Agent Reach output parser (roadmap Phase 18).

Tolerant parsing of `agent-reach` CLI output. The CLI's JSON shape is
channel-implementation specific and may evolve, so nothing is assumed
beyond the documented facts: `doctor --json` emits a JSON object and every
`get` read accepts `--json`. Malformed bytes degrade to `[]`/`{}` with a
descriptive error instead of crashing the pipeline.
"""

from __future__ import annotations

import json


class AgentReachParseError(ValueError):
    """The agent-reach CLI returned unusable output."""


def parse_json(text: str, *, allow_list: bool = False):
    """Parse CLI JSON, raising AgentReachParseError when unusable."""
    try:
        payload = json.loads(text or "{}")
    except json.JSONDecodeError as exc:
        raise AgentReachParseError("agent-reach produced no machine-readable JSON.") from exc
    if not allow_list and not isinstance(payload, dict):
        raise AgentReachParseError("agent-reach --json output is not a JSON object.")
    return payload


def parse_doctor(text: str) -> dict:
    """Parse `agent-reach doctor --json` into a dict (empty on failure)."""
    try:
        return parse_json(text)
    except AgentReachParseError:
        return {}


def extract_records(text: str) -> list[dict]:
    """Pull candidate records out of a `get --json` response, tolerating shapes."""
    try:
        payload = parse_json(text, allow_list=True)
    except AgentReachParseError:
        return []
    if isinstance(payload, list):
        candidates = payload
    elif isinstance(payload, dict):
        candidates = (
            payload.get("results")
            or payload.get("candidates")
            or payload.get("links")
            or payload.get("items")
            or payload.get("data")
        )
    else:
        candidates = None
    return [item for item in (candidates or []) if isinstance(item, dict)]