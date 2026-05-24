from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = Field(default=...)
    PROJECT_DESCRIPTION: str = Field(default=...)
    PROJECT_VERSION: str = Field(default=...)

    # DB
    DB: str = Field(default=...)

    # JWT
    JWT_PRIVATE_KEY_PATH: str = Field(default=...)
    JWT_PUBLIC_KEY_PATH: str = Field(default=...)
    JWT_ALGORITHM: str = Field(default=...)

    ACCESS_TOKEN_EXPIRES_MINUTES: int = Field(default=...)
    REFRESH_TOKEN_EXPIRES_MINUTES: int = Field(default=...)

    ACCESS_COOKIE_NAME: str = Field(default=...)
    REFRESH_COOKIE_NAME: str = Field(default=...)

    SESSION_COOKIE_SECURE: bool = Field(default=...)
    SESSION_COOKIE_DOMAIN: str | None = Field(default=None)
    JWT_ISSUER: str = Field(default=...)
    JWT_AUDIENCE: str = Field(default=...)

    PRIVATE_KEY: str = Field(default="")
    PUBLIC_KEY: str = Field(default="")

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
    )

    def load_keys(self) -> None:
        self.PRIVATE_KEY = Path(self.JWT_PRIVATE_KEY_PATH).read_text()
        self.PUBLIC_KEY = Path(self.JWT_PUBLIC_KEY_PATH).read_text()


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.load_keys()
    return settings
