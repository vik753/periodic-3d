# Periodic Table 3D

An interactive 3D periodic table. Click an element and fly inside it: glowing rays lead
to the elements it forms compounds with, and each ray carries the compounds of that
pair. Open a compound to see its molecule or crystal slowly rotating in 3D, with atoms
labelled and its formula, composition, properties and sources beside it. Select several
elements to get a cloud of compounds that contain all of them.

**Live demo:** https://vik753.github.io/periodic-3d/ (interface in Ukrainian, Russian
and English).

## Features

- 3D table of 118 elements; a camera flight into the element shows its Bohr model or
  its simple substance in 3D (O₂, bcc iron, graphite).
- Red rays to partner elements; ray thickness shows the number of shared compounds.
  Drag along a ray to walk through the compounds of the pair, most famous first.
- Compound card: 3D molecule or crystal fragment, atom labels, formula, composition,
  molar mass, classes, description, similar compounds and per-record sources.
- Several elements → a cloud of compounds that contain all of them (or only them);
  extra elements light up in cyan.
- Search by formula or name in UA/RU/EN; every scene has its own URL.
- Similar elements and compounds from a vector model (PPMI + SVD, pgvector).
- Photos of substances and elements from Wikimedia Commons, with author and license.
- The cloud can be filtered: all, organic, inorganic or minerals.
- Keyboard access to all elements, reduced-motion support, adaptive rendering quality.

## Dataset

27 202 compounds that have a Wikipedia article in English, Russian or Ukrainian
(selection rules: [ADR 0004](docs/adr/0004-data-sources-and-selection.md)); 25 554 (94%)
have a 3D model: PubChem conformers, crystals from Materials Project, RDKit for the rest;
salts and hydrates are shown as ions side by side. Each dataset version is a GitHub release
(`data-<version>`); `data/DATASET` says which one the site uses.

## Architecture

```text
sources ──► pipeline (Python, offline) ──► dataset ──┬─► PostgreSQL + pgvector ──► FastAPI ──┐
PubChem, Materials Project,                           │                                       ├─► CDN ──► web (React + R3F)
Wikidata, Wikipedia                                   └─► static export (JSON) ───────────────┘
```

| Part | Stack |
| --- | --- |
| `apps/web` | React 19, TypeScript, Vite, three.js, React Three Fiber, drei, zustand, TanStack Query, i18next, Tailwind CSS |
| `apps/api` | Python 3.12, FastAPI, SQLAlchemy 2 (async), asyncpg, Alembic, PostgreSQL 17 + pgvector, pg_trgm |
| `pipeline` | Python 3.12, httpx, tenacity, RDKit, spglib, numpy, Typer |
| CI/CD | GitHub Actions (checks, data builds, screenshots, load and speed tests), GitHub Pages |

Design decisions are recorded in [docs/adr](docs/adr); the plan is in
[docs/plan.md](docs/plan.md).

## Run it

- Demo: nothing to do — every push to `main` rebuilds and deploys the site.
- Own server (Docker Compose), managed cloud services or local development: see
  [docs/DEPLOY.md](docs/DEPLOY.md).

## Performance budgets

| Metric | Budget | Measured (CI) |
| --- | --- | --- |
| Initial JavaScript (gzip) | ≤ 400 KB | ≈ 380 KB |
| LCP on 4G (9 Mbit/s, 170 ms) | ≤ 2.5 s | ≈ 0.85 s desktop, ≈ 1.1 s phone (CPU ×4) |
| Draw calls per frame | ≤ 100 | 3–14 |
| 3D structure file (gzip), 95% of compounds | ≤ 20 KB | ≈ 1.5 KB |
| API p95 without cache, 4 parallel requests, full dataset | ≤ 300 ms | 14–66 ms per endpoint |

## Data sources and licenses

The source code is MIT-licensed. Chemical data keeps the licenses of its sources:
Wikidata (CC0), Wikipedia (CC BY-SA 4.0), PubChem (NIH, public domain), Materials
Project (CC BY 4.0), Wikimedia Commons (license per photo). GNoME data (CC BY-NC) is
excluded. The site's About page and
[docs/data-sources.md](docs/data-sources.md) list the details.

## License

[MIT](LICENSE) © 2026 Ihor Korenets
