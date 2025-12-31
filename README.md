# letterboxd2notion

<p align="center">
  <img src="images/letterboxd_icon.png" alt="Letterboxd" width="32" height="32">
  <img src="images/notion_icon.png" alt="Notion" width="32" height="32">
</p>

Sync your Letterboxd film diary to a Notion database.

Inspired by [@kach0w](https://github.com/kach0w/letterbox-to-notion).

## Features

- **RSS sync**: Incremental updates from your Letterboxd RSS feed (~50 recent entries)
- **Full sync**: Complete history via HTML scraping
- **TMDB enrichment**: Fetches backdrop images from TheMovieDB
- **Deduplication**: Uses Letterboxd ID to prevent duplicates

## Setup

### 1. Create a Notion integration

1. Go to [notion.so/my-integrations](https://notion.so/my-integrations)
2. Create a new integration and copy the token

### 2. Create a Notion database

1. Create a new database in Notion
2. Share it with your integration (click "..." → "Connections" → select your integration)
3. Copy the database ID from the URL: `notion.so/<DATABASE_ID>?v=...`

### 3. Get a TMDB API key

1. Create an account at [themoviedb.org](https://www.themoviedb.org/)
2. Go to Settings → API and request an API key

### 4. Configure environment

```bash
cp .env.example .env
```

Fill in your `.env`:
```
TOKEN_V3=your_notion_integration_token
DATABASE_ID=your_database_id
TMDB_API_KEY=your_tmdb_api_key
LETTERBOXD_USERNAME=your_letterboxd_username
```

## Local Usage

Requires [uv](https://docs.astral.sh/uv/).

```bash
# Install dependencies
uv sync

# Initialize database schema
make init-schema

# Sync recent entries (RSS)
make sync

# Full sync (HTML scraping)
make sync-full

# Dry run (preview without syncing)
make sync-dry
```

## Automated Sync with GitHub Actions

To run the sync automatically every 6 hours:

### 1. Fork this repository

### 2. Add repository secrets

Go to your fork's **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret | Value |
|--------|-------|
| `TOKEN_V3` | Your Notion integration token |
| `DATABASE_ID` | Your Notion database ID |
| `TMDB_API_KEY` | Your TMDB API key |
| `LETTERBOXD_USERNAME` | Your Letterboxd username |

### 3. Enable the workflow

The workflow at `.github/workflows/sync.yml` runs automatically every 6 hours. You can also trigger it manually from the **Actions** tab.

## Notion Database Schema

The sync will create these properties:

| Property | Type | Description |
|----------|------|-------------|
| Title | title | Film title |
| Rating | number | 0.5-5.0 |
| Film Year | number | Release year |
| Watched Date | date | When watched |
| Review | rich_text | Your review |
| Movie URL | url | Letterboxd link |
| Backdrop | files | TMDB backdrop image |
| Letterboxd ID | rich_text | Unique ID for dedup |
| TMDB ID | number | TMDB movie ID |
| Rewatch | checkbox | Is rewatch? |

## License

MIT
