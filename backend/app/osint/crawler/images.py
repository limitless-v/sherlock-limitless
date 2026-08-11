"""Candidate image download and caching (roadmap Phase 25).

Implements real image downloading with:
- URL validation (http/https only)
- SSRF protection
- Request timeout
- Content-Type validation (image/*)
- Image size limits
- Maximum images per candidate
"""

from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path
from typing import Optional

import httpx
from PIL import Image

from app.agents.web_research.policies import UrlGuard
from app.config.settings import Settings


class CandidateCrawlerError(Exception):
    """Base exception for crawler errors."""
    pass


class InvalidURLError(CandidateCrawlerError):
    """Raised when URL fails validation."""
    pass


class SSRFError(CandidateCrawlerError):
    """Raised when URL is blocked by SSRF guard."""
    pass


class ContentTypeError(CandidateCrawlerError):
    """Raised when content type is not an image."""
    pass


class ImageSizeError(CandidateCrawlerError):
    """Raised when image exceeds size limit."""
    pass


class DownloadError(CandidateCrawlerError):
    """Raised when download fails."""
    pass


class CandidateCrawler:
    """Download candidate images for local face verification and correlation."""

    def __init__(
        self,
        settings: Settings | None = None,
        url_guard: UrlGuard | None = None,
        max_images_per_candidate: int = 5,
    ) -> None:
        self._settings = settings or Settings()
        self._url_guard = url_guard or UrlGuard(
            allow_domains=tuple(
                d.strip().lower() for d in self._settings.agent_allow_domains.split(",") if d.strip()
            )
        )
        self._max_images_per_candidate = max_images_per_candidate
        self._client: httpx.AsyncClient | None = None
        self._downloads_dir = self._settings.cache_dir / "candidate_images"
        self._downloads_dir.mkdir(parents=True, exist_ok=True)

    async def __aenter__(self) -> "CandidateCrawler":
        self._client = httpx.AsyncClient(
            timeout=self._settings.agent_http_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": self._settings.http_user_agent},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("CandidateCrawler must be used as async context manager")
        return self._client

    def _generate_filename(self, url: str, content_type: str) -> str:
        """Generate a unique filename for the downloaded image."""
        # Use SHA256 of URL for uniqueness
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        # Determine extension from content type
        ext_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "image/bmp": ".bmp",
            "image/tiff": ".tiff",
        }
        ext = ext_map.get(content_type, ".jpg")
        return f"{url_hash}{ext}"

    def _validate_url(self, url: str) -> tuple[bool, str]:
        """Validate URL scheme and SSRF protection."""
        allowed, reason = self._url_guard.check(url)
        if not allowed:
            return False, reason
        return True, ""

    async def fetch_image(self, url: str, candidate_id: int, image_index: int = 0) -> dict:
        """Download and validate an image from a URL.

        Args:
            url: Image URL to download
            candidate_id: Database ID of the candidate this image belongs to
            image_index: Index of this image for the candidate (for ordering)

        Returns:
            Dict with download info: local_path, sha256, width, height, content_type, file_size

        Raises:
            CandidateCrawlerError: On validation or download failure
        """
        # Validate URL
        allowed, reason = self._validate_url(url)
        if not allowed:
            raise SSRFError(f"URL blocked: {reason}")

        # Check image index limit
        if image_index >= self._max_images_per_candidate:
            raise CandidateCrawlerError(f"Max images per candidate ({self._max_images_per_candidate}) exceeded")

        # Download with timeout
        try:
            response = await self.client.get(url, timeout=self._settings.agent_http_timeout_seconds)
            response.raise_for_status()
        except httpx.TimeoutException:
            raise DownloadError(f"Download timeout after {self._settings.agent_http_timeout_seconds}s")
        except httpx.HTTPStatusError as e:
            raise DownloadError(f"HTTP {e.response.status_code}: {e.response.reason_phrase}")
        except httpx.RequestError as e:
            raise DownloadError(f"Request failed: {e}")

        # Validate content type
        content_type = response.headers.get("content-type", "").lower()
        if not content_type.startswith("image/"):
            raise ContentTypeError(f"Invalid content type: {content_type} (expected image/*)")

        # Check file size limit (10MB default)
        content_length = response.headers.get("content-length")
        max_size = self._settings.crawler_max_image_size_mb * 1024 * 1024
        if content_length and int(content_length) > max_size:
            raise ImageSizeError(f"Image too large: {content_length} bytes (max {max_size})")

        # Read content and check actual size
        content = response.content
        if len(content) > max_size:
            raise ImageSizeError(f"Image too large: {len(content)} bytes (max {max_size})")

        # Validate image with PIL
        try:
            img = Image.open(BytesIO(content))
            img.verify()  # Verify integrity
            img = Image.open(BytesIO(content))  # Reopen after verify
            width, height = img.size
            img_format = img.format
        except Exception as e:
            raise DownloadError(f"Invalid image file: {e}")

        # Check dimensions
        if width > self._settings.max_image_dimension or height > self._settings.max_image_dimension:
            raise ImageSizeError(f"Image dimensions too large: {width}x{height} (max {self._settings.max_image_dimension})")

        # Compute SHA256
        sha256 = hashlib.sha256(content).hexdigest()

        # Generate filename and save
        filename = self._generate_filename(url, content_type)
        local_path = self._downloads_dir / filename
        
        # Save image
        try:
            with open(local_path, "wb") as f:
                f.write(content)
        except OSError as e:
            raise DownloadError(f"Failed to save image: {e}")

        return {
            "local_path": str(local_path),
            "sha256": sha256,
            "width": width,
            "height": height,
            "content_type": content_type,
            "file_size": len(content),
            "image_format": img_format,
        }

    async def fetch_images_batch(self, urls: list[str], candidate_id: int) -> list[dict]:
        """Download multiple images for a candidate.

        Args:
            urls: List of image URLs
            candidate_id: Database ID of the candidate

        Returns:
            List of download info dicts (failed downloads omitted with error logged)
        """
        results = []
        for idx, url in enumerate(urls[:self._max_images_per_candidate]):
            try:
                result = await self.fetch_image(url, candidate_id, idx)
                results.append({"url": url, "success": True, **result})
            except CandidateCrawlerError as e:
                results.append({"url": url, "success": False, "error": str(e)})
        return results