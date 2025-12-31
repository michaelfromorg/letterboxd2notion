# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

letterboxd2notion syncs movie ratings from a Letterboxd user's film diary to a Notion database. It scrapes Letterboxd pages, enriches data with TheMovieDB API (backdrop images), and creates Notion entries while preventing duplicates.

## Commands

```bash
make run      # Run the sync (python -m letterboxd2notion.main)
make mypy     # Type checking
make check    # Lint with ruff
make format   # Format with ruff
```

## Architecture

The codebase is a single-package Python module with three files:

- `main.py` - Entry point. Paginates through Letterboxd diary pages, collects movies, then adds each to Notion
- `letterboxd.py` - Core logic: `scrape()` fetches HTML, `get_data()` parses it and calls TMDB API, `add_to_notion()` creates Notion entries
- `config.py` - Loads environment variables from `.env` and exports them. Contains hardcoded `LETTERBOXD_USERNAME`

Data flow: Letterboxd HTML → BeautifulSoup parsing → TMDB API enrichment → Notion API creation

## Environment Setup

Required `.env` variables (see `.env.example`):
- `TOKEN_V3` - Notion integration token
- `DATABASE_ID` - Notion database ID (first UUID from database URL)
- `TMDB_API_KEY` - TheMovieDB API key

Notion database must have fields: Title (text), Rating (text), Year (text), Movie URL (URL), Backdrop (files)

## Key Dependencies

- `beautifulsoup4` - HTML scraping
- `notion-client` - Official Notion SDK
- `requests` - HTTP requests
- `python-dotenv` - Environment loading
- `mypy` / `ruff` - Type checking and linting
