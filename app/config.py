from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central config. Every secret the app needs is declared here, typed,
    and required by default — a missing env var fails at startup, not
    on the first webhook delivery three days after deploy.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # GitHub webhook HMAC secret (set when you create the GitHub App).
    # Required in step 1. GitHub App ID / private key are added in step 2
    # when we start calling the GitHub API back, not before — no dead config.
    github_webhook_secret: str

    environment: str = "development"


@lru_cache
def get_settings() -> Settings:
    # Cached so we don't re-parse env vars on every request.
    # Pydantic resolves required settings from the environment at runtime.
    return Settings()  # pyright: ignore[reportCallIssue]