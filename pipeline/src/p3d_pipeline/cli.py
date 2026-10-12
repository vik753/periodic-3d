"""Command line: `p3d-pipeline build ...`."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from . import gnome
from .build import Options, run
from .golden import GOLDEN, verify

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
    uses: Annotated[bool, typer.Option(help="Collect where substances are used (PubChem, ChEBI, USGS).")] = True,
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
        uses=uses,
    )
    typer.echo(run(options))


@app.command("verify")
def verify_command(
    dataset: Annotated[Path, typer.Argument(exists=True, help="Dataset directory (with compounds.jsonl).")],
    report: Annotated[Path | None, typer.Option(help="Write the result as Markdown here.")] = None,
) -> None:
    """Check a built dataset against the golden set of reference substances (Q.3)."""
    problems = verify(dataset)
    lines = [f"# Золотой набор: {len(GOLDEN) - len({p.split()[0] for p in problems})} из {len(GOLDEN)} в порядке", ""]
    lines += [f"- {problem}" for problem in problems] or ["Все эталонные вещества совпали."]
    text = "\n".join(lines) + "\n"
    if report:
        report.write_text(text, encoding="utf-8")
    typer.echo(text)
    if problems:
        raise typer.Exit(code=1)


@app.command("probe-uses")
def probe_uses_command(
    sample: Annotated[Path, typer.Option(help="JSON with the sample compounds and elements.")] = Path(
        "../tools/probe/uses-sample.json"
    ),
    cache: Annotated[Path, typer.Option(help="Cache directory for raw responses.")] = Path("../data/cache"),
    out: Annotated[Path, typer.Option(help="Output directory for the report.")] = Path("out/probe-uses"),
) -> None:
    """Measure where uses of substances can come from (Wikidata P366, PubChem): task U.1."""
    from .probe_uses import run_probe

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    typer.echo(run_probe(sample, cache, out))


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
