"""Application settings (Twelve-Factor: config from the environment).

All settings are validated at startup; the process fails fast on misconfiguration
rather than surfacing errors deep in a request.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EKA_", env_file=".env", extra="ignore"
    )

    environment: str = Field(default="development")
    service_name: str = Field(default="eka-api")
    log_level: str = Field(default="INFO")

    database_dsn: str = Field(
        default="postgresql+asyncpg://eka:eka@localhost:5432/eka"
    )
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_echo: bool = Field(default=False)

    otlp_endpoint: str | None = Field(default=None)

    api_root_path: str = Field(default="")

    embedding_dimension: int = Field(default=384, ge=8, le=4096)
    chunk_size: int = Field(default=800, ge=64)
    chunk_overlap: int = Field(default=120, ge=0)
    ingestion_max_attempts: int = Field(default=5, ge=1, le=20)
    worker_id: str = Field(default="worker-1")
    worker_batch_size: int = Field(default=5, ge=1, le=100)
    worker_poll_interval_seconds: float = Field(default=1.0, gt=0)

    redis_url: str = Field(default="redis://localhost:6379/0")
    search_cache_ttl_seconds: int = Field(default=300, ge=0)
    search_pool_size: int = Field(default=50, ge=1, le=500)
    search_default_top_k: int = Field(default=5, ge=1, le=50)
    jwt_secret: str = Field(default="dev-only-insecure-secret-change-me-in-production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_issuer: str = Field(default="eka")
    jwt_access_ttl_seconds: int = Field(default=3600, ge=60)
    auth_dev_token_enabled: bool = Field(default=True)

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def json_logs(self) -> bool:
        return self.environment.lower() != "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
