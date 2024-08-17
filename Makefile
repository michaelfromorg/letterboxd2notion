run:
	@python -m letterboxd2notion.main

mypy:
	@python -m mypy letterboxd2notion

check:
	@ruff check letterboxd2notion

format:
	@ruff format letterboxd2notion
