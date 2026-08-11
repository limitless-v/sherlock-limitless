"""ORM models — schema definitions (implementation pending)."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func, JSON
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class User(Base):
    """Application user."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    search_history: Mapped[list["SearchHistory"]] = relationship(back_populates="user")
    searches: Mapped[list["Search"]] = relationship(back_populates="user")


class SearchHistory(Base):
    """One face search job initiated by a user."""

    __tablename__ = "search_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    uploaded_image: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User | None"] = relationship(back_populates="search_history")
    detected_faces: Mapped[list["DetectedFace"]] = relationship(back_populates="search")
    candidates: Mapped[list["Candidate"]] = relationship(back_populates="search", cascade="all, delete-orphan")
    evidence_nodes: Mapped[list["EvidenceNode"]] = relationship(back_populates="search", cascade="all, delete-orphan")
    evidence_edges: Mapped[list["EvidenceEdge"]] = relationship(back_populates="search", cascade="all, delete-orphan")


class DetectedFace(Base):
    """Face crop detected from an uploaded image."""

    __tablename__ = "detected_faces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_id: Mapped[int] = mapped_column(ForeignKey("search_history.id"), index=True)
    face_image: Mapped[str] = mapped_column(String(512), nullable=False)
    embedding_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    search: Mapped["SearchHistory"] = relationship(back_populates="detected_faces")
    matched_profiles: Mapped[list["MatchedProfile"]] = relationship(back_populates="face")


class MatchedProfile(Base):
    """Public profile candidate linked to a detected face."""

    __tablename__ = "matched_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    face_id: Mapped[int] = mapped_column(ForeignKey("detected_faces.id"), index=True)
    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_url: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    face: Mapped["DetectedFace"] = relationship(back_populates="matched_profiles")
    candidate_images: Mapped[list["CandidateImage"]] = relationship(back_populates="profile")


class CandidateImage(Base):
    """Downloaded image used to verify a matched profile."""

    __tablename__ = "candidate_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("matched_profiles.id"), index=True)
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    embedding_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    profile: Mapped["MatchedProfile"] = relationship(back_populates="candidate_images")


class Candidate(Base):
    """Normalized candidate page from web research."""

    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_id: Mapped[int] = mapped_column(ForeignKey("search_history.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    candidate_metadata: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    search: Mapped["SearchHistory"] = relationship(back_populates="candidates")
    images: Mapped[list["CandidateExtractedImage"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    profiles: Mapped[list["CandidateProfile"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    locations: Mapped[list["CandidateLocation"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    dates: Mapped[list["CandidateDate"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")


class CandidateExtractedImage(Base):
    """Image extracted from a candidate page."""

    __tablename__ = "candidate_extracted_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    local_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    a_hash: Mapped[str | None] = mapped_column(String(16), nullable=True)
    d_hash: Mapped[str | None] = mapped_column(String(16), nullable=True)
    p_hash: Mapped[str | None] = mapped_column(String(16), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    correlation_classification: Mapped[str | None] = mapped_column(String(50), nullable=True)
    correlation_hamming_distance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    face_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    correlation_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    correlated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    candidate: Mapped["Candidate"] = relationship(back_populates="images")


class CandidateProfile(Base):
    """Public profile link extracted from a candidate page."""

    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    profile_url: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str] = mapped_column(String(100), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    candidate: Mapped["Candidate"] = relationship(back_populates="profiles")


class CandidateLocation(Base):
    """Location extracted from a candidate page."""

    __tablename__ = "candidate_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    location: Mapped[str] = mapped_column(String(512), nullable=False)
    location_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    candidate: Mapped["Candidate"] = relationship(back_populates="locations")


class CandidateDate(Base):
    """Date/timestamp extracted from a candidate page."""

    __tablename__ = "candidate_dates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    date_value: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    date_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    candidate: Mapped["Candidate"] = relationship(back_populates="dates")


class EvidenceNode(Base):
    """Node in the evidence graph."""

    __tablename__ = "evidence_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_id: Mapped[int] = mapped_column(ForeignKey("search_history.id", ondelete="CASCADE"), index=True)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_value: Mapped[str] = mapped_column(Text, nullable=False)
    attributes: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_evidence_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    search: Mapped["SearchHistory"] = relationship(back_populates="evidence_nodes")
    outgoing_edges: Mapped[list["EvidenceEdge"]] = relationship(
        foreign_keys="EvidenceEdge.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[list["EvidenceEdge"]] = relationship(
        foreign_keys="EvidenceEdge.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan",
    )


class EvidenceEdge(Base):
    """Edge in the evidence graph."""

    __tablename__ = "evidence_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_id: Mapped[int] = mapped_column(ForeignKey("search_history.id", ondelete="CASCADE"), index=True)
    source_node_id: Mapped[int] = mapped_column(ForeignKey("evidence_nodes.id", ondelete="CASCADE"), index=True)
    target_node_id: Mapped[int] = mapped_column(ForeignKey("evidence_nodes.id", ondelete="CASCADE"), index=True)
    edge_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_evidence_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    edge_metadata: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    search: Mapped["SearchHistory"] = relationship(back_populates="evidence_edges")
    source_node: Mapped["EvidenceNode"] = relationship(
        foreign_keys=[source_node_id],
        back_populates="outgoing_edges",
    )
    target_node: Mapped["EvidenceNode"] = relationship(
        foreign_keys=[target_node_id],
        back_populates="incoming_edges",
    )


class Search(Base):
    """Search job record with results and evidence."""

    __tablename__ = "searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    image_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    uploaded_image: Mapped[str] = mapped_column(String(512), nullable=False)
    providers: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    ranked_evidence: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    sources_checked: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    pages_analyzed: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    total_candidates: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    total_evidence: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User | None"] = relationship()
    events: Mapped[list["SearchEvent"]] = relationship(back_populates="search", cascade="all, delete-orphan")


class SearchEvent(Base):
    """SSE event for live search progress."""

    __tablename__ = "search_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_id: Mapped[int] = mapped_column(ForeignKey("searches.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    search: Mapped["Search"] = relationship(back_populates="events")
