"""Structured logging configuration."""

import sys

from loguru import logger

from app.config.settings import get_settings


def configure_logging() -> None:
    """Configure loguru sinks and levels from settings."""
    settings = get_settings()
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        serialize=settings.log_json,
        backtrace=settings.debug,
        diagnose=settings.debug,
    )
    if settings.log_file:
        logger.add(
            settings.log_file,
            level=settings.log_level,
            rotation="10 MB",
            retention="14 days",
            serialize=settings.log_json,
        )


def get_logger():
    """Return configured logger instance."""
    return logger
