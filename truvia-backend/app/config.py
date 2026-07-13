from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

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

    # LLM Provider Config
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    GOOGLE_API_KEY: Optional[str] = Field(default=None)

    # Storage Config
    STORAGE_TYPE: str = "local"  # local or s3
    STORAGE_BUCKET_NAME: str = "truvia-evidence"
    LOCAL_STORAGE_DIR: str = "./storage/evidence"

    # OCR/ASR Fallback Configuration
    OCR_LOW_CONFIDENCE_THRESHOLD: float = 0.60
    ASR_LOW_CONFIDENCE_THRESHOLD: float = 0.60

settings = Settings()
