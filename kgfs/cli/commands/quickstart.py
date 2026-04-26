"""KGFS quickstart command."""

from __future__ import annotations

import typer

from kgfs.quickstart import build_quickstart_text


def register(app: typer.Typer) -> None:
    app.command("quickstart")(quickstart_cmd)


def quickstart_cmd() -> None:
    """Print a safe local-first first-run guide."""

    typer.echo(build_quickstart_text().rstrip())
