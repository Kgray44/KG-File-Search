"""Read-only local health reporting for KGFS."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from kgfs.core.config import KGFSConfig
from kgfs.db.stats import get_database_stats
from kgfs.intelligence.duplicates import find_exact_duplicates
from kgfs.intelligence.models import HealthIssue, HealthReport


def build_health_report(
    conn: sqlite3.Connection,
    config: KGFSConfig,
    *,
    database_path: Path | None = None,
) -> HealthReport:
    stats = get_database_stats(conn, database_path)
    duplicate_report = find_exact_duplicates(conn)
    workflow_counts = _workflow_counts(conn)
    project_candidates = _count(conn, "project_candidates")
    summary = {
        "indexed_files": stats["total_files"],
        "stale_records": stats["stale_records"],
        "extraction_failures": stats["extraction_failures"],
        "ocr_failures": stats["ocr_failures"],
        "semantic_chunks": stats["total_chunks"],
        "duplicate_groups": len(duplicate_report.groups),
        "project_candidates": project_candidates,
        "database_size": stats["database_size"],
        "schema_version": stats["schema_version"],
        "ai_enabled": bool(config.ai.enabled),
    }
    issues: list[HealthIssue] = []
    suggestions: list[str] = ["kgfs metadata export --output kgfs-metadata-backup.json"]
    if stats["stale_records"]:
        issues.append(
            HealthIssue(
                severity="warning",
                title="Stale file records",
                detail=f"{stats['stale_records']} indexed paths no longer exist.",
                suggestion="kgfs prune --dry-run",
            )
        )
        suggestions.append("kgfs prune --dry-run")
    if stats["extraction_failures"]:
        issues.append(
            HealthIssue(
                severity="warning",
                title="Extraction failures",
                detail=f"{stats['extraction_failures']} files have extraction errors.",
                suggestion="kgfs stats",
            )
        )
    if duplicate_report.groups:
        issues.append(
            HealthIssue(
                severity="info",
                title="Exact duplicates found",
                detail=f"{len(duplicate_report.groups)} exact duplicate groups found.",
                suggestion="kgfs duplicates --exact",
            )
        )
        suggestions.append("kgfs duplicates --exact")
    if config.semantic.enabled and not stats["total_chunks"]:
        issues.append(
            HealthIssue(
                severity="warning",
                title="Semantic search enabled but no chunks",
                detail="Semantic search needs local chunks/vectors before it can help.",
                suggestion="kgfs vector rebuild",
            )
        )
        suggestions.append("kgfs vector rebuild")
    if config.ai.enabled:
        issues.append(
            HealthIssue(
                severity="info",
                title="AI Assist enabled",
                detail="AI remains opt-in per command; review privacy settings before use.",
                suggestion="kgfs config",
            )
        )
    return HealthReport(summary=summary, issues=issues, workflow_counts=workflow_counts, suggestions=_unique(suggestions))


def _workflow_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        "profiles": _count(conn, "profiles"),
        "saved_searches": _count(conn, "saved_searches"),
        "collections": _count(conn, "collections"),
        "tags": _count(conn, "tags"),
        "notes": _count(conn, "file_notes"),
        "projects": _count(conn, "projects"),
        "assignment_runs": _count(conn, "assignment_runs"),
    }


def _count(conn: sqlite3.Connection, table: str) -> int:
    try:
        return int(conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"])
    except sqlite3.Error:
        return 0


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
