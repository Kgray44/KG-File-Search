"""Config display command."""

from __future__ import annotations

from pathlib import Path

import typer

from kgfs.cli.shared import console
from kgfs.core.app_dirs import get_app_paths, resolve_config_path


def register(app: typer.Typer) -> None:
    app.command("config")(show_config)


def show_config(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Print the active config file."""

    app_paths = get_app_paths(project_local=project_local, project_root=Path.cwd())
    resolved_config_path = resolve_config_path(app_paths, config_path)
    console.print(f"[bold]Config path:[/bold] {resolved_config_path}")
    console.print(resolved_config_path.read_text(encoding="utf-8"))
