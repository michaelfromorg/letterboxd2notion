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
    import time

    for attempt in range(5):
        response = requests.get(url)
        if response.status_code == 429:
            wait_time = 30 * (attempt + 1)
            print(f"Rate limited, waiting {wait_time}s...")
            time.sleep(wait_time)
            continue
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
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

        # Get title and slug from col-production
        col_production = e.find("td", class_="col-production")
        if not isinstance(col_production, Tag):
            continue
        title_link = col_production.find("a")
        if not isinstance(title_link, Tag):
            continue
        title = title_link.get_text(strip=True)
        href = title_link.get("href")
        if not isinstance(href, str):
            continue
        # Extract slug from href like /michaelfromyeg/film/SLUG/
        slug = href.split("/film/")[-1].rstrip("/")
        movie_url = "https://letterboxd.com/film/" + slug

        # Get watch date from col-monthdate
        col_monthdate = e.find("td", class_="col-monthdate")
        if not isinstance(col_monthdate, Tag):
            continue
        month_link = col_monthdate.find("a", class_="month")
        year_link = col_monthdate.find("a", class_="year")
        if not isinstance(month_link, Tag) or not isinstance(year_link, Tag):
            continue
        month_str = month_link.get_text(strip=True)
        year_str = year_link.get_text(strip=True)
        year = MONTH_MAPPING.get(month_str, month_str) + " " + year_str

        link = f"https://api.themoviedb.org/3/search/movie?query={quote(title)}&api_key={TMDB_API_KEY}"

        response = requests.get(link)
        backdrop = ""

        if response.status_code == 200:
            response_json = response.json()
            if len(response_json["results"]) == 0:
                print(f"No TMDB results for {title}")
            else:
                backdrop_path = response_json["results"][0].get("backdrop_path")
                if backdrop_path:
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
