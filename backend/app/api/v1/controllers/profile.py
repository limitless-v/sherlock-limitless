"""Matched profile detail endpoints (scaffold)."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.search import ProfileDetailRead

router = APIRouter(prefix="/profile")


@router.get("/{profile_id}", response_model=ProfileDetailRead)
async def get_profile(profile_id: int) -> ProfileDetailRead:
    """Return aggregated public profile metadata for a match."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Profile detail not implemented",
    )
