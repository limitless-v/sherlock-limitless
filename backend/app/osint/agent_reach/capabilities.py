"""Agent Reach capability detection (roadmap Phase 12 / 18).

Runs `agent-reach doctor --json` and reflects the real CLI state: which
channels are configured and which backend serves each. The doctor JSON
shape is channel-implementation specific, so extraction is tolerant and
never assumes a fixed key layout. When the CLI is missing, the capability
snapshot defaults to available=False with a human reason.
"""

from __future__ import annotations


def _flatten_channel_names(data: dict) -> list[str]:
    """Best-effort collection of channel names/sources from doctor output."""
    names: list[str] = []
    candidates = (
        data.get("channels"),
        data.get("sources"),
        data.get("report"),
        data.get("channel_status"),
    )
    for group in candidates:
        if isinstance(group, dict):
            names.extend(str(key) for key in group if key not in names)
        elif isinstance(group, list):
            for entry in group:
                if isinstance(entry, dict):
                    name = entry.get("name") or entry.get("channel") or entry.get("id")
                    if name:
                        names.append(str(name))
                elif isinstance(entry, str):
                    names.append(entry)
    return names


class AgentReachCapabilities:
    """Runtime capability snapshot for the Agent Reach client."""

    def __init__(self) -> None:
        self.available: bool = False
        self.sources: list[str] = []
        self.operations: list[str] = []
        self.reason: str = "agent-reach CLI not installed"

    def refresh(self, client) -> None:
        """Query the client and populate this capability snapshot."""
        if not client.is_available():
            self.available = False
            self.reason = "agent-reach CLI not installed"
            return
        try:
            data = client.doctor_json()
        except Exception as exc:  # CLI present but unusable -> degraded, not fatal
            self.available = False
            self.reason = f"agent-reach doctor failed: {exc}"
            return
        self.sources = _flatten_channel_names(data) or []
        self.operations = sorted(
            {str(v.get("active_backend", v.get("backend", name))) for name, v in data.items() if isinstance(v, dict)}
        )
        self.available = True
        self.reason = ""

    def supports(self, source: str) -> bool:
        return source in self.sources