"""Wikipedia intro extracts (plain text) in batches of 20 titles per request."""

from __future__ import annotations

import json
from collections.abc import Iterable

from ..http import Fetcher

BATCH = 20
MAX_SENTENCES = 3


def extracts(fetcher: Fetcher, language: str, titles: Iterable[str]) -> dict[str, str]:
    """Map article title → first sentences of the article (plain text)."""
    unique = sorted(set(titles))
    result: dict[str, str] = {}
    endpoint = f"https://{language}.wikipedia.org/w/api.php"
    for start in range(0, len(unique), BATCH):
        batch = unique[start : start + BATCH]
        body = fetcher.get(
            endpoint,
            {
                "action": "query",
                "prop": "extracts",
                "exintro": "1",
                "explaintext": "1",
                "exsentences": str(MAX_SENTENCES),
                "exlimit": str(BATCH),
                "redirects": "1",
                "format": "json",
                "formatversion": "2",
                "titles": "|".join(batch),
            },
        )
        if body is None:
            continue
        query = json.loads(body).get("query", {})
        # Map normalized and redirected titles back to the requested ones.
        aliases: dict[str, str] = {title: title for title in batch}
        for step in ("normalized", "redirects"):
            for change in query.get(step, []):
                source = aliases.get(change["from"], change["from"])
                aliases[change["to"]] = source
        for page in query.get("pages", []):
            text = (page.get("extract") or "").strip()
            requested = aliases.get(page.get("title", ""))
            if requested and text:
                result[requested] = text
    return result
