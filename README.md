# Periodic Table 3D

An interactive 3D periodic table. Click an element and fly inside it: glowing rays lead
to the elements it bonds with, and each ray carries the compounds of that pair. Open a
compound to see its molecule or crystal slowly rotating in 3D, with atoms labelled and
its formula, composition and properties beside it. Select several elements to get a
cloud of compounds that contain all of them.

> Status: under active development (stage 0 — foundations). See
> [docs/agent/PROGRESS.md](docs/agent/PROGRESS.md).

## Highlights

- One WebGL canvas for the whole app; every transition is a smooth camera flight.
- Fast by design: precomputed dataset, instanced rendering, strict performance budgets.
- Real chemistry: molecules from PubChem 3D, crystals from Materials Project and COD,
  names in Ukrainian, Russian and English from Wikidata.
- Two data modes: a static snapshot (free hosting on GitHub Pages) and a live
  FastAPI + PostgreSQL/pgvector backend.

## Architecture

```text
sources ──► pipeline (Python, offline) ──► dataset ──┬─► PostgreSQL + pgvector ──► FastAPI ──┐
PubChem, Materials Project,                           │                                       ├─► CDN ──► web (React + R3F)
COD, Wikidata, Wikipedia                              └─► static export (JSON) ───────────────┘
```

| Part | Stack |
| --- | --- |
| `apps/web` | React 19, TypeScript, Vite, three.js, React Three Fiber, drei, zustand, TanStack Query |
| `apps/api` | Python 3.12, FastAPI, SQLAlchemy 2 (async), asyncpg, Alembic, PostgreSQL 17 + pgvector |
| `pipeline` | Python 3.12, RDKit, pymatgen, polars, Typer |
| CI/CD | GitHub Actions, GitHub Pages (demo) |

Design decisions are recorded in [docs/adr](docs/adr). The full plan is in
[docs/plan.md](docs/plan.md).

## Data sources and licenses

The source code is MIT-licensed. Chemical data keeps the licenses of its sources:
PubChem (NIH, public data), Materials Project (CC BY 4.0), Crystallography Open
Database (public domain), Wikidata (CC0), Wikipedia (CC BY-SA). Details:
[docs/data-sources.md](docs/data-sources.md).

## License

[MIT](LICENSE) © 2026 Ihor Korenets
