# scrap_indicadores

Projeto Python com `uv` usando `PySUS` (fonte GitHub) e pipeline de CI/CD para GitHub Actions.

## Requisitos

- Python 3.12+
- `uv` instalado
- Docker (opcional para container)

## Rodar localmente

```bash
cd scrap_indicadores
uv sync
uv run main.py
```

## Rodar com Docker

Na raiz do repositório:

```bash
docker build -t scrap_indicadores:local .
docker run --rm scrap_indicadores:local
```

Ou com compose:

```bash
docker compose up --build
```

## GitHub Actions configurado

- `.github/workflows/ci.yml`
	- valida em `push` e `pull_request` na `main`
	- instala dependências com `uv`
	- executa smoke test do app

- `.github/workflows/release.yml`
	- executa `release-please` em `push` na `main`

- `.github/workflows/docker-build.yml`
	- builda e publica imagem em `ghcr.io/pet-eixo-3-gt5/scrap_indicadores`
	- dispara em release publicada e manual (`workflow_dispatch`)

## Permissões e segredos

Para publicar imagem no GHCR, garanta:

1. O repositório está na organização `pet-eixo-3-gt5`.
2. `Actions` com permissão de `Read and write` para packages.
3. O pacote no GHCR permite publicação pelo repositório.

Os workflows atuais usam `secrets.GITHUB_TOKEN` (não precisa PAT extra no cenário padrão).
