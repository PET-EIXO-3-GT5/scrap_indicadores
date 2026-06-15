.PHONY: all test browser browser-setup

all:
	uv run --directory . python -m scrap_indicadores.main

test:
	uv run --directory . python -m coverage erase
	uv run --directory . pytest

browser: browser-setup
	uv run --directory . python -m scrap_indicadores.scraper_navegador

browser-setup:
	uv run --directory . playwright install chromium