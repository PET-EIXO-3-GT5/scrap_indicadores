FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app/scrap_indicadores
ENV PYTHONPATH=/app/scrap_indicadores/src

RUN apt-get update \
	&& apt-get install -y --no-install-recommends git \
	&& rm -rf /var/lib/apt/lists/*

# Copia apenas os arquivos de dependencias primeiro para aproveitar cache.
COPY scrap_indicadores/pyproject.toml scrap_indicadores/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project && uv run playwright install --with-deps chromium

# Copia o codigo da aplicacao.
COPY scrap_indicadores/ ./
RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "scrap_indicadores.main"]

