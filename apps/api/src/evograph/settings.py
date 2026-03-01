from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/evograph"
    redis_url: str = "redis://redis:6379/0"
    scope_ott_root: str = "Aves"
    cors_origins: list[str] = ["*"]
    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info"
    log_format: Literal["text", "json"] = "text"

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
