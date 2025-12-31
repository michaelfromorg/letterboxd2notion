.PHONY: install dev lint format typecheck test run sync sync-full init-schema check-schema test-rss

# Installation
install:
	uv sync

dev:
	uv sync --all-extras

# Code quality
lint:
	uv run ruff check src

format:
	uv run ruff format src

typecheck:
	uvx ty check src

# Testing
test:
	uv run pytest tests -v

# Running
run: sync

sync:
	uv run letterboxd2notion sync

sync-full:
	uv run letterboxd2notion sync --full

sync-dry:
	uv run letterboxd2notion sync --dry-run

init-schema:
	uv run letterboxd2notion init-schema

check-schema:
	uv run letterboxd2notion check-schema

test-rss:
	uv run letterboxd2notion test-rss

# All checks
check: lint
