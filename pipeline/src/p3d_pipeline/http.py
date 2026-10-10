"""Polite HTTP fetching with a disk cache, per-host rate limits and retries.

Every response is cached on disk by URL, so re-running the pipeline does not hit the
sources again. A missing resource (404) is cached as a marker file.
"""

from __future__ import annotations

import hashlib
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlencode, urlparse

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

USER_AGENT = "periodic-3d/0.1 (https://github.com/vik753/periodic-3d; data pipeline)"

# Requests per second per host. PubChem asks for at most 5.
DEFAULT_RATES: dict[str, float] = {
    "pubchem.ncbi.nlm.nih.gov": 4.0,
    "qlever.cs.uni-freiburg.de": 1.0,
    "query.wikidata.org": 1.0,
    "optimade.materialsproject.org": 3.0,
    "en.wikipedia.org": 10.0,
    "ru.wikipedia.org": 10.0,
    "uk.wikipedia.org": 10.0,
}
FALLBACK_RATE = 2.0


class RetryableError(RuntimeError):
    """A transient server or network problem worth retrying."""


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

    def _throttle(self, host: str) -> None:
        interval = 1.0 / self.rates.get(host, FALLBACK_RATE)
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
    ) -> bytes | None:
        """GET a URL. Returns the body, or None when the resource does not exist."""
        path = self._cache_path(url, params)
        missing = path.with_suffix(".missing")
        if use_cache and path.exists():
            self.stats["cache_hit"] += 1
            return path.read_bytes()
        if use_cache and missing.exists():
            self.stats["cache_missing"] += 1
            return None
        body = self._fetch(url, params, accept)
        path.parent.mkdir(parents=True, exist_ok=True)
        if body is None:
            missing.touch()
            self.stats["missing"] += 1
            return None
        path.write_bytes(body)
        self.stats["fetched"] += 1
        return body

    @retry(
        retry=retry_if_exception_type((RetryableError, httpx.TransportError)),
        wait=wait_exponential(multiplier=2, min=2, max=90),
        stop=stop_after_attempt(7),
        reraise=True,
    )
    def _fetch(self, url: str, params: Mapping[str, str] | None, accept: str | None) -> bytes | None:
        host = urlparse(url).hostname or ""
        self._throttle(host)
        headers = {"Accept": accept} if accept else {}
        response = self.client.get(url, params=params, headers=headers)
        status = response.status_code
        if status == 404:
            return None
        if status == 400 and host == "pubchem.ncbi.nlm.nih.gov":
            # PubChem answers 400 for records without the requested data.
            return None
        if status in (429, 500, 502, 503, 504):
            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                time.sleep(min(int(retry_after), 120))
            self.stats[f"retry_{status}"] += 1
            raise RetryableError(f"HTTP {status} for {url}")
        response.raise_for_status()
        return response.content
