import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "Deepfake Shield"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "deepfake-shield-super-secure-jwt-secret-key-at-least-32-bytes-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database: Defaults to local SQLite async for instant zero-dependency execution,
    # and seamlessly connects to PostgreSQL asyncpg when configured in .env
    DATABASE_URL: str = "sqlite+aiosqlite:///./deepfake_shield.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    STORAGE_DIR: Path = Path("./storage")
    UPLOAD_DIR: Path = Path("./storage/uploads")
    MAX_UPLOAD_SIZE_MB: int = 250

    # Allowed File Extensions
    ALLOWED_AUDIO_EXTENSIONS: list[str] = [".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac"]
    ALLOWED_VIDEO_EXTENSIONS: list[str] = [".mp4", ".avi", ".mov", ".mkv", ".webm", ".webp", ".jpg", ".jpeg", ".png"]

    # ML Inference Device
    DEVICE: str = "cpu"  # 'cuda', 'cpu', 'mps'

    # Security Thresholds (Percentages 0.0 - 1.0)
    SYNTHETIC_SPEECH_THRESHOLD: float = 0.70
    SPATIAL_MANIPULATION_THRESHOLD: float = 0.65
    LIP_SYNC_THRESHOLD_MS: float = 80.0

    # Hugging Face Dataset API Integration
    HF_TOKEN: Optional[str] = None
    HF_DEFAULT_DATASET: str = "UniDataPro/deepfake-videos-dataset"
    HF_CACHE_TTL_SECONDS: int = 300  # 5 minutes
    HF_REQUEST_TIMEOUT_SECONDS: float = 15.0

    # Security, Rate Limiting & Data Retention
    RATE_LIMITING_ENABLED: bool = True
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 10
    RATE_LIMIT_INFERENCE_PER_MINUTE: int = 30
    RATE_LIMIT_GENERAL_PER_MINUTE: int = 120
    DATA_RETENTION_DAYS: int = 30
    ALLOWED_HOSTS: list[str] = ["*"]
    CORS_ORIGINS: list[str] = ["*"]

    @property
    def masked_hf_token(self) -> str:
        if not self.HF_TOKEN:
            return "Not Configured"
        if len(self.HF_TOKEN) <= 8:
            return "********"
        return f"{self.HF_TOKEN[:4]}...{self.HF_TOKEN[-4:]}"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ["production", "prod"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
