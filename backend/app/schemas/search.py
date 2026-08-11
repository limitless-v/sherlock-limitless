"""Pydantic request/response schemas (scaffold)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.search.modes import SearchMode


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Auth ---


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRead(ORMModel):
    id: int
    email: EmailStr
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Search ---


class SearchCreateRequest(BaseModel):
    """POST /api/v1/search body (roadmap section 11)."""

    image_id: UUID
    mode: SearchMode = SearchMode.INTERNET
    max_results: int = Field(default=50, ge=1, le=200)
    sources: list[str] = Field(default_factory=list)
    user_id: int | None = None
    uploaded_image: str | None = None


class SearchResultRead(ORMModel):
    """One normalized result entry (roadmap section 12-13)."""

    id: str
    source: str
    url: str
    title: str = ""
    username: str = ""
    display_name: str = ""
    image_urls: list[str] = Field(default_factory=list)
    text: str = ""
    discovery_method: str = ""
    face_similarity: float = 0.0
    confidence: str = "low"
    discovered_at: datetime | None = None
    location: str | None = None
    date: str | None = None
    profiles: list[dict] = Field(default_factory=list)


class SearchResponseRead(ORMModel):
    """Normalized search response shared by all modes."""

    search_id: str
    mode: SearchMode
    status: str = "completed"
    results: list[SearchResultRead] = Field(default_factory=list)
    providers: dict[str, dict] = Field(default_factory=dict)
    ranked_evidence: list[dict] | None = None


class SearchCreateResponse(BaseModel):
    search_id: int
    status: str = "pending"


class MatchedProfileRead(ORMModel):
    id: int
    platform: str
    profile_url: str
    image_url: str | None
    confidence: float


class DetectedFaceRead(ORMModel):
    id: int
    face_image: str
    embedding_path: str | None
    matched_profiles: list[MatchedProfileRead] = Field(default_factory=list)


class SearchDetailRead(ORMModel):
    id: int
    uploaded_image: str
    created_at: datetime
    detected_faces: list[DetectedFaceRead] = Field(default_factory=list)
    matched_profiles: list[MatchedProfileRead] = Field(default_factory=list)
    mode: str = ""
    status: str = ""
    providers: dict[str, dict] = Field(default_factory=dict)
    ranked_evidence: list[dict] | None = None


class SearchHistoryItem(ORMModel):
    id: int
    uploaded_image: str
    created_at: datetime
    mode: str = ""
    status: str = ""


class SearchHistoryRead(BaseModel):
    """Paginated search history response."""
    items: list[SearchHistoryItem]
    total: int
    page: int
    page_size: int


class ProfileDetailRead(ORMModel):
    id: int
    platform: str
    profile_url: str
    image_url: str | None
    confidence: float
    candidate_images: list[str] = Field(default_factory=list)


class SearchEvidenceRead(BaseModel):
    """Evidence graph for a search."""
    search_id: int
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
