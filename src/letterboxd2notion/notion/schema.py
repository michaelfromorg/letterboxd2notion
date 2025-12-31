"""Notion database schema definitions."""

# Schema for letterboxd2notion v2
# These are the properties that will be created/updated by init-schema
SCHEMA = {
    "Title": {"title": {}},
    "Rating": {"number": {"format": "number"}},
    "Film Year": {"number": {"format": "number"}},
    "Watched Date": {"date": {}},
    "Review": {"rich_text": {}},
    "Movie URL": {"url": {}},
    "Backdrop": {"files": {}},
    "Letterboxd ID": {"rich_text": {}},
    "TMDB ID": {"number": {"format": "number"}},
    "Rewatch": {"checkbox": {}},
}


def get_schema_update_payload() -> dict:
    """Get the payload for updating database schema via PATCH /databases/{id}."""
    return {"properties": SCHEMA}
