# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

letterboxd2notion syncs movie ratings from a Letterboxd user's film diary to a Notion database. It parses RSS feeds (primary) or scrapes HTML pages (fallback for full history), enriches data with TheMovieDB API (backdrop images), and syncs to Notion with upsert logic.

## Commands

```bash
make install      # Install dependencies with uv
make dev          # Install with dev dependencies
make init-schema  # Create/update Notion database properties
make sync         # Incremental sync via RSS (~50 recent)
make sync-full    # Full sync via HTML scraping
make sync-dry     # Dry run (show what would sync)
make check-schema # Show Notion database properties
make test-rss     # Test RSS parsing without Notion
make lint         # Lint with ruff
make format       # Format with ruff
make typecheck    # Type check with ty
```

## Architecture

```
src/letterboxd2notion/
├── cli.py           # Click CLI commands
├── config.py        # Pydantic settings from .env
├── models.py        # Film pydantic model with to_notion_properties()
├── exceptions.py    # Custom exceptions
├── parsers/
│   ├── __init__.py  # TMDB enrichment (enrich_film_with_tmdb)
│   ├── rss_parser.py    # Primary: parse RSS feed
│   └── html_parser.py   # Fallback: scrape diary pages
└── notion/
    ├── client.py    # Async httpx Notion client
    └── sync.py      # NotionSync with upsert/deduplication
```

### Data Flow

1. **Parse**: RSS feed (has TMDB ID, review text) or HTML scraping
2. **Enrich**: Fetch backdrop URLs from TMDB API (by ID or search)
3. **Sync**: Upsert to Notion (create new or update existing by Letterboxd ID)

### Key Patterns

- **Async everywhere**: httpx async client, `async with` context managers
- **Pydantic models**: `Film` model with `to_notion_properties()` method
- **Upsert logic**: Matches by `letterboxd_id` first, falls back to title

## Environment Setup

Required `.env` variables:
- `TOKEN_V3` - Notion integration token
- `DATABASE_ID` - Notion database ID
- `TMDB_API_KEY` - TheMovieDB API key
- `LETTERBOXD_USERNAME` (optional) - defaults to michaelfromyeg

## Notion Database Schema (v2)

| Property | Type | Description |
|----------|------|-------------|
| Title | title | Film title |
| Rating | number | 0.5-5.0 |
| Film Year | number | Release year |
| Watched Date | date | When watched |
| Review | rich_text | User's review |
| Movie URL | url | Letterboxd link |
| Backdrop | files | TMDB backdrop image |
| Letterboxd ID | rich_text | Unique ID for dedup |
| TMDB ID | number | TMDB movie ID |
| Rewatch | checkbox | Is rewatch? |

## Key Dependencies

- `httpx` - Async HTTP client
- `pydantic` / `pydantic-settings` - Data models and config
- `click` - CLI framework
- `beautifulsoup4` / `lxml` - HTML/XML parsing
- `ruff` - Linting and formatting
- `ty` - Type checking
