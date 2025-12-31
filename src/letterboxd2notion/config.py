"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Notion configuration
    notion_token: str = Field(alias="TOKEN_V3")
    notion_database_id: str = Field(alias="DATABASE_ID")

    # TMDB configuration
    tmdb_api_key: str = Field(alias="TMDB_API_KEY")

    # Letterboxd configuration
    letterboxd_username: str = Field(default="michaelfromyeg", alias="LETTERBOXD_USERNAME")

    # Sync configuration
    rate_limit_delay: float = Field(default=0.35, description="Seconds between API calls")

    @property
    def letterboxd_rss_url(self) -> str:
        """URL to user's Letterboxd RSS feed."""
        return f"https://letterboxd.com/{self.letterboxd_username}/rss/"

    @property
    def letterboxd_diary_url(self) -> str:
        """URL to user's Letterboxd diary page."""
        return f"https://letterboxd.com/{self.letterboxd_username}/films/diary"

    @property
    def letterboxd_diary_url_alt(self) -> str:
        """Alternative diary URL (Letterboxd sometimes redirects)."""
        return f"https://letterboxd.com/{self.letterboxd_username}/diary"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()  # type: ignore[call-arg]  # pydantic-settings loads from env
