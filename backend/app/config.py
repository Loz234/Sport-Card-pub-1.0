from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="CardSignal AI", alias="APP_NAME")
    app_env: Literal["development", "test", "production"] = Field(default="development", alias="APP_ENV")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    debug: bool = Field(default=False, alias="DEBUG")
    database_url: str = Field(
        default="postgresql+psycopg://postgres@localhost:5432/cardsignal",
        alias="DATABASE_URL",
    )
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"], alias="CORS_ORIGINS")
    ml_model_version: str = Field(default="baseline-v1", alias="ML_MODEL_VERSION")
    llm_provider: str = Field(default="disabled", alias="LLM_PROVIDER")
    llm_model: str = Field(default="", alias="LLM_MODEL")
    llm_api_key: SecretStr | None = Field(default=None, alias="LLM_API_KEY")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if "://" not in value:
            return value
        scheme, remainder = value.split("://", 1)
        if scheme in {"postgres", "postgresql"}:
            return f"postgresql+psycopg://{remainder}"
        return value

    @model_validator(mode="after")
    def validate_production_database_backend(self) -> "Settings":
        if self.app_env == "production" and self.database_url.startswith("sqlite"):
            raise ValueError("SQLite is not supported in production. Configure DATABASE_URL for PostgreSQL.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
