"""Optional terminal UI command."""

from __future__ import annotations

from pathlib import Path

import typer

from kgfs.cli.shared import console


def register(app: typer.Typer) -> None:
    app.command("tui")(tui_cmd)


def tui_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    check: bool = typer.Option(False, "--check", help="Check optional TUI dependency without launching."),
) -> None:
    """Launch the optional KGFS terminal UI."""

    from kgfs.tui.app import TextualUnavailableError, launch_tui, textual_available

    if check:
        if textual_available():
            console.print("Textual is available; kgfs tui can launch.")
        else:
            console.print('Textual is not installed. Install with: python -m pip install -e ".[tui]"')
        return
    try:
        launch_tui(config_path=config_path, database_path=database_path, project_local=project_local)
    except TextualUnavailableError as exc:
        raise typer.BadParameter(str(exc)) from exc
