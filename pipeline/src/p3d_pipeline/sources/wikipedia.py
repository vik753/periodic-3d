"""Wikipedia intro extracts (plain text) in batches of 20 titles per request."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from typing import Any

import httpx

from ..http import Fetcher, RetryableError

log = logging.getLogger("p3d.wikipedia")

BATCH = 20
MAX_SENTENCES = 3


MEMO = "wikipedia-extract"


def extracts(fetcher: Fetcher, language: str, titles: Iterable[str]) -> dict[str, str]:
    """Map article title → first sentences of the article (plain text).

    Every answer is also remembered per title (Fetcher.memo_*), so a changed list of
    compounds re-asks only for new titles. An empty memo means "no extract".
    """
    unique = sorted(set(titles))
    result: dict[str, str] = {}
    missing: list[str] = []
    for title in unique:
        remembered = fetcher.memo_get(MEMO, f"{language}|{title}")
        if remembered is None:
            missing.append(title)
        elif remembered:
            result[title] = remembered
    if len(missing) < len(unique):
        log.info("Wikipedia %s: %d of %d titles remembered", language, len(unique) - len(missing), len(unique))
    endpoint = f"https://{language}.wikipedia.org/w/api.php"
    for start in range(0, len(missing), BATCH):
        batch = missing[start : start + BATCH]
        try:
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
        except (RetryableError, httpx.HTTPError) as error:
            fetcher.stats["failed_batches"] += 1
            log.warning("Wikipedia %s extracts failed for %d titles: %s", language, len(batch), error)
            continue
        if body is None:
            continue
        data = json.loads(body)
        found = parse_extracts(data, batch)
        # A cut-off answer ("continue") lacks some extracts: remember only what came.
        complete = "continue" not in data
        for title in batch:
            text = found.get(title, "")
            if text or complete:
                fetcher.memo_put(MEMO, f"{language}|{title}", text)
            if text:
                result[title] = text
    return result


def parse_extracts(data: dict[str, Any], batch: list[str]) -> dict[str, str]:
    """Extracts by requested title; normalized and redirected titles map back."""
    query = data.get("query", {})
    aliases: dict[str, str] = {title: title for title in batch}
    for step in ("normalized", "redirects"):
        for change in query.get(step, []):
            source = aliases.get(change["from"], change["from"])
            aliases[change["to"]] = source
    found: dict[str, str] = {}
    for page in query.get("pages", []):
        text = (page.get("extract") or "").strip()
        requested = aliases.get(page.get("title", ""))
        if requested and text:
            found[requested] = text
    return found
