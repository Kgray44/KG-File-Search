"""Version finder commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import connect_runtime, console, format_timestamp
from kgfs.intelligence.versions import find_versions_for_path, find_versions_for_result


def register(app: typer.Typer) -> None:
    app.command("versions", help="Find likely versions of a latest result.")(versions_cmd)
    app.command("versions-file", help="Find likely versions of an indexed file path.")(versions_file_cmd)


def versions_cmd(
    result_id: int,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        try:
            candidates = find_versions_for_result(conn, result_id, config)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        _print_versions(candidates)
    finally:
        conn.close()


def versions_file_cmd(
    path: Path,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        try:
            candidates = find_versions_for_path(conn, path, config)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        _print_versions(candidates)
    finally:
        conn.close()


def _print_versions(candidates) -> None:
    table = Table(title="Likely Versions")
    table.add_column("File")
    table.add_column("Relation")
    table.add_column("Score", justify="right")
    table.add_column("Modified")
    table.add_column("Evidence")
    table.add_column("Path")
    for candidate in candidates:
        table.add_row(
            candidate.file_name,
            candidate.relationship,
            f"{candidate.score:.3f}",
            format_timestamp(candidate.modified_time),
            "; ".join(candidate.evidence),
            str(candidate.path),
        )
    console.print(table)
    if not candidates:
        console.print("No likely versions found.")
