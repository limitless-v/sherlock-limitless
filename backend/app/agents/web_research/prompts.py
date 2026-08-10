"""Prompts for the optional LLM planner (roadmap Phase 26).

Not used by the deterministic planner; reserved for when an optional LLM is
wired to choose tool sequences. Kept small and non-sensitive — prompts never
carry face embeddings or identity assertions.
"""

PLANNER_SYSTEM_PROMPT = (
    "You choose which research tools to run for a public candidate page. "
    "Tools: fetch_page, extract_metadata, extract_text, extract_links, "
    "extract_images, find_public_profile_links, find_external_profiles. "
    "Return only tool names in order."
)