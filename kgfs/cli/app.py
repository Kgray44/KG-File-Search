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
    folders,
    index,
    init,
    maintenance,
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
    vector,
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
        profiles,
        saved_searches,
        collections,
        tags,
        notes,
        assignment,
        projects,
        semantic,
        maintenance,
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
