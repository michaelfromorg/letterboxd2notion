"""Async Notion API client with rate limiting."""

import asyncio
import time
from typing import Any

import httpx

from letterboxd2notion.exceptions import NotionError, RateLimitError

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionClient:
    """Async Notion API client with rate limiting."""

    def __init__(
        self,
        token: str,
        rate_limit_delay: float = 0.35,  # ~3 requests/second
    ):
        self.token = token
        self.rate_limit_delay = rate_limit_delay
        self._last_request_time: float = 0
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "NotionClient":
        self._client = httpx.AsyncClient(
            base_url=NOTION_API_BASE,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make a rate-limited request to Notion API."""
        if self._client is None:
            raise NotionError("Client not initialized. Use async context manager.")

        # Rate limiting
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)

        response = await self._client.request(method, path, **kwargs)
        self._last_request_time = time.monotonic()

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise RateLimitError(retry_after=retry_after)

        if response.status_code >= 400:
            raise NotionError(f"Notion API error {response.status_code}: {response.text}")

        return response.json()

    async def query_database(
        self,
        database_id: str,
        filter_: dict[str, Any] | None = None,
        sorts: list[dict[str, Any]] | None = None,
        start_cursor: str | None = None,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """Query a Notion database."""
        body: dict[str, Any] = {"page_size": page_size}
        if filter_:
            body["filter"] = filter_
        if sorts:
            body["sorts"] = sorts
        if start_cursor:
            body["start_cursor"] = start_cursor

        return await self._request(
            "POST",
            f"/databases/{database_id}/query",
            json=body,
        )

    async def create_page(
        self,
        database_id: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a page in a database."""
        return await self._request(
            "POST",
            "/pages",
            json={
                "parent": {"database_id": database_id},
                "properties": properties,
            },
        )

    async def update_page(
        self,
        page_id: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an existing page."""
        return await self._request(
            "PATCH",
            f"/pages/{page_id}",
            json={"properties": properties},
        )

    async def get_database(self, database_id: str) -> dict[str, Any]:
        """Get database metadata including schema."""
        return await self._request("GET", f"/databases/{database_id}")

    async def update_database(
        self,
        database_id: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Update database properties (schema)."""
        return await self._request(
            "PATCH",
            f"/databases/{database_id}",
            json={"properties": properties},
        )
