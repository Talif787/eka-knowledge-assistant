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

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def json_logs(self) -> bool:
        return self.environment.lower() != "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
