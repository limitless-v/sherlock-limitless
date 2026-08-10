"""Ollama HTTP client — scaffold.

Optional, off by default. Only called after the search pipeline is
functional (roadmap section 18).
"""


class OllamaClient:
    """Minimal client for a local Ollama instance."""

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url
        self._model = model

    async def complete(self, prompt: str) -> str:
        raise NotImplementedError