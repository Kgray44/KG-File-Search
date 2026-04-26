"""OCR command group."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import console, optional_config_runtime, runtime
from kgfs.db import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.ocr.base import OCRRequest
from kgfs.ocr.registry import get_ocr_backend, list_ocr_backends
from kgfs.ocr.status import get_ocr_status

ocr_app = typer.Typer(help="Inspect and run optional local OCR.")


def register(app: typer.Typer) -> None:
    app.add_typer(ocr_app, name="ocr")


@ocr_app.command("status")
def status_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Show OCR configuration and local backend availability."""

    _, _, resolved_database_path, config = optional_config_runtime(config_path, database_path, project_local)
    conn = None
    if resolved_database_path.exists():
        try:
            conn = connect_database(resolved_database_path)
        except sqlite3.Error:
            conn = None
    try:
        status = get_ocr_status(config, conn)
    finally:
        if conn is not None:
            conn.close()

    table = Table(title="KGFS OCR Status")
    table.add_column("Check")
    table.add_column("Value")
    table.add_row("OCR enabled", str(status.enabled))
    table.add_row("Backend", status.backend_name)
    table.add_row("Backend available", str(status.available))
    table.add_row("Message", status.message)
    table.add_row("Tesseract command", status.command)
    table.add_row("Language", status.language)
    table.add_row("Supported image extensions", ", ".join(status.supported_extensions))
    table.add_row("Max image size", f"{status.max_image_size_mb:g} MB")
    table.add_row("Cache enabled", str(status.cache_enabled))
    table.add_row("Cache entries", str(status.cache_entries))
    table.add_row("OCR indexed files", str(status.indexed_file_count))
    table.add_row("OCR failures", str(status.failure_count))
    if status.install_hint:
        table.add_row("Install hint", status.install_hint)
    console.print(table)


@ocr_app.command("test")
def test_cmd(
    image_path: Path = typer.Argument(..., help="Image file to OCR without indexing it."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Run OCR on one image and print a preview without indexing."""

    _, _, _, config = optional_config_runtime(config_path, database_path, project_local)
    path = image_path.expanduser()
    if not path.exists():
        raise typer.BadParameter(f"Image does not exist: {path}")
    backend = get_ocr_backend(config.ocr.backend)
    result = backend.extract_image(OCRRequest(path=path, config=config, source_kind="image"))
    console.print(f"OCR backend: [bold]{result.backend}[/bold]")
    console.print(f"Status: [bold]{result.status}[/bold]")
    if result.error:
        console.print(f"[red]{result.error}[/red]")
    if result.text:
        console.print("[bold]Text preview[/bold]")
        console.print(result.text[:2000])


@ocr_app.command("advanced-status")
def advanced_status_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Show optional advanced OCR backend status without running OCR."""

    _, _, _, config = optional_config_runtime(config_path, database_path, project_local)
    table = Table(title="KGFS Advanced OCR Status")
    table.add_column("Backend")
    table.add_column("Enabled")
    table.add_column("Available")
    table.add_column("Message")
    table.add_column("Install hint")
    for name in list_ocr_backends():
        backend = get_ocr_backend(name)
        availability = backend.available(config)
        enabled = _advanced_backend_enabled(name, config)
        table.add_row(
            _display_ocr_backend_name(name),
            str(enabled),
            str(availability.available),
            availability.message,
            availability.install_hint or "",
        )
    cloud = config.ocr.cloud_fallback
    table.add_row(
        "Cloud OCR fallback",
        str(cloud.enabled),
        "False",
        "Disabled unless config, explicit CLI allow-cloud, preview, and confirmation are all present."
        if not cloud.enabled
        else "Configured scaffold only; no provider upload is implemented in this phase.",
        "",
    )
    console.print(table)


@ocr_app.command("index")
def index_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Discover OCR-capable files without writing."),
    force: bool = typer.Option(False, "--force", help="Re-extract even if KGFS metadata is unchanged."),
    allow_risky_root: bool = typer.Option(False, "--allow-risky-root", help="Allow risky root folders."),
) -> None:
    """Run normal indexing with OCR-capable extraction enabled by config."""

    _, _, resolved_database_path, config = runtime(config_path, database_path, project_local)
    if not config.ocr.enabled:
        console.print("OCR is disabled. Set ocr.enabled: true in config.yaml, then rerun this command.")
        raise typer.Exit(code=2)
    if not config.indexed_folders:
        console.print("No indexed folders configured. Add folders first, then run kgfs ocr index.")
        return
    conn = connect_database(resolved_database_path)
    initialize_database(conn)
    try:
        summary = index_configured_folders(
            config,
            conn,
            dry_run=dry_run,
            force=force,
            allow_risky_root=allow_risky_root,
        )
    finally:
        conn.close()
    console.print(
        f"Discovered {summary.discovered}, indexed {summary.indexed}, "
        f"skipped unchanged {summary.skipped_unchanged}, failures {summary.failed}."
    )


def _advanced_backend_enabled(name: str, config) -> bool:
    if name == "tesseract":
        return config.ocr.backend == "tesseract" and config.ocr.enabled
    if name == "easyocr":
        return bool(config.ocr.easyocr.enabled)
    if name == "paddle":
        return bool(config.ocr.paddle.enabled)
    return False


def _display_ocr_backend_name(name: str) -> str:
    if name == "easyocr":
        return "EasyOCR"
    if name == "paddle":
        return "PaddleOCR"
    return name
