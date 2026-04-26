"""Local KGFS health dashboard command."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import connect_runtime, console, format_bytes
from kgfs.intelligence.health import build_health_report


def register(app: typer.Typer) -> None:
    app.command("health", help="Show a read-only KGFS health dashboard.")(health_cmd)


def health_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    json_output: bool = typer.Option(False, "--json", help="Print structured JSON."),
    fix_suggestions: bool = typer.Option(False, "--fix-suggestions", help="Show suggested maintenance commands."),
) -> None:
    _, _, resolved_database_path, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        report = build_health_report(conn, config, database_path=resolved_database_path)
        if json_output:
            console.print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
            return
        summary = Table(title="KGFS Health")
        summary.add_column("Metric")
        summary.add_column("Value")
        for key, value in report.summary.items():
            display = format_bytes(value) if key.endswith("size") and isinstance(value, int) else str(value)
            summary.add_row(key, display)
        console.print(summary)
        workflow = Table(title="Workflow Metadata")
        workflow.add_column("Type")
        workflow.add_column("Count", justify="right")
        for key, value in report.workflow_counts.items():
            workflow.add_row(key, str(value))
        console.print(workflow)
        issues = Table(title="Issues")
        issues.add_column("Severity")
        issues.add_column("Title")
        issues.add_column("Detail")
        issues.add_column("Suggestion")
        for issue in report.issues:
            issues.add_row(issue.severity, issue.title, issue.detail, issue.suggestion or "")
        console.print(issues)
        if fix_suggestions:
            console.print("[bold]Suggested Commands[/bold]")
            for suggestion in report.suggestions:
                console.print(f"- {suggestion}")
    finally:
        conn.close()
