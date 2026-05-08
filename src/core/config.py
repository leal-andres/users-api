from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: Literal["dev", "staging", "production", "test"] = "dev"
    log_level: str = "INFO"

    database_url: str
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False

    api_title: str = "Users API"
    api_version: str = "0.1.0"
    api_description: str = "User management REST API"

    cors_origins: list[str] = ["*"]

    secret_key: SecretStr = SecretStr("change-me-in-production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
