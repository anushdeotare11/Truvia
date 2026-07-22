from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
from typing import Optional
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General App Config
    APP_NAME: str = "Truvia"
    ENV: str = "dev"  # dev, staging, production
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # CORS — comma-separated origins, or "*" for allow-all.
    # Vercel production URL is always included automatically in main.py.
    CORS_ORIGINS: str = Field(default="")
    FRONTEND_URL: str = Field(default="")

    # PostgreSQL Config
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/truvia"
    )

    # Redis Config
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Neo4j Config
    NEO4J_URI: str = Field(default="bolt://localhost:7687")
    NEO4J_USER: str = Field(default="neo4j")
    NEO4J_PASSWORD: str = Field(default="password")

    # JWT Authentication Config
    JWT_SECRET_KEY: str = Field(default="supersecretkeyforjwtverificationandgeneration2026")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @model_validator(mode="after")
    def _jwt_secret_fallback(self) -> "Settings":
        """Railway often sets JWT_SECRET instead of JWT_SECRET_KEY. Accept both."""
        env_fallback = os.environ.get("JWT_SECRET")
        if env_fallback and self.JWT_SECRET_KEY == "supersecretkeyforjwtverificationandgeneration2026":
            self.JWT_SECRET_KEY = env_fallback
        return self

    # LLM Provider Config
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    GOOGLE_API_KEY: Optional[str] = Field(default=None)

    # Storage Config
    STORAGE_TYPE: str = "local"  # local, s3, or cloudinary
    STORAGE_BUCKET_NAME: str = "truvia-evidence"
    LOCAL_STORAGE_DIR: str = "./storage/evidence"

    # Cloudinary Config
    CLOUDINARY_CLOUD_NAME: Optional[str] = Field(default=None)
    CLOUDINARY_API_KEY: Optional[str] = Field(default=None)
    CLOUDINARY_API_SECRET: Optional[str] = Field(default=None)
    CLOUDINARY_URL: Optional[str] = Field(default=None)

    # OCR/ASR Fallback Configuration
    OCR_LOW_CONFIDENCE_THRESHOLD: float = 0.60
    ASR_LOW_CONFIDENCE_THRESHOLD: float = 0.60

settings = Settings()

