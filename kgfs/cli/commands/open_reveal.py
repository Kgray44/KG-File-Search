"""Open and reveal commands."""

from __future__ import annotations

from pathlib import Path

import typer

from kgfs.cli.shared import connect_runtime
from kgfs.core.platform_utils import open_file as open_path
from kgfs.core.platform_utils import reveal_file as reveal_path
from kgfs.search import get_latest_result_path


def register(app: typer.Typer) -> None:
    app.command()(open)
    app.command()(reveal)


def open(
    result_id: int,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Open a file from the latest search results."""

    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        file_path = get_latest_result_path(conn, result_id)
        if file_path is None:
            raise typer.BadParameter(f"No latest search result with ID {result_id}")
    finally:
        conn.close()
    open_path(file_path)


def reveal(
    result_id: int,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Reveal a file from the latest search results in the file manager."""

    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        file_path = get_latest_result_path(conn, result_id)
        if file_path is None:
            raise typer.BadParameter(f"No latest search result with ID {result_id}")
    finally:
        conn.close()
    reveal_path(file_path)
