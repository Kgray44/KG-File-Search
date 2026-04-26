"""Capability summary command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.capabilities import collect_capabilities
from kgfs.cli.shared import console, optional_config_runtime


def register(app: typer.Typer) -> None:
    app.command("capabilities")(capabilities_cmd)


def capabilities_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Summarize local KGFS feature availability."""

    _, _, resolved_database_path, config = optional_config_runtime(config_path, database_path, project_local)
    config = config.model_copy(update={"database_path": resolved_database_path})
    rows = collect_capabilities(config)

    table = Table(title="KGFS Capabilities")
    table.add_column("Feature")
    table.add_column("Status")
    table.add_column("Details")
    for row in rows:
        table.add_row(row.feature, row.status, row.details)
    console.print(table)
