"""Typer application wiring for KG File Search."""

from __future__ import annotations

import typer

from kgfs.cli.commands import (
    config,
    doctor,
    folders,
    index,
    init,
    maintenance,
    open_reveal,
    ocr,
    search,
    semantic,
    stats,
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
