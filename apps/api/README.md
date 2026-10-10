# p3d-api

Read-only API for Periodic Table 3D (FastAPI, SQLAlchemy 2 async, asyncpg, PostgreSQL).
It serves the dataset that the pipeline builds. The same code writes the static
JSON export that the GitHub Pages demo uses (ADR 0003).

## Endpoints (`/api/v1`)

| Path | Answer |
| --- | --- |
| `/meta` | dataset version, counts, licenses |
| `/elements` | 118 elements for the table |
| `/elements/{symbol}` | element card: properties, simple substance (3D), partners (rays), top compounds |
| `/compounds/{id}` | compound card: formula, composition, names, descriptions, 3D structure, sources |
| `/pairs/{A}-{B}` | compounds of two elements, most famous first (beads on a ray) |
| `/compounds?elements=Fe,O&mode=contains\|only` | compounds of a selection (the cloud) |
| `/index` | compact list of all compounds (browser-side search in static mode) |
| `/search?q=гематит` | compounds by formula or name in UA/RU/EN (pg_trgm index) |

Interactive docs: `/api/docs`. Health check: `/health`.

## Commands

```bash
uv sync
export DATABASE_URL=postgresql://p3d:p3d@localhost:5432/p3d
uv run p3d-api migrate                     # create or upgrade the schema
uv run p3d-api load path/to/dataset.tar.gz # replace the data (one transaction)
uv run p3d-api serve --port 8000           # run the API
uv run p3d-api export-static out/data      # write every answer as JSON files
```

Tests need PostgreSQL: `TEST_DATABASE_URL=postgresql://… uv run pytest`.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://p3d:p3d@localhost:5432/p3d` | database; `postgres://` and `sslmode` are accepted |
| `P3D_CORS_ORIGINS` | `*` | allowed origins, comma-separated |
| `P3D_CACHE_MAX_AGE` | `300` | browser cache, seconds |
| `P3D_CACHE_S_MAXAGE` | `86400` | CDN cache, seconds |
| `P3D_BUILD_ID` | `dev` | part of the ETag; set it to the git commit |
