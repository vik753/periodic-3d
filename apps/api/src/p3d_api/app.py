"""FastAPI application: read-only endpoints under /api/v1 with CDN-friendly caching."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from . import __version__
from .db import Database
from .repository import NoDatasetError, Repository
from .schemas import (
    CompoundDetail,
    CompoundIndex,
    CompoundQuery,
    ElementDetail,
    ElementList,
    Health,
    MaterialList,
    MaterialPairs,
    MaterialShard,
    Meta,
    PairDetail,
    SearchResult,
)
from .settings import Settings, load_settings


class VersionCache:
    """Data version for ETags, refreshed every few seconds (a new load changes it).

    It joins the dataset version and the GNoME layer version: reloading either one
    changes every ETag.
    """

    def __init__(self, database: Database, ttl: float) -> None:
        self._database = database
        self._ttl = ttl
        self._value: str | None = None
        self._checked = float("-inf")

    async def get(self) -> str | None:
        now = time.monotonic()
        if now - self._checked >= self._ttl:
            async with self._database.session() as session:
                repo = Repository(session)
                try:
                    version = await repo.version()
                except NoDatasetError:
                    version = None
                layer = await repo.gnome()
                self._value = f"{version}+{layer[0]}" if version and layer else version
            self._checked = now
        return self._value


async def get_repository(request: Request) -> AsyncIterator[Repository]:
    database: Database = request.app.state.database
    async with database.session() as session:
        yield Repository(session)


Repo = Annotated[Repository, Depends(get_repository)]

router = APIRouter(prefix="/api/v1")


@router.get("/meta", response_model=Meta, summary="Dataset version, counts and licenses")
async def read_meta(repo: Repo) -> Meta:
    return await repo.meta()


@router.get("/elements", response_model=ElementList, summary="All 118 elements")
async def read_elements(repo: Repo) -> ElementList:
    return await repo.elements()


@router.get("/elements/{symbol}", response_model=ElementDetail, summary="One element with partners and top compounds")
async def read_element(symbol: str, repo: Repo) -> ElementDetail:
    element = await repo.element(symbol)
    if element is None:
        raise HTTPException(status_code=404, detail=f"unknown element: {symbol}")
    return element


@router.get("/compounds", response_model=CompoundQuery, summary="Compounds of a set of elements")
async def query_compounds(
    repo: Repo,
    elements: Annotated[str, Query(description="Comma-separated element symbols, e.g. Fe,O")],
    mode: Annotated[
        Literal["contains", "only"], Query(description="contains: at least these; only: exactly these")
    ] = "contains",
    limit: Annotated[int, Query(ge=1, le=200)] = 60,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CompoundQuery:
    try:
        return await repo.query(elements.split(","), mode, limit, offset)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/compounds/{compound_id}", response_model=CompoundDetail, summary="Compound card with 3D structure")
async def read_compound(compound_id: str, repo: Repo) -> CompoundDetail:
    compound = await repo.compound(compound_id)
    if compound is None:
        raise HTTPException(status_code=404, detail=f"unknown compound: {compound_id}")
    return compound


@router.get("/pairs/{pair}", response_model=PairDetail, summary="Compounds of two elements, e.g. O-Fe")
async def read_pair(pair: str, repo: Repo) -> PairDetail:
    parts = pair.split("-")
    result = await repo.pair(parts[0], parts[1]) if len(parts) == 2 else None
    if result is None:
        raise HTTPException(status_code=404, detail=f"no compounds for pair: {pair}")
    return result


@router.get("/search", response_model=SearchResult, summary="Find compounds by formula or name (UA/RU/EN)")
async def search(
    repo: Repo,
    q: Annotated[str, Query(min_length=1, max_length=80, description="Formula or name, e.g. h2o, гематит")],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> SearchResult:
    return await repo.search(q, limit)


@router.get("/index", response_model=CompoundIndex, summary="Compact list of all compounds")
async def read_index(repo: Repo) -> CompoundIndex:
    return await repo.index()


NO_MATERIALS = "predicted materials are not loaded"


@router.get(
    "/materials/pairs",
    response_model=MaterialPairs,
    summary="Predicted materials (GNoME) per element and per pair of elements",
)
async def read_material_pairs(repo: Repo) -> MaterialPairs:
    result = await repo.material_pairs()
    if result is None:
        raise HTTPException(status_code=404, detail=NO_MATERIALS)
    return result


@router.get(
    "/materials/shard/{prefix}",
    response_model=MaterialShard,
    summary="Predicted materials whose id starts with these 4 hex characters, with unit cells",
)
async def read_material_shard(prefix: str, repo: Repo) -> MaterialShard:
    result = await repo.material_shard(prefix)
    if result is None:
        raise HTTPException(status_code=404, detail=f"no predicted materials in shard: {prefix}")
    return result


@router.get(
    "/materials/by-element/{symbol}",
    response_model=MaterialList,
    summary="All predicted materials that contain an element, simplest and most stable first",
)
async def read_materials_by_element(symbol: str, repo: Repo) -> MaterialList:
    result = await repo.materials_by_element(symbol)
    if result is None:
        raise HTTPException(status_code=404, detail=f"no predicted materials with: {symbol}")
    return result


def _etag_matches(header: str | None, etag: str) -> bool:
    if not header:
        return False
    candidates = [value.strip() for value in header.split(",")]
    bare = etag.removeprefix("W/")
    return "*" in candidates or any(value.removeprefix("W/") == bare for value in candidates)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    database = Database(settings.database_url)
    versions = VersionCache(database, settings.version_ttl)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await database.dispose()

    app = FastAPI(
        title="Periodic Table 3D API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.state.database = database
    app.state.settings = settings
    app.state.versions = versions

    async def no_dataset(_: Request, __: Exception) -> Response:
        return JSONResponse(status_code=503, content={"detail": "dataset is not loaded"})

    async def cache_headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Same dataset → same answers: one ETag per dataset and build; 304 when unchanged."""
        if request.method not in ("GET", "HEAD") or not request.url.path.startswith("/api/v1/"):
            return await call_next(request)
        version = await versions.get()
        etag = f'W/"{version}-{settings.build_id}"' if version else None
        cache_control = (
            f"public, max-age={settings.cache_max_age}, s-maxage={settings.cache_s_maxage}, "
            "stale-while-revalidate=86400"
        )
        if etag and _etag_matches(request.headers.get("if-none-match"), etag):
            return Response(status_code=304, headers={"ETag": etag, "Cache-Control": cache_control})
        response = await call_next(request)
        if response.status_code == 200 and etag:
            response.headers["ETag"] = etag
            response.headers["Cache-Control"] = cache_control
        elif response.status_code in (400, 404):
            response.headers["Cache-Control"] = "public, max-age=60"
        else:
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health", response_model=Health, include_in_schema=False)
    async def health() -> Health:
        return Health(status="ok", version=await versions.get())

    app.add_exception_handler(NoDatasetError, no_dataset)
    app.include_router(router)
    app.add_middleware(BaseHTTPMiddleware, dispatch=cache_headers)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "HEAD", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["ETag"],
        max_age=86400,
    )
    return app
