"""CLI commands using click."""

import asyncio
from typing import Any

import click

from letterboxd2notion import __version__
from letterboxd2notion.config import Settings, get_settings


@click.group()
@click.version_option(version=__version__)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Sync Letterboxd diary to Notion database."""
    ctx.ensure_object(dict)
    try:
        ctx.obj["settings"] = get_settings()
    except Exception as e:
        # Settings will fail if .env is missing - allow check commands to run
        ctx.obj["settings"] = None
        ctx.obj["settings_error"] = str(e)


@main.command()
@click.option("--full", is_flag=True, help="Full sync using HTML scraping")
@click.option("--dry-run", is_flag=True, help="Show what would be synced without syncing")
@click.option("--limit", type=int, help="Limit number of films to sync")
@click.pass_context
def sync(ctx: click.Context, full: bool, dry_run: bool, limit: int | None) -> None:
    """Sync films from Letterboxd to Notion.

    By default, uses RSS feed for incremental sync (~50 most recent).
    Use --full for complete history sync via HTML scraping.
    """
    settings: Settings | None = ctx.obj.get("settings")
    if settings is None:
        click.echo(f"Error loading settings: {ctx.obj.get('settings_error')}", err=True)
        ctx.exit(1)

    asyncio.run(_sync(settings, full=full, dry_run=dry_run, limit=limit))


async def _sync(
    settings: Settings,
    full: bool,
    dry_run: bool,
    limit: int | None,
) -> None:
    """Async sync implementation."""
    import httpx

    from letterboxd2notion.notion.client import NotionClient
    from letterboxd2notion.notion.sync import NotionSync
    from letterboxd2notion.parsers import enrich_film_with_tmdb
    from letterboxd2notion.parsers.html_parser import parse_all_diary_pages
    from letterboxd2notion.parsers.rss_parser import parse_rss_feed

    click.echo(f"Syncing for user: {settings.letterboxd_username}")

    async with httpx.AsyncClient() as http_client:
        # Parse films
        if full:
            click.echo("Performing full sync via HTML scraping...")
            films = await parse_all_diary_pages(
                http_client,
                settings.letterboxd_diary_url,
                on_page=lambda p: click.echo(f"  Fetching page {p}..."),
            )
        else:
            click.echo("Performing incremental sync via RSS feed...")
            films = await parse_rss_feed(http_client, settings.letterboxd_rss_url)

        click.echo(f"Found {len(films)} films")

        if limit:
            films = films[:limit]
            click.echo(f"Limited to {len(films)} films")

        # Enrich with TMDB data
        click.echo("Enriching with TMDB data...")
        enriched_films = []
        with click.progressbar(films, label="Fetching backdrops") as bar:
            for film in bar:
                try:
                    enriched = await enrich_film_with_tmdb(http_client, film, settings.tmdb_api_key)
                    enriched_films.append(enriched)
                except Exception as e:
                    click.echo(f"\n  Warning: TMDB error for {film.title}: {e}", err=True)
                    enriched_films.append(film)
                await asyncio.sleep(0.25)  # TMDB rate limit

        if dry_run:
            click.echo("\nDry run - would sync:")
            for film in enriched_films:
                status = "new"
                stars = f" - {film.rating_stars}" if film.rating else ""
                click.echo(f"  [{status}] {film.title} ({film.year}){stars}")
            return

        # Sync to Notion
        click.echo("\nSyncing to Notion...")
        async with NotionClient(settings.notion_token) as notion:
            sync_client = NotionSync(notion, settings.notion_database_id)
            await sync_client.initialize()
            click.echo(f"Found {sync_client.existing_count} existing entries in database")

            def on_progress(film: Any, action: str) -> None:
                symbol = "+" if action == "created" else "~"
                click.echo(f"  [{symbol}] {film.title}")

            counts = await sync_client.sync_films(enriched_films, on_progress=on_progress)

            click.echo(f"\nSync complete: {counts['created']} created, {counts['updated']} updated")


@main.command("init-schema")
@click.pass_context
def init_schema(ctx: click.Context) -> None:
    """Initialize Notion database with required properties."""
    settings: Settings | None = ctx.obj.get("settings")
    if settings is None:
        click.echo(f"Error loading settings: {ctx.obj.get('settings_error')}", err=True)
        ctx.exit(1)

    asyncio.run(_init_schema(settings))


async def _init_schema(settings: Settings) -> None:
    """Initialize database schema."""
    from letterboxd2notion.notion.client import NotionClient
    from letterboxd2notion.notion.schema import SCHEMA

    click.echo("Updating Notion database schema...")

    async with NotionClient(settings.notion_token) as notion:
        # Get current database info
        db = await notion.get_database(settings.notion_database_id)
        title_list = db.get("title", [])
        db_name = title_list[0].get("plain_text", "Unknown") if title_list else "Unknown"
        click.echo(f"Database: {db_name}")

        # Update schema
        await notion.update_database(settings.notion_database_id, SCHEMA)

        click.echo("\nSchema updated! Properties:")
        for name, config in SCHEMA.items():
            prop_type = list(config.keys())[0]
            click.echo(f"  + {name}: {prop_type}")

        click.echo("\nDone! Your database now has all required properties.")


@main.command("check-schema")
@click.pass_context
def check_schema(ctx: click.Context) -> None:
    """Check the current Notion database schema."""
    settings: Settings | None = ctx.obj.get("settings")
    if settings is None:
        click.echo(f"Error loading settings: {ctx.obj.get('settings_error')}", err=True)
        ctx.exit(1)

    asyncio.run(_check_schema(settings))


async def _check_schema(settings: Settings) -> None:
    """Check database schema."""
    from letterboxd2notion.notion.client import NotionClient

    async with NotionClient(settings.notion_token) as notion:
        db = await notion.get_database(settings.notion_database_id)

        title_list = db.get("title", [])
        db_name = title_list[0].get("plain_text", "Unknown") if title_list else "Unknown"

        click.echo(f"Database: {db_name}")
        click.echo("\nProperties:")
        for name, prop in db.get("properties", {}).items():
            click.echo(f"  {name}: {prop.get('type')}")

        click.echo("\nRequired properties for v2 schema:")
        required = [
            "Title (title)",
            "Rating (number)",
            "Film Year (number)",
            "Watched Date (date)",
            "Review (rich_text)",
            "Movie URL (url)",
            "Backdrop (files)",
            "Letterboxd ID (rich_text)",
            "TMDB ID (number)",
            "Rewatch (checkbox)",
        ]
        for prop in required:
            click.echo(f"  - {prop}")


@main.command("test-rss")
@click.option("--limit", type=int, default=5, help="Number of entries to show")
@click.pass_context
def test_rss(ctx: click.Context, limit: int) -> None:
    """Test RSS feed parsing (no Notion connection needed)."""
    settings: Settings | None = ctx.obj.get("settings")

    # Allow running without full settings - just need username
    username = settings.letterboxd_username if settings else "michaelfromyeg"

    asyncio.run(_test_rss(username, limit))


async def _test_rss(username: str, limit: int) -> None:
    """Test RSS parsing."""
    import httpx

    from letterboxd2notion.parsers.rss_parser import parse_rss_feed

    rss_url = f"https://letterboxd.com/{username}/rss/"
    click.echo(f"Fetching RSS from: {rss_url}")

    async with httpx.AsyncClient() as client:
        films = await parse_rss_feed(client, rss_url)

    click.echo(f"\nFound {len(films)} entries. Showing first {limit}:\n")

    for film in films[:limit]:
        click.echo(f"Title: {film.title} ({film.year})")
        click.echo(f"  Rating: {film.rating_stars or 'none'} ({film.rating})")
        click.echo(f"  Watched: {film.watched_date}")
        click.echo(f"  Rewatch: {film.rewatch}")
        click.echo(f"  TMDB ID: {film.tmdb_id}")
        click.echo(f"  URL: {film.letterboxd_url}")
        if film.review:
            review_preview = film.review[:100] + "..." if len(film.review) > 100 else film.review
            click.echo(f"  Review: {review_preview}")
        click.echo()


if __name__ == "__main__":
    main()
