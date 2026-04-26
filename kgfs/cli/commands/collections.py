"""Collection commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import connect_runtime, console, format_timestamp
from kgfs.workflows.collections import (
    add_results_to_collection,
    create_collection,
    delete_collection,
    export_collection_markdown,
    get_collection_items,
    list_collections,
    remove_files_from_collection,
)


collection_app = typer.Typer(help="Manage local file collections.")


def register(app: typer.Typer) -> None:
    app.add_typer(collection_app, name="collection")


@collection_app.command("create")
def collection_create_cmd(
    name: str,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    description: str | None = typer.Option(None, "--description", help="Collection description."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        collection = create_collection(conn, name, description)
        console.print(f"Created collection: {collection.name}")
    finally:
        conn.close()


@collection_app.command("list")
def collection_list_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        table = Table(title="Collections")
        table.add_column("Name")
        table.add_column("Description")
        for collection in list_collections(conn):
            table.add_row(collection.name, collection.description or "")
        console.print(table)
    finally:
        conn.close()


@collection_app.command("add")
def collection_add_cmd(
    name: str,
    result_ids: list[int] = typer.Argument(..., help="Latest result IDs to add."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        try:
            summary = add_results_to_collection(conn, name, result_ids)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        console.print(f"Added {summary.added}; skipped {summary.skipped}.")
    finally:
        conn.close()


@collection_app.command("remove")
def collection_remove_cmd(
    name: str,
    file_ids: list[int] = typer.Argument(..., help="Latest result IDs or file IDs to remove."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        console.print(f"Removed {remove_files_from_collection(conn, name, file_ids)} items.")
    finally:
        conn.close()


@collection_app.command("show")
def collection_show_cmd(
    name: str,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        table = Table(title=f"Collection: {name}")
        table.add_column("File ID")
        table.add_column("Name")
        table.add_column("Modified")
        table.add_column("Path")
        for item in get_collection_items(conn, name):
            table.add_row(str(item.file_id), item.file_name, format_timestamp(item.modified_time), str(item.path))
        console.print(table)
    finally:
        conn.close()


@collection_app.command("delete")
def collection_delete_cmd(
    name: str,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        console.print("Deleted collection." if delete_collection(conn, name) else "Collection not found.")
    finally:
        conn.close()


@collection_app.command("export")
def collection_export_cmd(
    name: str,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        console.print(export_collection_markdown(conn, name))
    finally:
        conn.close()
