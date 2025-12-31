"""Parsers for Letterboxd data and TMDB enrichment."""

import httpx

from letterboxd2notion.exceptions import TMDBError
from letterboxd2notion.models import Film

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"


async def enrich_film_with_tmdb(
    client: httpx.AsyncClient,
    film: Film,
    api_key: str,
) -> Film:
    """Enrich a Film with TMDB backdrop/poster URLs.

    If tmdb_id is available (from RSS), fetches directly by ID.
    Otherwise, searches by title and year.
    """
    if film.tmdb_id:
        movie_data = await _fetch_movie_by_id(client, film.tmdb_id, api_key)
    else:
        movie_data = await _search_movie(client, film.title, film.year, api_key)

    if movie_data is None:
        return film

    backdrop_path = movie_data.get("backdrop_path")
    poster_path = movie_data.get("poster_path")

    return film.model_copy(
        update={
            "backdrop_url": f"{TMDB_IMAGE_BASE}/w1280{backdrop_path}" if backdrop_path else None,
            "poster_url": f"{TMDB_IMAGE_BASE}/w500{poster_path}" if poster_path else None,
            "tmdb_id": movie_data.get("id") if film.tmdb_id is None else film.tmdb_id,
        }
    )


async def _fetch_movie_by_id(
    client: httpx.AsyncClient,
    tmdb_id: int,
    api_key: str,
) -> dict | None:
    """Fetch movie details by TMDB ID."""
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
    response = await client.get(url, params={"api_key": api_key})

    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise TMDBError(f"TMDB API error: {response.status_code}")

    return response.json()


async def _search_movie(
    client: httpx.AsyncClient,
    title: str,
    year: int | None,
    api_key: str,
) -> dict | None:
    """Search for movie by title, optionally filtering by year."""
    url = f"{TMDB_BASE_URL}/search/movie"
    params: dict[str, str] = {"api_key": api_key, "query": title}
    if year:
        params["year"] = str(year)

    response = await client.get(url, params=params)

    if response.status_code != 200:
        raise TMDBError(f"TMDB search error: {response.status_code}")

    data = response.json()
    results = data.get("results", [])

    return results[0] if results else None
