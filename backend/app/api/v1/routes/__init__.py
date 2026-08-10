"""API v1 route aggregation."""

from fastapi import APIRouter

from app.api.v1.controllers import auth, history, profile, search, upload

router = APIRouter()

router.include_router(upload.router, tags=["upload"])
router.include_router(search.router, tags=["search"])
router.include_router(history.router, tags=["history"])
router.include_router(profile.router, tags=["profile"])
router.include_router(auth.router, tags=["auth"])
