"""Photos from Wikimedia Commons: a thumbnail URL, the author and the license per file.

Wikidata links items to photos (P18: "Hematite.jpg"). Every Commons file has its own
free license (CC BY-SA, CC BY, CC0, public domain…), so each photo carries its
attribution into the dataset, and the site shows it under the photo.
"""

from __future__ import annotations

import html
import json
import logging
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import quote

import httpx

from ..http import Fetcher, RetryableError

log = logging.getLogger("p3d.commons")

API = "https://commons.wikimedia.org/w/api.php"
BATCH = 50
THUMB_WIDTH = 640
MEMO = "commons-photo"
# Photos only: SVG files on items are usually diagrams, not pictures of the substance.
RASTER = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff")
MAX_AUTHOR_CHARS = 120


@dataclass(frozen=True)
class Photo:
    url: str  # thumbnail, THUMB_WIDTH px wide
    page: str  # file page on Commons (author, license, full size)
    license: str
    author: str | None = None
    license_url: str | None = None

    def as_json(self) -> dict[str, str]:
        data = {"url": self.url, "page": self.page, "license": self.license}
        if self.author:
            data["author"] = self.author
        if self.license_url:
            data["licenseUrl"] = self.license_url
        return data


def plain_text(value: str | None, limit: int = MAX_AUTHOR_CHARS) -> str:
    """Commons metadata is HTML ('<a href=…>Name</a>'): keep the visible text only."""
    if not value:
        return ""
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def photos(fetcher: Fetcher, names: Iterable[str]) -> dict[str, Photo]:
    """Map Commons file name → Photo. Files without a license or a thumbnail are skipped."""
    unique = sorted({name for name in names if name.lower().endswith(RASTER)})
    result: dict[str, Photo] = {}
    missing: list[str] = []
    for name in unique:
        remembered = fetcher.memo_get(MEMO, name)
        if remembered is None:
            missing.append(name)
        elif remembered:
            result[name] = Photo(**json.loads(remembered))
    for start in range(0, len(missing), BATCH):
        batch = missing[start : start + BATCH]
        try:
            body = fetcher.get(
                API,
                {
                    "action": "query",
                    "prop": "imageinfo",
                    "iiprop": "url|extmetadata",
                    "iiurlwidth": str(THUMB_WIDTH),
                    "iiextmetadatafilter": "LicenseShortName|Artist|LicenseUrl",
                    "titles": "|".join(f"File:{name}" for name in batch),
                    "format": "json",
                    "formatversion": "2",
                },
            )
        except (RetryableError, httpx.HTTPError) as error:
            fetcher.stats["failed_batches"] += 1
            log.warning("Commons: %d files failed: %s", len(batch), error)
            continue
        if body is None:
            continue
        data = json.loads(body)
        found = parse_photos(data, batch)
        complete = "continue" not in data
        for name in batch:
            photo = found.get(name)
            if photo or complete:
                fetcher.memo_put(MEMO, name, json.dumps(asdict(photo)) if photo else "")
            if photo:
                result[name] = photo
    return result


def parse_photos(data: dict[str, Any], batch: list[str]) -> dict[str, Photo]:
    query = data.get("query", {})
    aliases = {f"File:{name}": name for name in batch}
    for change in query.get("normalized", []):
        aliases[change["to"]] = aliases.get(change["from"], change["from"])
    found: dict[str, Photo] = {}
    for page in query.get("pages", []):
        name = aliases.get(page.get("title", ""))
        info = (page.get("imageinfo") or [{}])[0]
        thumb = info.get("thumburl") or info.get("url")
        meta = info.get("extmetadata") or {}
        license_name = plain_text((meta.get("LicenseShortName") or {}).get("value"))
        if not name or not thumb or not license_name:
            continue
        found[name] = Photo(
            url=thumb,
            page=info.get("descriptionurl") or f"https://commons.wikimedia.org/wiki/File:{quote(name)}",
            license=license_name,
            author=plain_text((meta.get("Artist") or {}).get("value")) or None,
            license_url=(meta.get("LicenseUrl") or {}).get("value") or None,
        )
    return found
