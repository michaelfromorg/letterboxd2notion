"""Data models for letterboxd2notion."""

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, computed_field


class Film(BaseModel):
    """Represents a film entry from Letterboxd."""

    # Core identifiers
    letterboxd_id: str = Field(description="From guid: letterboxd-review-XXX")
    tmdb_id: int | None = Field(default=None, description="TMDB movie ID from RSS")

    # Film metadata
    title: str
    year: int
    letterboxd_url: str

    # Watch metadata
    rating: float | None = Field(default=None, ge=0.5, le=5.0)
    watched_date: date | None = None
    rewatch: bool = False
    review: str | None = None

    # Enrichment data (from TMDB)
    backdrop_url: str | None = None
    poster_url: str | None = None

    @computed_field
    @property
    def rating_stars(self) -> str:
        """Convert numeric rating to star representation for display."""
        if self.rating is None:
            return ""
        full_stars = int(self.rating)
        half_star = self.rating % 1 >= 0.5
        return "\u2605" * full_stars + ("\u00bd" if half_star else "")

    def to_notion_properties(self) -> dict[str, Any]:
        """Convert to Notion API property format."""
        props: dict[str, Any] = {
            "Title": {"title": [{"text": {"content": self.title}}]},
            "Movie URL": {"url": self.letterboxd_url},
            "Letterboxd ID": {"rich_text": [{"text": {"content": self.letterboxd_id}}]},
            "Film Year": {"number": self.year},
            "Rewatch": {"checkbox": self.rewatch},
        }

        if self.rating is not None:
            props["Rating"] = {"number": self.rating}

        if self.watched_date:
            props["Watched Date"] = {"date": {"start": self.watched_date.isoformat()}}

        if self.review:
            # Notion rich_text has 2000 char limit per block
            review_text = self.review[:2000] if len(self.review) > 2000 else self.review
            props["Review"] = {"rich_text": [{"text": {"content": review_text}}]}

        if self.backdrop_url:
            props["Backdrop"] = {
                "files": [{"name": self.title[:100], "external": {"url": self.backdrop_url}}]
            }

        if self.tmdb_id:
            props["TMDB ID"] = {"number": self.tmdb_id}

        return props
