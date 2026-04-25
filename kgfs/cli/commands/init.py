"""`kgfs init` command."""

from __future__ import annotations

from pathlib import Path

import typer

from kgfs.app_dirs import get_app_paths, resolve_config_path
from kgfs.cli.shared import console
from kgfs.config import create_default_config_file


def register(app: typer.Typer) -> None:
    app.command()(init)


def init(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    project_local: bool = typer.Option(False, "--project-local", help="Store config/data under .kgfs in this project."),
) -> None:
    """Create a config file without indexing anything."""

    app_paths = get_app_paths(project_local=project_local, project_root=Path.cwd())
    resolved_config_path = resolve_config_path(app_paths, config_path)
    for directory in (app_paths.config_dir, app_paths.data_dir, app_paths.cache_dir, app_paths.log_dir):
        directory.mkdir(parents=True, exist_ok=True)
    created = create_default_config_file(resolved_config_path)
    console.print(f"Config: [bold]{resolved_config_path}[/bold]")
    console.print(f"Data:   [bold]{app_paths.data_dir}[/bold]")
    console.print(f"Cache:  [bold]{app_paths.cache_dir}[/bold]")
    console.print("Created config file." if created else "Config file already exists; left it unchanged.")
    console.print("Edit indexed_folders, then run: [bold]kgfs index[/bold]")
