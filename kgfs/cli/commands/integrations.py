"""Local integration status and scaffold commands."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import typer
from rich.table import Table

from kgfs.cli.shared import console, optional_config_runtime
from kgfs.integrations.alfred import export_alfred
from kgfs.integrations.explorer import scaffold_explorer
from kgfs.integrations.finder import scaffold_finder
from kgfs.integrations.powertoys import scaffold_powertoys
from kgfs.integrations.raycast import export_raycast
from kgfs.integrations.status import get_integration_status
from kgfs.integrations.tray import scaffold_tray

integrations_app = typer.Typer(help="Inspect and export local KGFS integration scaffolds.")
raycast_app = typer.Typer(help="Raycast script-command scaffold.")
alfred_app = typer.Typer(help="Alfred workflow scaffold.")
powertoys_app = typer.Typer(help="PowerToys Run scaffold.")
finder_app = typer.Typer(help="Finder Quick Action scaffold.")
explorer_app = typer.Typer(help="Explorer context-menu scaffold.")
tray_app = typer.Typer(help="Tray/menu-bar scaffold.")


def register(app: typer.Typer) -> None:
    integrations_app.add_typer(raycast_app, name="raycast")
    integrations_app.add_typer(alfred_app, name="alfred")
    integrations_app.add_typer(powertoys_app, name="powertoys")
    integrations_app.add_typer(finder_app, name="finder")
    integrations_app.add_typer(explorer_app, name="explorer")
    app.add_typer(integrations_app, name="integrations")
    app.add_typer(tray_app, name="tray")


@integrations_app.command("status")
def integrations_status_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Show local integration scaffold status without changing system settings."""

    optional_config_runtime(config_path, database_path, project_local)
    table = Table(title="KGFS Integrations")
    table.add_column("Integration")
    table.add_column("Supported")
    table.add_column("Scaffold")
    table.add_column("Installed")
    table.add_column("Command")
    table.add_column("Notes")
    for item in get_integration_status():
        table.add_row(
            item.name,
            "yes" if item.supported else "no",
            "yes" if item.scaffold_available else "no",
            "yes" if item.installed else "no",
            item.command,
            item.notes,
        )
    console.print(table)


@raycast_app.command("export")
def raycast_export_cmd(
    output: Path | None = typer.Option(None, "--output", help="Output directory."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _write_scaffold("raycast", export_raycast, output, config_path, database_path, project_local)


@alfred_app.command("export")
def alfred_export_cmd(
    output: Path | None = typer.Option(None, "--output", help="Output directory."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _write_scaffold("alfred", export_alfred, output, config_path, database_path, project_local)


@powertoys_app.command("scaffold")
def powertoys_scaffold_cmd(
    output: Path | None = typer.Option(None, "--output", help="Output directory."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _write_scaffold("powertoys", scaffold_powertoys, output, config_path, database_path, project_local)


@finder_app.command("scaffold")
def finder_scaffold_cmd(
    output: Path | None = typer.Option(None, "--output", help="Output directory."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _write_scaffold("finder", scaffold_finder, output, config_path, database_path, project_local)


@explorer_app.command("scaffold")
def explorer_scaffold_cmd(
    output: Path | None = typer.Option(None, "--output", help="Output directory."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _write_scaffold("explorer", scaffold_explorer, output, config_path, database_path, project_local)


@tray_app.command("status")
def tray_status_cmd() -> None:
    """Show optional tray/menu-bar scaffold status."""

    item = next(status for status in get_integration_status() if status.name == "tray")
    console.print(f"Tray scaffold available: {item.scaffold_available}. Installed: {item.installed}.")
    console.print(item.notes)


@tray_app.command("scaffold")
def tray_scaffold_cmd(
    output: Path | None = typer.Option(None, "--output", help="Output directory."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _write_scaffold("tray", scaffold_tray, output, config_path, database_path, project_local)


def _write_scaffold(
    name: str,
    writer: Callable[[Path], list[Path]],
    output: Path | None,
    config_path: Path | None,
    database_path: Path | None,
    project_local: bool,
) -> None:
    app_paths, _, _, _ = optional_config_runtime(config_path, database_path, project_local)
    output_dir = output or (app_paths.data_dir / "integrations" / name)
    paths = writer(output_dir.expanduser())
    console.print(f"Wrote {name} scaffold to {output_dir}.")
    for path in paths:
        console.print(f"- {path}")
    console.print("No system settings were changed.")
