"""Dependency injection package."""

from app.dependencies.container import (
    get_search_service,
    get_settings_dep,
    get_upload_service,
)

__all__ = ["get_settings_dep", "get_upload_service", "get_search_service"]
