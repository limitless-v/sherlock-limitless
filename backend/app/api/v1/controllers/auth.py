"""Authentication endpoints (scaffold)."""

from fastapi import APIRouter, status

from app.schemas.search import TokenResponse, UserCreate, UserRead

router = APIRouter(prefix="/auth")


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate) -> UserRead:
    """Register a new user (implementation pending)."""
    raise NotImplementedError


@router.post("/login", response_model=TokenResponse)
async def login() -> TokenResponse:
    """Issue JWT access token (implementation pending)."""
    raise NotImplementedError
