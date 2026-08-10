"""Profile summarization and information extraction — scaffold.

Good uses: profile summarization, evidence organization, duplicate
explanation, natural-language reports. Never used for face operations.
"""

from app.llm.ollama_client import OllamaClient


class Summarizer:
    """Turn search results into a human-readable summary / report."""

    def __init__(self, client: OllamaClient) -> None:
        self._client = client

    async def summarize(self, results: list, entity_id: str) -> str:
        raise NotImplementedError