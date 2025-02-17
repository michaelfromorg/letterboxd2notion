from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup, Tag
from notion_client import Client

from letterboxd2notion.config import (
    DATABASE_ID,
    TMDB_API_KEY,
    TOKEN_V3,
)

MONTH_MAPPING = {
    "Jan": "January",
    "Feb": "February",
    "Mar": "March",
    "Apr": "April",
    "May": "May",
    "Jun": "June",
    "Jul": "July",
    "Aug": "August",
    "Sep": "September",
    "Oct": "October",
    "Nov": "November",
    "Dec": "December",
}

notion = Client(auth=TOKEN_V3)


def scrape(url: str) -> BeautifulSoup:
    """
    Turn a URL into a BeautifulSoup object.
    """
    response = requests.get(url)
    response.raise_for_status()
    return BeautifulSoup(response.content, "html.parser")


@dataclass
class Movie:
    title: str
    rating: str
    year: str
    movie_url: str
    backdrop: str


def get_data(soup: BeautifulSoup) -> list[Movie]:
    movies: list[Movie] = []

    for e in soup.select("tr.diary-entry-row"):
        if e is None:
            continue

        hide_for_owner = e.find("div", class_="hide-for-owner")
        if hide_for_owner is None:
            continue
        rating = hide_for_owner.get_text().strip()

        td_actions = e.find("td", class_="td-actions")
        if not isinstance(td_actions, Tag):
            continue

        title = td_actions.get("data-film-name")
        if not isinstance(title, str):
            continue

        if e.find("div", class_="date"):
            td_calendar = e.find("td", class_="td-calendar")
            if td_calendar is None:
                continue
            small = td_calendar.find("small")
            if not isinstance(small, Tag):
                continue
            year_str = small.get_text(strip=True)

            date = e.find("div", class_="date")
            if date is None:
                continue
            month_str = date.get_text()
            month_str = month_str.strip().split(" ")[0]

            year = MONTH_MAPPING[month_str] + " " + year_str

        slug = td_actions.get("data-film-slug")
        if not isinstance(slug, str):
            continue
        movie_url = "https://letterboxd.com/film/" + slug

        link = f"https://api.themoviedb.org/3/search/movie?query={quote(title)}&api_key={TMDB_API_KEY}"

        response = requests.get(link)
        backdrop = ""

        if response.status_code == 200:
            response_json = response.json()
            if len(response_json["results"]) == 0:
                print(f"No images found for {title}")
                continue

            backdrop_path = response_json["results"][0]["backdrop_path"]
            backdrop = "https://image.tmdb.org/t/p/w500" + backdrop_path

        movie = Movie(
            title=title,
            rating=rating,
            year=year,
            movie_url=movie_url,
            backdrop=backdrop,
        )
        movies.append(movie)

    return movies


def add_to_notion(movie: Movie) -> None:
    """
    Add a movie to Notion.
    """
    properties = {
        "Title": {"title": [{"text": {"content": movie.title}}]},
        "Rating": {"rich_text": [{"text": {"content": movie.rating}}]},
        "Year": {"rich_text": [{"text": {"content": movie.year}}]},
        "Movie URL": {"url": movie.movie_url},
    }
    if movie.backdrop:
        properties["Backdrop"] = {
            "files": [{"name": movie.title, "external": {"url": movie.backdrop}}]
        }
    response: Any = notion.databases.query(
        database_id=DATABASE_ID,
        filter={"property": "Title", "rich_text": {"equals": movie.title}},
    )
    if len(response["results"]) > 0:
        print("Found it!")
    else:
        print(f"Adding {movie.title}!")
        notion.pages.create(parent={"database_id": DATABASE_ID}, properties=properties)
