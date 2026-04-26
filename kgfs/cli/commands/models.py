"""Local model backend status and recommendation commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.markup import escape
from rich.table import Table

from kgfs.cli.shared import console, optional_config_runtime
from kgfs.models.benchmark import benchmark_models
from kgfs.models.doctor import build_model_doctor_report
from kgfs.models.paths import collect_model_paths, default_model_cache_dir
from kgfs.models.recommend import recommend_models
from kgfs.models.registry import collect_model_statuses, list_model_backends
from kgfs.models.snippets import config_snippet
from kgfs.models.testing import test_backend
from kgfs.models.validation import validate_all_backends, validate_backend

models_app = typer.Typer(help="Inspect optional local OCR/media model backends.")


def register(app: typer.Typer) -> None:
    app.add_typer(models_app, name="models")


@models_app.command("status")
def status_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Show local model backend status without running model inference."""

    _, _, _, config = optional_config_runtime(config_path, database_path, project_local)
    table = Table(title="KGFS Local Model Status")
    table.add_column("Kind")
    table.add_column("Backend")
    table.add_column("Enabled")
    table.add_column("Available")
    table.add_column("Readiness")
    table.add_column("Model path")
    table.add_column("Downloads")
    statuses = collect_model_statuses(config)
    for status in statuses:
        table.add_row(
            status.kind,
            _display_name(status.name),
            str(status.enabled),
            str(status.available),
            status.readiness,
            str(status.model_path or ""),
            "enabled" if status.download_enabled else "downloads disabled",
        )
    console.print(table)
    console.print("[bold]Notes[/bold]")
    for status in statuses:
        label = f"{status.kind}:{_display_name(status.name)}"
        suffix = f" Install hint: {status.install_hint}" if status.install_hint else ""
        console.print(f"- {escape(label)}: {escape(status.message + suffix)}")
    console.print(
        "Known backends: Tesseract, EasyOCR, PaddleOCR, metadata-caption, "
        "transformers-caption, faster-whisper, bytehash-visual, clip-visual"
    )
    console.print("Readiness summary: " + ", ".join(f"{status.name}={status.readiness}" for status in statuses))
    console.print("Model downloads disabled by default unless a backend config explicitly enables them.")


@models_app.command("list")
def list_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """List known KGFS local model backend names."""

    optional_config_runtime(config_path, database_path, project_local)
    table = Table(title="KGFS Local Model Backends")
    table.add_column("Kind")
    table.add_column("Backend")
    table.add_column("Config")
    table.add_column("Install hint")
    for item in list_model_backends():
        table.add_row(item.kind, item.name, item.config_key, item.install_hint or "")
    console.print(table)


@models_app.command("benchmark")
def benchmark_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Run a bounded availability benchmark for local model backends."""

    _, _, _, config = optional_config_runtime(config_path, database_path, project_local)
    table = Table(title="KGFS Model Benchmark")
    table.add_column("Kind")
    table.add_column("Backend")
    table.add_column("Available")
    table.add_column("Elapsed")
    table.add_column("Notes")
    for row in benchmark_models(config):
        elapsed = "" if row.elapsed_ms is None else f"{row.elapsed_ms:.3f} ms"
        table.add_row(row.kind, row.name, str(row.available), elapsed, row.notes)
    console.print(table)


@models_app.command("doctor")
def doctor_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Inspect local model readiness, paths, and privacy guardrails."""

    _, _, _, config = optional_config_runtime(config_path, database_path, project_local)
    report = build_model_doctor_report(config)
    _print_validation_table("KGFS Model Doctor", report.validations)
    console.print(
        "Readiness states: disabled, ready, missing_dependency, missing_model, configuration_needed, scaffold, error"
    )
    if report.warnings:
        for warning in report.warnings:
            console.print(f"[yellow]Warning[/yellow]: {warning}")
    else:
        console.print("No model path warnings.")


@models_app.command("paths")
def paths_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Show KGFS model cache and configured local model paths without creating them."""

    _, _, _, config = optional_config_runtime(config_path, database_path, project_local)
    table = Table(title="KGFS Model Paths")
    table.add_column("Backend")
    table.add_column("Label")
    table.add_column("Path")
    table.add_column("Configured")
    table.add_column("Exists")
    table.add_column("Readable")
    table.add_column("Warnings")
    for item in collect_model_paths(config):
        table.add_row(
            item.backend,
            item.label,
            str(item.path or ""),
            str(item.configured),
            str(item.exists),
            str(item.readable),
            "; ".join(item.warnings),
        )
    console.print(f"KGFS model cache: {default_model_cache_dir(config)}")
    console.print(table)


@models_app.command("validate")
def validate_cmd(
    backend: str | None = typer.Argument(None, help="Optional backend name or alias to validate."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Validate dependency, model path, and no-download readiness for local model backends."""

    _, _, _, config = optional_config_runtime(config_path, database_path, project_local)
    rows = [validate_backend(backend, config)] if backend else validate_all_backends(config)
    _print_validation_table("KGFS Model Validation", rows)
    console.print("Readiness summary: " + ", ".join(row.readiness.value for row in rows))


@models_app.command("config-snippet")
def config_snippet_cmd(
    backend: str = typer.Argument(..., help="Backend name, for example easyocr or faster-whisper."),
) -> None:
    """Print a YAML snippet for a local model backend without modifying config."""

    try:
        console.print(config_snippet(backend), end="")
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


@models_app.command("test")
def test_cmd(
    backend: str = typer.Argument(..., help="Backend name or alias to test."),
    path: Path = typer.Argument(..., help="Local file to test without indexing."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Run one tiny local backend operation without indexing or modifying the file."""

    _, _, _, config = optional_config_runtime(config_path, database_path, project_local)
    target = path.expanduser()
    if not target.exists():
        raise typer.BadParameter(f"Path does not exist: {target}")
    try:
        result = test_backend(backend, target, config)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print(f"Backend: [bold]{result.backend}[/bold]")
    console.print(f"Status: [bold]{result.status}[/bold]")
    if result.detail:
        console.print(result.detail)
    if result.output:
        console.print(result.output[:2000])


@models_app.command("recommend")
def recommend_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Recommend local model backend setup from current config."""

    _, _, _, config = optional_config_runtime(config_path, database_path, project_local)
    recommendation = recommend_models(config)
    console.print(f"[bold]Recommended[/bold]: {recommendation.recommended}")
    for reason in recommendation.reasons:
        console.print(f"- {reason}")
    for warning in recommendation.warnings:
        console.print(f"[yellow]Warning[/yellow]: {warning}")


def _display_name(name: str) -> str:
    labels = {"easyocr": "EasyOCR", "paddle": "PaddleOCR", "faster_whisper": "faster-whisper"}
    return labels.get(name, name)


def _print_validation_table(title: str, rows) -> None:
    table = Table(title=title)
    table.add_column("Backend")
    table.add_column("Kind")
    table.add_column("Enabled")
    table.add_column("Dependency")
    table.add_column("Readiness")
    table.add_column("Model path")
    table.add_column("Downloads")
    for row in rows:
        table.add_row(
            row.backend,
            row.kind,
            str(row.enabled),
            "available" if row.dependency_available else "missing",
            row.readiness.value,
            str(row.model_path or ""),
            "enabled" if row.download_enabled else "downloads disabled",
        )
    console.print(table)
    console.print("[bold]Notes[/bold]")
    for row in rows:
        messages = "; ".join([*row.messages, *row.warnings])
        if messages:
            console.print(f"- {escape(row.backend)}: {escape(messages)}")
