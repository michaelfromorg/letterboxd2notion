"""RSS feed parser for Letterboxd."""

from datetime import date
from xml.etree import ElementTree as ET

import httpx
from bs4 import BeautifulSoup

from letterboxd2notion.exceptions import ParseError, RateLimitError
from letterboxd2notion.models import Film

# RSS namespace mappings
NAMESPACES = {
    "letterboxd": "https://letterboxd.com",
    "tmdb": "https://themoviedb.org",
    "dc": "http://purl.org/dc/elements/1.1/",
}


async def parse_rss_feed(
    client: httpx.AsyncClient,
    rss_url: str,
) -> list[Film]:
    """Parse Letterboxd RSS feed into Film objects.

    Args:
        client: Async HTTP client
        rss_url: URL to Letterboxd RSS feed

    Returns:
        List of Film objects parsed from feed

    Raises:
        ParseError: If RSS cannot be parsed
        RateLimitError: If rate limited by Letterboxd
    """
    response = await client.get(rss_url)

    if response.status_code == 429:
        raise RateLimitError(retry_after=int(response.headers.get("Retry-After", 60)))
    response.raise_for_status()

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as e:
        raise ParseError(f"Failed to parse RSS XML: {e}") from e

    films: list[Film] = []

    for item in root.findall(".//item"):
        film = _parse_rss_item(item)
        if film:
            films.append(film)

    return films


def _parse_rss_item(item: ET.Element) -> Film | None:
    """Parse a single RSS item into a Film object."""

    # Extract guid (letterboxd-review-XXXXXXXXX)
    guid_elem = item.find("guid")
    if guid_elem is None or guid_elem.text is None:
        return None
    letterboxd_id = guid_elem.text

    # Extract film title
    title_elem = item.find("letterboxd:filmTitle", NAMESPACES)
    if title_elem is None or title_elem.text is None:
        return None
    title = title_elem.text

    # Extract film year
    year_elem = item.find("letterboxd:filmYear", NAMESPACES)
    if year_elem is None or year_elem.text is None:
        return None
    year = int(year_elem.text)

    # Extract link/URL
    link_elem = item.find("link")
    letterboxd_url = link_elem.text if link_elem is not None and link_elem.text else ""

    # Extract rating (optional)
    rating_elem = item.find("letterboxd:memberRating", NAMESPACES)
    rating = float(rating_elem.text) if rating_elem is not None and rating_elem.text else None

    # Extract watched date (optional)
    watched_elem = item.find("letterboxd:watchedDate", NAMESPACES)
    watched_date = None
    if watched_elem is not None and watched_elem.text:
        watched_date = date.fromisoformat(watched_elem.text)

    # Extract rewatch flag
    rewatch_elem = item.find("letterboxd:rewatch", NAMESPACES)
    rewatch = rewatch_elem is not None and rewatch_elem.text == "Yes"

    # Extract TMDB ID
    tmdb_elem = item.find("tmdb:movieId", NAMESPACES)
    tmdb_id = int(tmdb_elem.text) if tmdb_elem is not None and tmdb_elem.text else None

    # Extract review text from description
    review = _extract_review_from_description(item)

    return Film(
        letterboxd_id=letterboxd_id,
        tmdb_id=tmdb_id,
        title=title,
        year=year,
        letterboxd_url=letterboxd_url,
        rating=rating,
        watched_date=watched_date,
        rewatch=rewatch,
        review=review,
    )


def _extract_review_from_description(item: ET.Element) -> str | None:
    """Extract review text from RSS description field.

    The description contains HTML like:
    <p><img src="...poster.jpg"/></p>
    <p>First paragraph of review</p>
    <p>Second paragraph</p>
    """
    desc_elem = item.find("description")
    if desc_elem is None or desc_elem.text is None:
        return None

    soup = BeautifulSoup(desc_elem.text, "lxml")

    # Find all paragraphs
    paragraphs = soup.find_all("p")

    review_parts: list[str] = []
    for p in paragraphs:
        # Skip paragraphs that only contain an image
        if p.find("img") and not p.get_text(strip=True):
            continue
        # Skip spoiler warning
        text = p.get_text(strip=True)
        if text.startswith("This review may contain spoilers"):
            continue
        if text:
            review_parts.append(text)

    return "\n\n".join(review_parts) if review_parts else None
