"""Similar-file search commands."""

from __future__ import annotations

from pathlib import Path

import typer

from kgfs.cli.shared import connect_runtime, console, print_results
from kgfs.search.similar import similar_file, similar_from_result


def register(app: typer.Typer) -> None:
    app.command("similar")(similar_cmd)
    app.command("similar-file")(similar_file_cmd)


def similar_cmd(
    result_id: int = typer.Argument(..., help="Result ID from the latest search/deep results."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Maximum similar files."),
    include_self: bool = typer.Option(False, "--include-self", help="Include the source file in results."),
) -> None:
    """Find files similar to a latest search result."""

    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        try:
            report = similar_from_result(conn, result_id, config, limit=limit, include_self=include_self, save_latest=True)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        _print_report(report)
    finally:
        conn.close()


def similar_file_cmd(
    file_path: Path = typer.Argument(..., help="Path to an already indexed file."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Maximum similar files."),
    include_self: bool = typer.Option(False, "--include-self", help="Include the source file in results."),
) -> None:
    """Find files similar to an already indexed path."""

    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        try:
            report = similar_file(conn, file_path, config, limit=limit, include_self=include_self)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        _print_report(report)
    finally:
        conn.close()


def _print_report(report) -> None:
    console.print(f"[bold]Similar Files[/bold]")
    console.print(f"Source: {report.source.file_name}")
    console.print(f"Strategy: {report.strategy}")
    for warning in report.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")
    print_results("Similar files", report.results)
