"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root = backend/app/config/settings.py -> parents[3]
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Central configuration for API, AI, storage, and security."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="Face Search OSINT Platform", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    cors_origins: str = Field(
        default="http://localhost:3000",
        alias="CORS_ORIGINS",
    )
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")

    database_url: str = Field(
        alias="DATABASE_URL",
    )

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    storage_uploads: str = Field(default="uploads", alias="STORAGE_UPLOADS")
    storage_cache: str = Field(default="cache", alias="STORAGE_CACHE")
    storage_embeddings: str = Field(default="embeddings", alias="STORAGE_EMBEDDINGS")
    storage_results: str = Field(default="results", alias="STORAGE_RESULTS")
    storage_logs: str = Field(default="logs", alias="STORAGE_LOGS")
    storage_models: str = Field(default="models", alias="STORAGE_MODELS")

    max_upload_size_mb: int = Field(default=10, alias="MAX_UPLOAD_SIZE_MB")
    allowed_image_mime_types: str = Field(
        default="image/jpeg,image/png,image/webp",
        alias="ALLOWED_IMAGE_MIME_TYPES",
    )
    max_image_dimension: int = Field(default=4096, alias="MAX_IMAGE_DIMENSION")

    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")

    ai_device: str = Field(default="cpu", alias="AI_DEVICE")
    ai_use_gpu: bool = Field(default=False, alias="AI_USE_GPU")
    ai_model_cache: bool = Field(default=True, alias="AI_MODEL_CACHE")
    ai_lazy_load: bool = Field(default=True, alias="AI_LAZY_LOAD")
    insightface_model: str = Field(default="buffalo_l", alias="INSIGHTFACE_MODEL")
    face_det_confidence: float = Field(default=0.5, alias="FACE_DET_CONFIDENCE")
    embedding_dim: int = Field(default=512, alias="EMBEDDING_DIM")
    similarity_threshold: float = Field(default=0.6, alias="SIMILARITY_THRESHOLD")
    faiss_index_path: str = Field(default="embeddings/faiss.index", alias="FAISS_INDEX_PATH")
    faiss_top_k: int = Field(default=20, alias="FAISS_TOP_K")

    search_default_mode: str = Field(default="internet", alias="SEARCH_DEFAULT_MODE")
    search_max_results: int = Field(default=50, alias="SEARCH_MAX_RESULTS")

    agent_reach_enabled: bool = Field(default=False, alias="AGENT_REACH_ENABLED")
    agent_reach_timeout_seconds: int = Field(default=30, alias="AGENT_REACH_TIMEOUT_SECONDS")
    agent_reach_max_candidates: int = Field(default=10, alias="AGENT_REACH_MAX_CANDIDATES")

    ollama_enabled: bool = Field(default=False, alias="OLLAMA_ENABLED")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3", alias="OLLAMA_MODEL")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=False, alias="LOG_JSON")
    log_file: str = Field(default="logs/app.log", alias="LOG_FILE")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_mime_types_list(self) -> list[str]:
        return [m.strip() for m in self.allowed_image_mime_types.split(",") if m.strip()]

    @property
    def uploads_dir(self) -> Path:
        """Absolute uploads directory, anchored to the project root."""
        return PROJECT_ROOT / self.storage_uploads

    @property
    def cache_dir(self) -> Path:
        return PROJECT_ROOT / self.storage_cache

    @property
    def embeddings_dir(self) -> Path:
        return PROJECT_ROOT / self.storage_embeddings

    @property
    def results_dir(self) -> Path:
        return PROJECT_ROOT / self.storage_results

    @property
    def logs_dir(self) -> Path:
        return PROJECT_ROOT / self.storage_logs

    @property
    def models_dir(self) -> Path:
        return PROJECT_ROOT / self.storage_models

    @property
    def face_model_pack_dir(self) -> Path:
        """Directory holding a downloaded InsightFace model pack.

        FaceAnalysis stores packs under <models_root>/models/<pack_name>.
        Shared by face detection and face embedding.
        """
        return self.models_dir / "models" / self.insightface_model

    @property
    def faces_dir(self) -> Path:
        """Directory for persisted face embeddings (relative paths stored in DB)."""
        return self.embeddings_dir / "faces"

    @property
    def face_crops_dir(self) -> Path:
        """Directory for persisted aligned face crops."""
        return self.cache_dir / "faces"

    @property
    def faiss_index_abs(self) -> Path:
        return PROJECT_ROOT / self.faiss_index_path


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton for dependency injection."""
    return Settings()
