"""Command line: migrate, load a dataset, export static JSON, serve."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Annotated

import typer

from .db import Database
from .export import export_static
from .loader import load_dataset, load_gnome, open_dataset
from .migrate import run_migrations
from .settings import load_settings

app = typer.Typer(no_args_is_help=True, add_completion=False, help="Periodic Table 3D API tools.")


@app.callback()
def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@app.command()
def migrate() -> None:
    """Create or upgrade the database schema (DATABASE_URL)."""
    run_migrations(load_settings().database_url)
    typer.echo("schema is up to date")


@app.command()
def load(
    dataset: Annotated[Path, typer.Argument(exists=True, help="Dataset directory or .tar.gz from the pipeline")],
) -> None:
    """Replace the data in the database with a dataset built by the pipeline."""

    async def run() -> None:
        database = Database(load_settings().database_url)
        try:
            with open_dataset(dataset) as root:
                report = await load_dataset(database.engine, root)
        finally:
            await database.dispose()
        typer.echo(
            f"loaded {report.version}: {report.elements} elements, {report.compounds} compounds "
            f"({report.structures} with 3D), {report.pairs} pairs, {report.classes} classes"
        )

    asyncio.run(run())


@app.command("load-gnome")
def load_gnome_command(
    layer: Annotated[Path, typer.Argument(exists=True, help="GNoME layer directory or .tar.gz from the pipeline")],
) -> None:
    """Replace the layer of predicted materials (GNoME, ADR 0007); known compounds stay."""

    async def run() -> None:
        database = Database(load_settings().database_url)
        try:
            with open_dataset(layer) as root:
                report = await load_gnome(database.engine, root)
        finally:
            await database.dispose()
        typer.echo(
            f"loaded {report.version}: {report.materials} materials, {report.pairs} pairs, {report.elements} elements"
        )

    asyncio.run(run())


@app.command("export-static")
def export_static_command(
    out: Annotated[Path, typer.Argument(help="Output directory, e.g. apps/web/dist/data")],
) -> None:
    """Write every API answer as a JSON file for static hosting (GitHub Pages, any CDN)."""

    async def run() -> None:
        database = Database(load_settings().database_url)
        try:
            report = await export_static(database, out)
        finally:
            await database.dispose()
        typer.echo(f"exported {report.version}: {report.files} files, {report.bytes / 1e6:.1f} MB")
        if report.gnome:
            typer.echo(f"of them {report.gnome}: {report.material_files} files, {report.material_bytes / 1e6:.1f} MB")
        if report.missing:
            typer.echo(f"missing: {report.missing[:20]}", err=True)
            raise typer.Exit(code=1)

    asyncio.run(run())


@app.command()
def serve(
    host: Annotated[str, typer.Option(help="Interface to listen on")] = "0.0.0.0",
    port: Annotated[int, typer.Option(help="Port")] = 8000,
    workers: Annotated[int, typer.Option(help="Worker processes")] = 1,
) -> None:
    """Run the API with uvicorn."""
    import uvicorn

    uvicorn.run(
        "p3d_api.main:app",
        host=host,
        port=port,
        workers=workers,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
