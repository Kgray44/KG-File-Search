"""KGFS version command."""

from __future__ import annotations

import typer

from kgfs.version import __version__


def register(app: typer.Typer) -> None:
    app.command("version")(version_cmd)


def version_cmd() -> None:
    """Show the KGFS version."""

    typer.echo(f"KGFS {__version__}")
