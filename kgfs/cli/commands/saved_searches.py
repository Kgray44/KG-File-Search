"""Saved search commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import connect_runtime, console, print_results
from kgfs.workflows.saved_searches import delete_saved_search, list_saved_searches, run_saved_search, save_search


def register(app: typer.Typer) -> None:
    app.command("save-search", help="Save a named local search.")(save_search_cmd)
    app.command("run-search", help="Run a saved local search.")(run_search_cmd)
    app.command("list-searches", help="List saved local searches.")(list_searches_cmd)
    app.command("delete-search", help="Delete a saved local search.")(delete_search_cmd)


def save_search_cmd(
    name: str,
    query: str,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    mode: str | None = typer.Option(None, "--mode", help="Search mode."),
    ext: list[str] | None = typer.Option(None, "--ext", help="Extension filter."),
    folder: str | None = typer.Option(None, "--folder", help="Folder/path substring filter."),
    after: str | None = typer.Option(None, "--after", help="Only files modified on/after YYYY-MM-DD."),
    before: str | None = typer.Option(None, "--before", help="Only files modified on/before YYYY-MM-DD."),
    replace: bool = typer.Option(False, "--replace", help="Replace an existing saved search."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        filters = {"extensions": ext, "folder": folder, "after": after, "before": before}
        try:
            saved = save_search(conn, name, query, mode=mode, filters=filters, replace=replace)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        console.print(f"Saved search: {saved.name}")
    finally:
        conn.close()


def run_search_cmd(
    name: str,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Maximum results."),
) -> None:
    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        try:
            report = run_saved_search(conn, name, config, limit=limit)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        print_results(f"Saved Search: {name}", report.results)
    finally:
        conn.close()


def list_searches_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        table = Table(title="Saved Searches")
        table.add_column("Name")
        table.add_column("Query")
        table.add_column("Mode")
        for saved in list_saved_searches(conn):
            table.add_row(saved.name, saved.query, saved.mode or "")
        console.print(table)
    finally:
        conn.close()


def delete_search_cmd(
    name: str,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        console.print("Deleted saved search." if delete_saved_search(conn, name) else "Saved search not found.")
    finally:
        conn.close()
