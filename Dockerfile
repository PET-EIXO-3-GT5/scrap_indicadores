FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app/scrap_indicadores

RUN apt-get update \
	&& apt-get install -y --no-install-recommends git \
	&& rm -rf /var/lib/apt/lists/*

# Copia apenas os arquivos de dependencias primeiro para aproveitar cache.
COPY scrap_indicadores/pyproject.toml scrap_indicadores/uv.lock ./
RUN uv sync --frozen --no-dev

# Copia o codigo da aplicacao.
COPY scrap_indicadores/ ./

CMD ["uv", "run", "main.py"]
