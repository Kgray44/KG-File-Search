"""Typer application wiring for KG File Search."""

from __future__ import annotations

import typer

from kgfs.cli.commands import (
    assignment,
    collections,
    compare,
    config,
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
    notes,
    open_reveal,
    ocr,
    profiles,
    projects,
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
    web,
    why,
)

app = typer.Typer(help="KG File Search: private local-first file search.")


def _register_commands() -> None:
    for module in (
        init,
        doctor,
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
