"""Folder config management commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.app_dirs import get_app_paths, resolve_config_path
from kgfs.cli.shared import console
from kgfs.config_commands import add_indexed_folder, list_indexed_folders, remove_indexed_folder
from kgfs.safety import risk_warning


def register(app: typer.Typer) -> None:
    app.command("add-folder")(add_folder_cmd)
    app.command("remove-folder")(remove_folder_cmd)
    app.command("list-folders")(list_folders_cmd)


def add_folder_cmd(
    folder: Path = typer.Argument(..., help="Folder to add to indexed_folders."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Add a folder to config.yaml without indexing it immediately."""

    app_paths = get_app_paths(project_local=project_local, project_root=Path.cwd())
    resolved_config_path = resolve_config_path(app_paths, config_path)
    result = add_indexed_folder(resolved_config_path, folder)
    console.print(f"Config: [bold]{resolved_config_path}[/bold]")
    console.print("Added folder." if result.added else "Folder is already configured.")
    console.print(str(result.path))
    if not result.exists:
        console.print("[yellow]Warning:[/yellow] folder does not exist yet.")
    if result.warning:
        console.print(f"[yellow]Warning:[/yellow] {result.warning}")


def remove_folder_cmd(
    folder: Path = typer.Argument(..., help="Folder to remove from indexed_folders."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Remove a folder from config.yaml without touching files or the index."""

    app_paths = get_app_paths(project_local=project_local, project_root=Path.cwd())
    resolved_config_path = resolve_config_path(app_paths, config_path)
    result = remove_indexed_folder(resolved_config_path, folder)
    console.print(f"Config: [bold]{resolved_config_path}[/bold]")
    console.print("Removed folder." if result.removed else "Folder was not configured.")


def list_folders_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """List configured indexed folders."""

    app_paths = get_app_paths(project_local=project_local, project_root=Path.cwd())
    resolved_config_path = resolve_config_path(app_paths, config_path)
    folders = list_indexed_folders(resolved_config_path)
    table = Table(title="Indexed Folders")
    table.add_column("Folder")
    table.add_column("Exists")
    table.add_column("Warning")
    for folder in folders:
        table.add_row(str(folder), str(folder.exists()), risk_warning(folder))
    console.print(table)
