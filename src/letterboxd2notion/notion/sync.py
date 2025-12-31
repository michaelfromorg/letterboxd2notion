"""Sync logic with upsert and deduplication."""

from collections.abc import Callable

from letterboxd2notion.models import Film
from letterboxd2notion.notion.client import NotionClient


class NotionSync:
    """Handles syncing films to Notion with deduplication and upsert."""

    def __init__(
        self,
        client: NotionClient,
        database_id: str,
    ):
        self.client = client
        self.database_id = database_id
        self._id_to_page: dict[str, str] = {}  # letterboxd_id -> page_id
        self._title_to_page: dict[str, str] = {}  # title -> page_id (fallback)

    async def initialize(self) -> None:
        """Initialize sync state by loading existing pages."""
        await self._load_existing_pages()

    async def _load_existing_pages(self) -> None:
        """Load all existing pages and build lookup indexes."""
        start_cursor: str | None = None

        while True:
            result = await self.client.query_database(
                self.database_id,
                start_cursor=start_cursor,
            )

            for page in result.get("results", []):
                props = page.get("properties", {})
                page_id = page["id"]

                # Try Letterboxd ID first
                lb_id_prop = props.get("Letterboxd ID", {})
                rich_text = lb_id_prop.get("rich_text", [])
                if rich_text:
                    lb_id = rich_text[0].get("plain_text", "")
                    if lb_id:
                        self._id_to_page[lb_id] = page_id

                # Also index by title for legacy entries
                title_prop = props.get("Title", {})
                title_list = title_prop.get("title", [])
                if title_list:
                    title = title_list[0].get("plain_text", "")
                    if title:
                        self._title_to_page[title] = page_id

            if not result.get("has_more"):
                break
            start_cursor = result.get("next_cursor")

    def _find_existing_page(self, film: Film) -> str | None:
        """Find existing page ID for a film."""
        # Check by Letterboxd ID first
        if film.letterboxd_id in self._id_to_page:
            return self._id_to_page[film.letterboxd_id]

        # Fallback to title match
        if film.title in self._title_to_page:
            return self._title_to_page[film.title]

        return None

    async def sync_film(self, film: Film) -> tuple[str, str]:
        """Sync a single film to Notion.

        Returns:
            Tuple of (page_id, action) where action is "created", "updated", or "skipped"
        """
        properties = film.to_notion_properties()
        existing_page_id = self._find_existing_page(film)

        if existing_page_id:
            # Update existing page
            await self.client.update_page(existing_page_id, properties)
            # Update index
            self._id_to_page[film.letterboxd_id] = existing_page_id
            return existing_page_id, "updated"
        else:
            # Create new page
            result = await self.client.create_page(self.database_id, properties)
            new_id = result["id"]
            # Update indexes
            self._id_to_page[film.letterboxd_id] = new_id
            self._title_to_page[film.title] = new_id
            return new_id, "created"

    async def sync_films(
        self,
        films: list[Film],
        on_progress: Callable[[Film, str], None] | None = None,
    ) -> dict[str, int]:
        """Sync multiple films.

        Args:
            films: List of films to sync
            on_progress: Optional callback called with (film, action)

        Returns:
            Dict with counts: {"created": N, "updated": N}
        """
        counts = {"created": 0, "updated": 0}

        for film in films:
            _, action = await self.sync_film(film)
            counts[action] += 1

            if on_progress:
                on_progress(film, action)

        return counts

    @property
    def existing_count(self) -> int:
        """Number of existing pages loaded."""
        return len(self._id_to_page)
