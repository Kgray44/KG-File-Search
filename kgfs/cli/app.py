"""Typer application wiring for KG File Search."""

from __future__ import annotations

import typer

from kgfs.cli.commands import (
    assignment,
    capabilities,
    collections,
    compare,
    config,
    db,
    deep,
    doctor,
    duplicates,
    folders,
    graph,
    health,
    index,
    init,
    integrations,
    maintenance,
    media,
    metadata,
    models,
    notes,
    open_reveal,
    ocr,
    profiles,
    projects,
    quickstart,
    search,
    semantic,
    similar,
    saved_searches,
    stats,
    tags,
    timeline,
    research,
    serve,
    tui,
    vector,
    versions,
    version,
    web,
    why,
)
from kgfs.version import __version__

app = typer.Typer(help="KG File Search: private local-first file search.", no_args_is_help=True)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"KGFS {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version_requested: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show KGFS version and exit.",
    ),
) -> None:
    """KG File Search: private local-first file search."""


def _register_commands() -> None:
    for module in (
        init,
        doctor,
        version,
        quickstart,
        capabilities,
        db,
        config,
        index,
        search,
        deep,
        similar,
        compare,
        timeline,
        research,
        duplicates,
        profiles,
        saved_searches,
        collections,
        tags,
        notes,
        assignment,
        projects,
        graph,
        health,
        metadata,
        versions,
        serve,
        integrations,
        tui,
        semantic,
        maintenance,
        media,
        models,
        folders,
        open_reveal,
        ocr,
        stats,
        vector,
        web,
        why,
    ):
        module.register(app)


_register_commands()


if __name__ == "__main__":
    app()
