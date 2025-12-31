"""Custom exceptions for letterboxd2notion."""


class LetterboxdError(Exception):
    """Base exception for letterboxd2notion."""


class ParseError(LetterboxdError):
    """Error parsing Letterboxd data."""


class RateLimitError(LetterboxdError):
    """Rate limit exceeded."""

    def __init__(self, retry_after: int | None = None):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after: {retry_after}s")


class NotionError(LetterboxdError):
    """Error interacting with Notion API."""


class TMDBError(LetterboxdError):
    """Error fetching TMDB data."""
