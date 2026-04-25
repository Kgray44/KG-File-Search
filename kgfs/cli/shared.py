"""Shared CLI helpers."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from kgfs.ai import AIError
from kgfs.core.app_dirs import get_app_paths, resolve_config_path, resolve_database_path
from kgfs.core.config import KGFSConfig, load_config
from kgfs.db import connect_database, initialize_database
from kgfs.db.migrations import get_schema_version

console = Console()


def runtime(
    config_path: Path | None,
    database_path: Path | None,
    project_local: bool,
):
    app_paths = get_app_paths(project_local=project_local, project_root=Path.cwd())
    resolved_config_path = resolve_config_path(app_paths, config_path)
    config = load_config(resolved_config_path)
    resolved_database_path = resolve_database_path(app_paths, database_path, config.database_path)
    config = config.model_copy(update={"database_path": resolved_database_path})
    return app_paths, resolved_config_path, resolved_database_path, config


def connect_runtime(config_path: Path | None, database_path: Path | None, project_local: bool):
    app_paths, resolved_config_path, resolved_database_path, config = runtime(config_path, database_path, project_local)
    conn = connect_database(resolved_database_path)
    initialize_database(conn)
    return app_paths, resolved_config_path, resolved_database_path, config, conn


def optional_config_runtime(
    config_path: Path | None,
    database_path: Path | None,
    project_local: bool,
):
    app_paths = get_app_paths(project_local=project_local, project_root=Path.cwd())
    resolved_config_path = resolve_config_path(app_paths, config_path)
    config = load_config(resolved_config_path) if resolved_config_path.exists() else KGFSConfig()
    resolved_database_path = resolve_database_path(app_paths, database_path, config.database_path)
    config = config.model_copy(update={"database_path": resolved_database_path})
    return app_paths, resolved_config_path, resolved_database_path, config


def print_results(title: str, results) -> None:
    table = Table(title=title)
    table.add_column("ID", justify="right")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Source")
    table.add_column("Score", justify="right")
    table.add_column("Modified")
    table.add_column("Path")
    table.add_column("Snippet")
    for result in results:
        table.add_row(
            str(result.result_id),
            result.file_name,
            result.extension,
            _format_result_source(result),
            f"{result.score:.3f}",
            format_timestamp(result.modified_time),
            str(result.path),
            result.snippet,
        )
    console.print(table)
    if not results:
        console.print("No results.")


def _format_result_source(result) -> str:
    source = str(result.metadata.get("extraction_source", "text") if result.metadata else "text")
    if source.startswith("ocr"):
        kind = result.metadata.get("ocr_source_kind") if result.metadata else None
        return "OCR PDF" if kind == "pdf" else "OCR"
    return ""


def ensure_ai_ready(config, *, feature: str) -> None:
    if not config.ai.enabled:
        raise AIError("AI Assist is disabled. Set ai.enabled: true in config.yaml to opt in.")
    if feature == "rerank" and not config.ai.allow_rerank:
        raise AIError("AI rerank is disabled by ai.allow_rerank: false.")
    if feature == "answer" and not config.ai.allow_answer_synthesis:
        raise AIError("AI answer synthesis is disabled by ai.allow_answer_synthesis: false.")


def preview_or_confirm_ai_context(context: str, ai_settings, preview_only: bool) -> bool:
    if preview_only or ai_settings.preview_context_before_send:
        console.print("[bold]AI Context Preview[/bold]")
        console.print(context)
    if preview_only:
        console.print("Preview only; no API call was made.")
        return False
    if ai_settings.require_confirmation:
        return typer.confirm("Send this context to OpenAI?", default=False)
    return True


def format_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M")


def format_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def read_schema_version_if_present(database_path: Path) -> str:
    try:
        conn = sqlite3.connect(database_path)
        try:
            return str(get_schema_version(conn))
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return f"unreadable ({exc})"
