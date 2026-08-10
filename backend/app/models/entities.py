"""ORM models — schema definitions (implementation pending)."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
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
