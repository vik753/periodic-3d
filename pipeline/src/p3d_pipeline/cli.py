"""Command line: `p3d-pipeline build ...`."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from . import gnome
from .build import Options, run

app = typer.Typer(add_completion=False, help="Periodic Table 3D data pipeline.")


@app.callback()
def main() -> None:
    """Fetch public chemistry data and build a versioned dataset."""
    logging.getLogger("httpx").setLevel(logging.WARNING)  # one line per request is too much


@app.command()
def build(
    out: Annotated[Path, typer.Option(help="Output directory for datasets.")] = Path("../data/build"),
    cache: Annotated[Path, typer.Option(help="Cache directory for raw responses.")] = Path("../data/cache"),
    version: Annotated[str, typer.Option(help="Dataset version; default is today's date.")] = "",
    only_elements: Annotated[
        str, typer.Option(help="Comma-separated symbols: keep compounds made only of these elements.")
    ] = "",
    limit: Annotated[int, typer.Option(help="Keep the N most famous compounds (0 = all).")] = 0,
    descriptions: Annotated[bool, typer.Option(help="Fetch Wikipedia descriptions.")] = True,
    structures: Annotated[bool, typer.Option(help="Build 3D structures.")] = True,
) -> None:
    """Build the dataset and print its directory."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    symbols = frozenset(s.strip() for s in only_elements.split(",") if s.strip()) or None
    options = Options(
        out_dir=out,
        cache_dir=cache,
        version=version or datetime.now(UTC).strftime("%Y.%m.%d"),
        only_elements=symbols,
        limit=limit,
        descriptions=descriptions,
        structures=structures,
    )
    typer.echo(run(options))


@app.command("gnome")
def gnome_layer(
    out: Annotated[Path, typer.Option(help="Output directory for GNoME layers.")] = Path("../data/gnome"),
    cache: Annotated[Path, typer.Option(help="Cache directory for downloaded files.")] = Path("../data/cache"),
    version: Annotated[str, typer.Option(help="Layer version; default is today's date.")] = "",
    limit: Annotated[int, typer.Option(help="Keep the first N materials (0 = all).")] = 0,
) -> None:
    """Build the GNoME layer of predicted crystals (ADR 0007) and print its directory."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    options = gnome.GnomeOptions(
        out_dir=out, cache_dir=cache, version=version or datetime.now(UTC).strftime("%Y.%m.%d"), limit=limit
    )
    typer.echo(gnome.run(options))


if __name__ == "__main__":
    app()
