# p3d-pipeline

Offline data pipeline for Periodic Table 3D. It downloads public chemistry data,
normalizes it and writes a versioned dataset that the API loads.

```text
fetch  → raw responses cached in data/cache (PubChem, Wikidata/QLever, Wikipedia, OPTIMADE)
build  → data/build/<version>/: elements.json, compounds.jsonl, structures/*.json, report
```

Run (in CI, the dev container has no internet):

```bash
uv sync
uv run p3d-pipeline build --out ../data/build --limit 0
uv run pytest
```

See docs/adr/0004-data-sources-and-selection.md for the source and selection rules.
