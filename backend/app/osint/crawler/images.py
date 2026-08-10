"""Candidate image download and caching — scaffold."""


class CandidateCrawler:
    """Download candidate images for local face verification."""

    async def fetch_image(self, url: str, dest_path: str) -> str:
        raise NotImplementedError
