"""`kgfs doctor` command."""

from __future__ import annotations

import os
import sys
from importlib.util import find_spec
from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import console, optional_config_runtime, read_schema_version_if_present
from kgfs.database import check_fts5_available
from kgfs.platform_utils import platform_diagnostics
from kgfs.resources import executable_path, is_frozen
from kgfs.safety import risk_warning
from kgfs.semantic import get_semantic_status


def register(app: typer.Typer) -> None:
    app.command()(doctor)


def doctor(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Show environment and configuration diagnostics."""

    app_paths, resolved_config_path, resolved_database_path, config = optional_config_runtime(
        config_path,
        database_path,
        project_local,
    )
    diagnostics = platform_diagnostics()
    database_exists = resolved_database_path.exists()
    schema_version = read_schema_version_if_present(resolved_database_path) if database_exists else "not initialized"
    table = Table(title="KGFS Doctor")
    table.add_column("Check")
    table.add_column("Value")
    table.add_row("Platform", diagnostics["platform"])
    table.add_row("Python", sys.version.split()[0])
    table.add_row("Packaged/frozen", str(is_frozen()))
    table.add_row("Executable path", str(executable_path()))
    table.add_row("Config path", str(resolved_config_path))
    table.add_row("Config exists", str(resolved_config_path.exists()))
    table.add_row("Data path", str(app_paths.data_dir))
    table.add_row("Cache path", str(app_paths.cache_dir))
    table.add_row("Log path", str(app_paths.log_dir))
    table.add_row("Database path", str(resolved_database_path))
    table.add_row("Database exists", str(database_exists))
    table.add_row("Schema version", str(schema_version))
    table.add_row("Path separator", diagnostics["path_separator"])
    table.add_row("Home directory", diagnostics["home_directory"])
    table.add_row("Open files", diagnostics["open_files"])
    table.add_row("Reveal files", diagnostics["reveal_files"])
    table.add_row("SQLite FTS5", "available" if check_fts5_available() else "missing")
    table.add_row("Semantic", get_semantic_status(config.semantic).message)
    table.add_row("PDF support", "available" if find_spec("pypdf") else "missing optional dependency")
    table.add_row("DOCX support", "available" if find_spec("docx") else "missing optional dependency")
    table.add_row("OpenAI SDK", "available" if find_spec("openai") else "missing unless using AI Assist")
    console.print(table)

    folder_table = Table(title="Configured Folders")
    folder_table.add_column("Folder")
    folder_table.add_column("Exists")
    folder_table.add_column("Readable")
    folder_table.add_column("Warning")
    for folder in config.indexed_folders:
        exists = folder.exists()
        readable = os.access(folder, os.R_OK) if exists else False
        folder_table.add_row(str(folder), str(exists), str(readable), risk_warning(folder))
    console.print(folder_table)
