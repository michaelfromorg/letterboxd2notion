import io
import sys
import time

from letterboxd2notion.config import LETTERBOXD_USERNAME
from letterboxd2notion.letterboxd import Movie, add_to_notion, get_data, scrape

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


if __name__ == "__main__":
    movies: list[Movie] = []
    url = f"https://letterboxd.com/{LETTERBOXD_USERNAME}/films/diary"

    page_num = 1
    while True:
        new_url = f"{url}/page/{page_num}"
        soup = scrape(new_url)
        data = get_data(soup)

        if not data:
            break

        movies.extend(data)
        page_num += 1
        time.sleep(2)  # Avoid rate limiting

    movies.reverse()
    for movie in movies:
        add_to_notion(movie)

    print("all done yay!")
