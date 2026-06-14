.PHONY: all test browser

all:
	PYTHONPATH=src uv run python -m scrap_indicadores.main

test:
	PYTHONPATH=src uv run pytest

browser:
	PYTHONPATH=src uv run python -m scrap_indicadores.scraper_navegador