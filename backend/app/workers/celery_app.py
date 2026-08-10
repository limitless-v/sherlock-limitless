"""Celery application (optional workers) — scaffold."""

# from celery import Celery
# celery_app = Celery("face_search", broker=..., backend=...)

celery_app = None  # type: ignore
