"""Search mode definition (roadmap section 6)."""

from enum import Enum


class SearchMode(str, Enum):
    """Supported search strategies.

    LOCAL    — search only the locally indexed face database (FAISS).
    INTERNET — discover public profiles through Agent Reach (first-class).
    HYBRID   — combine LOCAL and INTERNET independently.
    """

    LOCAL = "local"
    INTERNET = "internet"
    HYBRID = "hybrid"
