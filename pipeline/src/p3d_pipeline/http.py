"""Polite HTTP fetching with a disk cache, per-host rate limits and retries.

Every response is cached on disk by URL, so re-running the pipeline does not hit the
sources again. A missing resource (404) is cached as a marker file.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlencode, urlparse

import httpx
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

log = logging.getLogger("p3d.http")

USER_AGENT = "periodic-3d/0.1 (https://github.com/vik753/periodic-3d; data pipeline)"

# Requests per second per host. PubChem allows 5 per second, 400 per minute and
# 300 seconds of server time per minute; heavy 3D requests hit the time limit first.
DEFAULT_RATES: dict[str, float] = {
    "pubchem.ncbi.nlm.nih.gov": 2.0,
    "qlever.cs.uni-freiburg.de": 1.0,
    "query.wikidata.org": 1.0,
    "optimade.materialsproject.org": 3.0,
    "en.wikipedia.org": 10.0,
    "ru.wikipedia.org": 10.0,
    "uk.wikipedia.org": 10.0,
}
FALLBACK_RATE = 2.0

# PubChem reports its load in X-Throttling-Control, e.g.
# "Request Count status: Green (2%), Request Time status: Yellow (61%), Service status: Green (20%)".
# Extra pause per request (seconds) by the worst status.
THROTTLE_PAUSE: dict[str, float] = {"green": 0.0, "yellow": 1.0, "red": 5.0, "black": 60.0}
_STATUS = re.compile(r"status:\s*(green|yellow|red|black)", re.IGNORECASE)
# Without a Retry-After header, wait this long after 429/503 so the per-minute window resets.
BUSY_PAUSE = 20.0


class RetryableError(RuntimeError):
    """A transient server or network problem worth retrying."""


def throttle_pause(header: str | None) -> float:
    """Extra pause before the next request to a host that reports its load."""
    if not header:
        return 0.0
    return max((THROTTLE_PAUSE[match.lower()] for match in _STATUS.findall(header)), default=0.0)


class Fetcher:
    def __init__(
        self,
        cache_dir: Path,
        *,
        rates: Mapping[str, float] | None = None,
        user_agent: str = USER_AGENT,
        timeout: float = 90.0,
    ) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rates = {**DEFAULT_RATES, **(rates or {})}
        self.client = httpx.Client(
            headers={"User-Agent": user_agent},
            timeout=httpx.Timeout(timeout, connect=20.0),
            follow_redirects=True,
        )
        self._last_request: dict[str, float] = {}
        self._pause: dict[str, float] = {}
        self.stats: Counter[str] = Counter()

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> Fetcher:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _cache_path(self, url: str, params: Mapping[str, str] | None) -> Path:
        key_source = url + ("?" + urlencode(sorted(params.items())) if params else "")
        key = hashlib.sha256(key_source.encode("utf-8")).hexdigest()
        return self.cache_dir / key[:2] / key

    def _memo_path(self, namespace: str, key: str) -> Path:
        digest = hashlib.sha256(f"{namespace}|{key}".encode()).hexdigest()
        return self.cache_dir / "memo" / namespace / digest[:2] / digest

    def memo_get(self, namespace: str, key: str) -> str | None:
        """A small value remembered by key (None: never stored).

        Batched requests cache badly by URL: one title more or less shifts every batch.
        Per-item values survive changes in the batch layout.
        """
        path = self._memo_path(namespace, key)
        if not path.exists():
            return None
        self.stats["memo_hit"] += 1
        return path.read_text(encoding="utf-8")

    def memo_put(self, namespace: str, key: str, value: str) -> None:
        path = self._memo_path(namespace, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    def _throttle(self, host: str) -> None:
        interval = 1.0 / self.rates.get(host, FALLBACK_RATE) + self._pause.get(host, 0.0)
        last = self._last_request.get(host)
        if last is not None:
            wait = interval - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
        self._last_request[host] = time.monotonic()

    def get(
        self,
        url: str,
        params: Mapping[str, str] | None = None,
        *,
        accept: str | None = None,
        use_cache: bool = True,
        cache_only: bool = False,
        attempts: int = 10,
    ) -> bytes | None:
        """GET a URL. Returns the body, or None when the resource does not exist.

        cache_only: answer from the disk cache or return None without asking the host
        (used when a host has throttled us; the next run fills the gap).
        """
        path = self._cache_path(url, params)
        missing = path.with_suffix(".missing")
        if use_cache and path.exists():
            self.stats["cache_hit"] += 1
            return path.read_bytes()
        if use_cache and missing.exists():
            self.stats["cache_missing"] += 1
            return None
        if cache_only:
            self.stats["skipped_offline"] += 1
            return None
        body = self._fetch_with_retries(url, params, accept, attempts)
        path.parent.mkdir(parents=True, exist_ok=True)
        if body is None:
            missing.touch()
            self.stats["missing"] += 1
            return None
        path.write_bytes(body)
        self.stats["fetched"] += 1
        return body

    def _fetch_with_retries(
        self, url: str, params: Mapping[str, str] | None, accept: str | None, attempts: int
    ) -> bytes | None:
        """Retry transient errors with exponential back-off (5 s, 15 s, 45 s, then 120 s)."""
        retrying = Retrying(
            retry=retry_if_exception_type((RetryableError, httpx.TransportError)),
            wait=wait_exponential(multiplier=3, min=5, max=120),
            stop=stop_after_attempt(attempts),
            reraise=True,
        )
        body: bytes | None = retrying(self._fetch, url, params, accept)
        return body

    def _fetch(self, url: str, params: Mapping[str, str] | None, accept: str | None) -> bytes | None:
        host = urlparse(url).hostname or ""
        self._throttle(host)
        headers = {"Accept": accept} if accept else {}
        response = self.client.get(url, params=params, headers=headers)
        status = response.status_code
        pause = throttle_pause(response.headers.get("X-Throttling-Control"))
        if pause != self._pause.get(host, 0.0):
            log.info("%s asks to slow down: +%.1f s per request", host, pause)
            self._pause[host] = pause
        if status == 404:
            return None
        if status == 400 and host == "pubchem.ncbi.nlm.nih.gov":
            # PubChem answers 400 for records without the requested data.
            return None
        if status in (429, 500, 502, 503, 504):
            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                time.sleep(min(int(retry_after), 120))
            elif status in (429, 503):
                time.sleep(BUSY_PAUSE)
            self.stats[f"retry_{status}"] += 1
            raise RetryableError(f"HTTP {status} for {url}")
        response.raise_for_status()
        return response.content
