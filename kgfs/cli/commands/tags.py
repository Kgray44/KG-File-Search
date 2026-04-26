"""Tag commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import connect_runtime, console, print_results
from kgfs.workflows.tags import list_all_tags, list_file_tags, list_tagged_files, tag_result, untag_result


def register(app: typer.Typer) -> None:
    app.command("tag", help="Attach local tags to a latest result.")(tag_cmd)
    app.command("untag", help="Remove local tags from a latest result.")(untag_cmd)
    app.command("tags", help="List tags for a latest result.")(tags_cmd)
    app.command("tagged", help="Show files with a local tag.")(tagged_cmd)
    app.command("tag-list", help="List all local tags.")(tag_list_cmd)


def tag_cmd(
    result_id: int,
    tags: list[str] = typer.Argument(..., help="Tags to attach."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        try:
            console.print("Tags: " + ", ".join(tag_result(conn, result_id, tags)))
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
    finally:
        conn.close()


def untag_cmd(
    result_id: int,
    tags: list[str] = typer.Argument(..., help="Tags to remove."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        console.print("Tags: " + ", ".join(untag_result(conn, result_id, tags)))
    finally:
        conn.close()


def tags_cmd(
    result_id: int,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        console.print("Tags: " + ", ".join(list_file_tags(conn, result_id)))
    finally:
        conn.close()


def tagged_cmd(
    tag: str,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        print_results(f"Tagged: {tag}", list_tagged_files(conn, tag, save_latest=True))
    finally:
        conn.close()


def tag_list_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        table = Table(title="Tags")
        table.add_column("Tag")
        for tag in list_all_tags(conn):
            table.add_row(tag)
        console.print(table)
    finally:
        conn.close()
