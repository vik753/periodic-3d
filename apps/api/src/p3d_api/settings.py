"""Configuration from environment variables (no secrets in code)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

DEFAULT_DATABASE_URL = "postgresql+asyncpg://p3d:p3d@localhost:5432/p3d"


def normalize_database_url(url: str) -> str:
    """Accept the URL forms that hosting providers print.

    'postgres://…' and 'postgresql://…' become 'postgresql+asyncpg://…'.
    asyncpg names the TLS option 'ssl', not 'sslmode', and does not know
    'channel_binding', so the query string is translated.
    """
    url = url.strip()
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+asyncpg://" + url[len(prefix) :]
            break
    parts = urlsplit(url)
    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key == "sslmode":
            query.append(("ssl", value))
        elif key != "channel_binding":
            query.append((key, value))
    return urlunsplit(parts._replace(query=urlencode(query)))


@dataclass(frozen=True)
class Settings:
    database_url: str = DEFAULT_DATABASE_URL
    cors_origins: tuple[str, ...] = ("*",)
    # Browsers keep responses for a short time; CDNs keep them until the next dataset.
    cache_max_age: int = 300
    cache_s_maxage: int = 86400
    version_ttl: float = 30.0  # seconds between dataset-version checks
    build_id: str = "dev"  # part of the ETag: a new API build invalidates cached answers


def load_settings() -> Settings:
    origins = os.environ.get("P3D_CORS_ORIGINS", "*")
    return Settings(
        database_url=normalize_database_url(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)),
        cors_origins=tuple(origin.strip() for origin in origins.split(",") if origin.strip()),
        cache_max_age=int(os.environ.get("P3D_CACHE_MAX_AGE", "300")),
        cache_s_maxage=int(os.environ.get("P3D_CACHE_S_MAXAGE", "86400")),
        build_id=os.environ.get("P3D_BUILD_ID", "dev"),
    )
