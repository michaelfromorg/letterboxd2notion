run:
	@python -m letterboxd2notion.main

mypy:
	@python -m mypy letterboxd2notion

check:
	@python -m ruff check letterboxd2notion

format:
	@python -m ruff format letterboxd2notion
