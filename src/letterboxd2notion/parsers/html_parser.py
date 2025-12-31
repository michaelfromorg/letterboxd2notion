"""HTML scraper for Letterboxd diary (fallback for full history)."""

import asyncio
import re
from collections.abc import Callable
from datetime import date

import httpx
from bs4 import BeautifulSoup, Tag

from letterboxd2notion.exceptions import RateLimitError
from letterboxd2notion.models import Film


async def parse_diary_page(
    client: httpx.AsyncClient,
    diary_url: str,
    page: int = 1,
) -> tuple[list[Film], bool]:
    """Parse a single page of the Letterboxd diary.

    Args:
        client: Async HTTP client
        diary_url: Base diary URL
        page: Page number to fetch

    Returns:
        Tuple of (films, has_more_pages)
    """
    url = f"{diary_url}/page/{page}/"
    response = await client.get(url, follow_redirects=True)

    if response.status_code == 429:
        raise RateLimitError()
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    films: list[Film] = []

    for row in soup.select("tr.diary-entry-row"):
        film = _parse_diary_row(row)
        if film:
            films.append(film)

    # Check if there are more pages (empty page means no more)
    has_more = len(films) > 0

    return films, has_more


def _parse_diary_row(row: Tag) -> Film | None:
    """Parse a single diary table row."""

    # Get viewing ID for unique identifier
    viewing_id = row.get("data-viewing-id")
    if not viewing_id:
        return None

    # Find the react-component div with film data
    poster_div = row.select_one("div.react-component[data-item-slug]")
    if not poster_div:
        return None

    # Extract data from data attributes
    title = poster_div.get("data-item-name", "")
    slug = poster_div.get("data-item-slug", "")

    if not title or not slug:
        return None

    # Extract year from title like "Home Alone (1990)"
    year_match = re.search(r"\((\d{4})\)$", str(title))
    year = int(year_match.group(1)) if year_match else 0

    # Clean title (remove year)
    clean_title = re.sub(r"\s*\(\d{4}\)$", "", str(title))

    letterboxd_url = f"https://letterboxd.com/film/{slug}/"

    # Get rating from span.rating
    rating = _extract_rating(row)

    # Get watch date from the day link
    watched_date = _extract_watched_date(row)

    # Check for rewatch (icon-rewatch without icon-status-off)
    rewatch_td = row.select_one("td.col-rewatch")
    rewatch_classes = rewatch_td.get("class") if rewatch_td else None
    rewatch = (
        rewatch_classes is not None
        and isinstance(rewatch_classes, list)
        and "icon-status-off" not in rewatch_classes
    )

    # Generate letterboxd ID from viewing ID
    letterboxd_id = f"letterboxd-viewing-{viewing_id}"

    return Film(
        letterboxd_id=letterboxd_id,
        tmdb_id=None,  # Not available in HTML, needs TMDB search
        title=clean_title,
        year=year,
        letterboxd_url=letterboxd_url,
        rating=rating,
        watched_date=watched_date,
        rewatch=rewatch,
        review=None,  # Would need separate fetch to get review
    )


def _extract_rating(row: Tag) -> float | None:
    """Extract rating from the row."""
    # Find the rating span with class like "rated-5" or "rated-10"
    rating_span = row.select_one("span.rating[class*='rated-']")
    if rating_span:
        classes = rating_span.get("class")
        if not isinstance(classes, list):
            return None
        for cls in classes:
            if isinstance(cls, str) and cls.startswith("rated-"):
                try:
                    # rated-5 means 2.5 stars (5 half-stars), rated-10 means 5 stars
                    half_stars = int(cls.replace("rated-", ""))
                    return half_stars / 2.0
                except ValueError:
                    pass

    return None


def _extract_watched_date(row: Tag) -> date | None:
    """Extract the watch date from the diary row."""
    # Get from the daydate link href like /michaelfromyeg/diary/films/for/2025/12/26/
    day_link = row.select_one("a.daydate")
    if not day_link:
        return None

    href = day_link.get("href", "")
    if not isinstance(href, str):
        return None

    # Extract date from href
    match = re.search(r"/for/(\d{4})/(\d{1,2})/(\d{1,2})", href)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass

    return None


async def parse_all_diary_pages(
    client: httpx.AsyncClient,
    diary_url: str,
    on_page: Callable[[int], None] | None = None,
) -> list[Film]:
    """Parse all diary pages for full sync.

    Args:
        client: Async HTTP client
        diary_url: Base diary URL
        on_page: Optional callback called with page number

    Returns:
        List of all films from all pages
    """
    all_films: list[Film] = []
    page = 1

    while True:
        if on_page:
            on_page(page)

        films, has_more = await parse_diary_page(client, diary_url, page)

        if not films:
            break

        all_films.extend(films)
        page += 1

        if not has_more:
            break

        # Respect rate limits
        await asyncio.sleep(2)

    return all_films
