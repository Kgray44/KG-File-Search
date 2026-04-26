"""Read-only local health reporting for KGFS."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from kgfs.core.config import KGFSConfig
from kgfs.db.stats import get_database_stats
from kgfs.intelligence.duplicates import find_exact_duplicates
from kgfs.intelligence.models import HealthIssue, HealthReport
from kgfs.models.registry import collect_model_statuses


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
    model_statuses = collect_model_statuses(config)
    model_ready = [f"{item.kind}:{item.name}" for item in model_statuses if item.available]
    model_downloads_enabled = [f"{item.kind}:{item.name}" for item in model_statuses if item.download_enabled]
    model_unavailable_enabled = [
        f"{item.kind}:{item.name}" for item in model_statuses if item.enabled and not item.available
    ]
    summary = {
        "indexed_files": stats["total_files"],
        "stale_records": stats["stale_records"],
        "extraction_failures": stats["extraction_failures"],
        "ocr_failures": stats["ocr_failures"],
        "semantic_chunks": stats["total_chunks"],
        "duplicate_groups": len(duplicate_report.groups),
        "project_candidates": project_candidates,
        "media_metadata": stats["media_metadata_count"],
        "media_text": stats["media_text_count"],
        "media_embeddings": stats["media_embedding_count"],
        "media_enabled": bool(config.media.enabled),
        "database_size": stats["database_size"],
        "schema_version": stats["schema_version"],
        "ai_enabled": bool(config.ai.enabled),
        "model_backends_ready": model_ready,
        "model_downloads_enabled": model_downloads_enabled,
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
    if config.media.enabled and config.media.photos.store_location_metadata:
        issues.append(
            HealthIssue(
                severity="warning",
                title="Photo location metadata enabled",
                detail=f"Photo location metadata storage is configured as {config.media.photos.location_precision}.",
                suggestion="Review media.photos.store_location_metadata in config.yaml",
            )
        )
    if config.ocr.cloud_fallback.enabled:
        issues.append(
            HealthIssue(
                severity="warning",
                title="Cloud OCR fallback configured",
                detail="Cloud OCR remains scaffolded and requires explicit confirmation; verify privacy settings before use.",
                suggestion="kgfs ocr advanced-status",
            )
        )
    if model_unavailable_enabled:
        issues.append(
            HealthIssue(
                severity="warning",
                title="Configured local model backend unavailable",
                detail=", ".join(model_unavailable_enabled),
                suggestion="kgfs models status",
            )
        )
        suggestions.append("kgfs models status")
    if model_downloads_enabled:
        issues.append(
            HealthIssue(
                severity="warning",
                title="Model downloads enabled",
                detail="KGFS defaults to local files only; review these explicit download opt-ins: "
                + ", ".join(model_downloads_enabled),
                suggestion="kgfs models status",
            )
        )
    return HealthReport(
        summary=summary, issues=issues, workflow_counts=workflow_counts, suggestions=_unique(suggestions)
    )


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
