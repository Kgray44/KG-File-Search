"""Metadata helpers for optional vector backend artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from sqlite3 import Connection
from typing import Any

from kgfs.core.config import KGFSConfig
from kgfs.db.migrations import get_schema_version
from kgfs.vectors.storage import backend_metadata_path

METADATA_FORMAT_VERSION = 1


@dataclass(frozen=True)
class VectorBackendMetadata:
    backend_name: str
    model_name: str
    embedding_dim: int
    chunk_count: int
    chunk_fingerprint: str
    backend_config_hash: str
    schema_version: int
    metadata_format_version: int = METADATA_FORMAT_VERSION
    artifact_files: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class BackendMetadataHealth:
    ready: bool
    status: str
    reasons: list[str] = field(default_factory=list)
    metadata: VectorBackendMetadata | None = None
    metadata_path: Path | None = None


def current_backend_metadata(
    conn: Connection,
    config: KGFSConfig,
    backend_name: str,
    model_name: str,
    *,
    artifact_files: list[str] | None = None,
) -> VectorBackendMetadata:
    chunk_count, embedding_dim, fingerprint = chunk_fingerprint(conn, model_name)
    now = datetime.now(timezone.utc).isoformat()
    existing = read_backend_metadata(config, backend_name, model_name)
    return VectorBackendMetadata(
        backend_name=backend_name,
        model_name=model_name,
        embedding_dim=embedding_dim,
        chunk_count=chunk_count,
        chunk_fingerprint=fingerprint,
        backend_config_hash=backend_config_hash(config, backend_name),
        schema_version=get_schema_version(conn),
        artifact_files=artifact_files or [],
        created_at=existing.created_at if existing else now,
        updated_at=now,
    )


def write_backend_metadata(config: KGFSConfig, metadata: VectorBackendMetadata) -> Path:
    path = backend_metadata_path(config, metadata.backend_name, model_name=metadata.model_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(metadata), indent=2, sort_keys=True), encoding="utf-8")
    return path


def read_backend_metadata(
    config: KGFSConfig,
    backend_name: str,
    model_name: str,
) -> VectorBackendMetadata | None:
    path = backend_metadata_path(config, backend_name, model_name=model_name)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return VectorBackendMetadata(
            backend_name=str(data["backend_name"]),
            model_name=str(data["model_name"]),
            embedding_dim=int(data["embedding_dim"]),
            chunk_count=int(data["chunk_count"]),
            chunk_fingerprint=str(data["chunk_fingerprint"]),
            backend_config_hash=str(data["backend_config_hash"]),
            schema_version=int(data["schema_version"]),
            metadata_format_version=int(data.get("metadata_format_version", 0)),
            artifact_files=[str(item) for item in data.get("artifact_files", [])],
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def backend_metadata_health(
    conn: Connection,
    config: KGFSConfig,
    backend_name: str,
    model_name: str,
    *,
    required_artifacts: list[Path] | None = None,
) -> BackendMetadataHealth:
    path = backend_metadata_path(config, backend_name, model_name=model_name)
    metadata = read_backend_metadata(config, backend_name, model_name)
    if metadata is None:
        return BackendMetadataHealth(False, "missing", ["Backend metadata is missing."], None, path)

    current = current_backend_metadata(
        conn,
        config,
        backend_name,
        model_name,
        artifact_files=metadata.artifact_files,
    )
    reasons: list[str] = []
    if metadata.metadata_format_version != METADATA_FORMAT_VERSION:
        reasons.append("metadata format version changed")
    if metadata.schema_version != current.schema_version:
        reasons.append("database schema version changed")
    if metadata.chunk_count != current.chunk_count:
        reasons.append("chunk count changed")
    if metadata.embedding_dim != current.embedding_dim:
        reasons.append("embedding dimension changed")
    if metadata.chunk_fingerprint != current.chunk_fingerprint:
        reasons.append("chunk fingerprint changed")
    if metadata.backend_config_hash != current.backend_config_hash:
        reasons.append("backend config changed")
    for artifact in required_artifacts or []:
        if not artifact.exists():
            reasons.append(f"artifact missing: {artifact.name}")

    if reasons:
        return BackendMetadataHealth(False, "stale", reasons, metadata, path)
    return BackendMetadataHealth(True, "ready", [], metadata, path)


def chunk_fingerprint(conn: Connection, model_name: str) -> tuple[int, int, str]:
    digest = hashlib.sha256()
    rows = conn.execute(
        """
        SELECT id, file_id, chunk_index, embedding, embedding_dim, start_char, end_char, created_at
        FROM chunks
        WHERE model_name = ?
        ORDER BY id
        """,
        (model_name,),
    ).fetchall()
    embedding_dim = 0
    for row in rows:
        embedding_dim = int(row["embedding_dim"])
        digest.update(str(row["id"]).encode("utf-8"))
        digest.update(b"|")
        digest.update(str(row["file_id"]).encode("utf-8"))
        digest.update(b"|")
        digest.update(str(row["chunk_index"]).encode("utf-8"))
        digest.update(b"|")
        digest.update(str(row["embedding_dim"]).encode("utf-8"))
        digest.update(b"|")
        digest.update(bytes(row["embedding"]))
        digest.update(b"|")
        digest.update(str(row["start_char"]).encode("utf-8"))
        digest.update(b"|")
        digest.update(str(row["end_char"]).encode("utf-8"))
        digest.update(b"|")
        digest.update(str(row["created_at"]).encode("utf-8"))
        digest.update(b"\n")
    return len(rows), embedding_dim, digest.hexdigest()


def backend_config_hash(config: KGFSConfig, backend_name: str) -> str:
    settings = getattr(config.vectors, backend_name, None)
    if settings is None:
        payload: dict[str, Any] = {"backend": backend_name}
    elif hasattr(settings, "model_dump"):
        payload = settings.model_dump(mode="json")
    else:
        payload = dict(settings)
    payload["backend"] = backend_name
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
