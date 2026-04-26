"""Project workflow commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import connect_runtime, console, format_timestamp, print_results
from kgfs.workflows.notes import notes_for_file
from kgfs.workflows.projects import (
    add_results_to_project,
    create_project,
    delete_project,
    get_project_items,
    list_projects,
    project_search,
    remove_files_from_project,
)


project_app = typer.Typer(help="Manage local manual projects.")


def register(app: typer.Typer) -> None:
    app.add_typer(project_app, name="project")


@project_app.command("create")
def project_create_cmd(
    name: str,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    description: str | None = typer.Option(None, "--description", help="Project description."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        project = create_project(conn, name, description)
        console.print(f"Created project: {project.name}")
    finally:
        conn.close()


@project_app.command("list")
def project_list_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        table = Table(title="Projects")
        table.add_column("Name")
        table.add_column("Description")
        for project in list_projects(conn):
            table.add_row(project.name, project.description or "")
        console.print(table)
    finally:
        conn.close()


@project_app.command("add")
def project_add_cmd(
    name: str,
    result_ids: list[int] = typer.Argument(..., help="Latest result IDs to add."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    role: str | None = typer.Option(None, "--role", help="Optional project role."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        try:
            summary = add_results_to_project(conn, name, result_ids, role=role)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        console.print(f"Added {summary.added}; skipped {summary.skipped}.")
    finally:
        conn.close()


@project_app.command("remove")
def project_remove_cmd(
    name: str,
    file_ids: list[int] = typer.Argument(..., help="Latest result IDs or file IDs to remove."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        console.print(f"Removed {remove_files_from_project(conn, name, file_ids)} items.")
    finally:
        conn.close()


@project_app.command("show")
def project_show_cmd(
    name: str,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        table = Table(title=f"Project: {name}")
        table.add_column("File ID")
        table.add_column("Name")
        table.add_column("Role")
        table.add_column("Modified")
        table.add_column("Notes")
        for item in get_project_items(conn, name):
            notes = "; ".join(note.note for note in notes_for_file(conn, item.file_id))
            table.add_row(str(item.file_id), item.file_name, item.role or "", format_timestamp(item.modified_time), notes)
        console.print(table)
    finally:
        conn.close()


@project_app.command("delete")
def project_delete_cmd(
    name: str,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        console.print("Deleted project." if delete_project(conn, name) else "Project not found.")
    finally:
        conn.close()


@project_app.command("search")
def project_search_cmd(
    name: str,
    query: str,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Maximum results."),
) -> None:
    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        try:
            report = project_search(conn, name, query, config, limit=limit)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        print_results(f"Project {name}: {query}", report.results)
    finally:
        conn.close()
