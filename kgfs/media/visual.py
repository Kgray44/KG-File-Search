"""Optional local visual embedding backend contract and helpers."""

from __future__ import annotations

import hashlib
import math
import sqlite3
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Protocol

from kgfs.core.config import KGFSConfig
from kgfs.core.models import SearchResult
from kgfs.media.cache import decode_media_embedding, store_media_embedding


@dataclass(frozen=True)
class VisualStatus:
    enabled: bool
    backend: str
    available: bool
    message: str
    install_hint: str | None = None


@dataclass(frozen=True)
class VisualEmbeddingResult:
    vector: list[float]
    status: str
    error: str | None = None
    backend: str = "none"
    model_name: str | None = None


class VisualEmbeddingBackend(Protocol):
    name: str

    def available(self, config: KGFSConfig) -> tuple[bool, str] | VisualStatus: ...

    def embed(self, path: Path, config: KGFSConfig) -> VisualEmbeddingResult: ...


class NoneVisualBackend:
    name = "none"

    def available(self, config: KGFSConfig) -> tuple[bool, str]:
        return False, "No local visual embedding backend is configured."

    def embed(self, path: Path, config: KGFSConfig) -> VisualEmbeddingResult:
        return VisualEmbeddingResult(
            [], "skipped", "No local visual embedding backend is configured.", backend=self.name
        )


class ByteHashVisualBackend:
    """A deterministic local test/dev embedding based on file bytes, not visual understanding."""

    name = "bytehash"

    def available(self, config: KGFSConfig) -> tuple[bool, str]:
        return True, "Byte-hash visual embedding backend is available for deterministic local testing."

    def embed(self, path: Path, config: KGFSConfig) -> VisualEmbeddingResult:
        digest = hashlib.sha256(path.read_bytes()).digest()
        vector = [byte / 255.0 for byte in digest[:16]]
        return VisualEmbeddingResult(vector, "ok", backend=self.name, model_name="bytehash-v1")


class ClipVisualBackend:
    name = "clip"

    def available(self, config: KGFSConfig) -> tuple[bool, str]:
        if find_spec("sentence_transformers") is None or find_spec("PIL") is None:
            return False, 'Install with python -m pip install -e ".[visual]".'
        if config.media.visual.local_files_only and not config.media.visual.model_name:
            return False, "Set media.visual.model_name to a local model path/name; downloads are disabled by default."
        return True, "CLIP-compatible visual backend is available."

    def embed(self, path: Path, config: KGFSConfig) -> VisualEmbeddingResult:
        ok, message = self.available(config)
        if not ok:
            return VisualEmbeddingResult(
                [], "skipped", message, backend=self.name, model_name=config.media.visual.model_name
            )
        try:
            from PIL import Image
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(
                config.media.visual.model_name, local_files_only=config.media.visual.local_files_only
            )
            image = Image.open(path)
            vector = model.encode(image)
            values = [float(item) for item in vector.tolist() if isinstance(item, int | float)]
        except Exception as exc:  # pragma: no cover - optional model behavior varies
            return VisualEmbeddingResult([], "error", f"Visual embedding failed: {exc}", backend=self.name)
        return VisualEmbeddingResult(values, "ok", backend=self.name, model_name=config.media.visual.model_name)


_VISUAL_BACKENDS: dict[str, VisualEmbeddingBackend] = {
    "none": NoneVisualBackend(),
    "bytehash": ByteHashVisualBackend(),
    "clip": ClipVisualBackend(),
}


def register_visual_backend(name: str, backend: VisualEmbeddingBackend) -> None:
    _VISUAL_BACKENDS[name.strip().lower()] = backend


def get_visual_backend(name: str) -> VisualEmbeddingBackend:
    key = (name or "none").strip().lower()
    if key not in _VISUAL_BACKENDS:
        raise ValueError(f"Unknown visual backend '{name}'. Known backends: {', '.join(sorted(_VISUAL_BACKENDS))}.")
    return _VISUAL_BACKENDS[key]


def list_visual_backends() -> list[str]:
    return sorted(_VISUAL_BACKENDS)


def get_visual_status(config: KGFSConfig) -> VisualStatus:
    backend_name = config.media.visual.backend
    if not config.media.visual.enabled:
        return VisualStatus(False, backend_name, False, "Visual semantic search is disabled.")
    try:
        backend = get_visual_backend(backend_name)
    except ValueError as exc:
        return VisualStatus(True, backend_name, False, str(exc))
    available, message = _availability(backend.available(config))
    return VisualStatus(
        True, backend_name, available, message, None if available else _visual_install_hint(backend_name)
    )


def visual_embedding_for_file(path: Path, config: KGFSConfig) -> VisualEmbeddingResult:
    status = get_visual_status(config)
    if not status.available:
        return VisualEmbeddingResult([], "skipped", status.message, backend=status.backend)
    return get_visual_backend(status.backend).embed(path, config)


def index_existing_visual_embeddings(conn: sqlite3.Connection, config: KGFSConfig) -> tuple[int, int]:
    if not config.media.enabled or not config.media.visual.enabled:
        return 0, 0
    indexed = failed = 0
    rows = _iter_files(conn, set(config.media.photos.include_extensions))
    for row in rows:
        result = visual_embedding_for_file(Path(row["path"]), config)
        if result.status == "ok" and result.vector:
            store_media_embedding(
                conn,
                file_id=int(row["id"]),
                source_kind="image",
                backend=result.backend,
                model_name=result.model_name or config.media.visual.model_name or result.backend,
                vector=result.vector,
                metadata={"status": result.status},
            )
            indexed += 1
        elif result.status == "error":
            failed += 1
    return indexed, failed


def find_visual_similar(
    conn: sqlite3.Connection,
    source_file_id: int,
    config: KGFSConfig,
    *,
    limit: int = 10,
) -> list[SearchResult]:
    source = conn.execute(
        """
        SELECT * FROM media_embeddings
        WHERE file_id = ? AND source_kind = 'image'
        ORDER BY id DESC
        LIMIT 1
        """,
        (source_file_id,),
    ).fetchone()
    if source is None:
        return []
    source_vector = decode_media_embedding(source["embedding"])
    rows = conn.execute(
        """
        SELECT me.embedding, me.backend, me.model_name, f.*
        FROM media_embeddings me
        JOIN files f ON f.id = me.file_id
        WHERE me.source_kind = 'image' AND me.file_id != ?
        """,
        (source_file_id,),
    ).fetchall()
    ranked: list[SearchResult] = []
    for row in rows:
        score = _cosine(source_vector, decode_media_embedding(row["embedding"]))
        ranked.append(
            SearchResult(
                result_id=0,
                file_id=int(row["id"]),
                file_name=row["file_name"],
                path=Path(row["path"]),
                extension=row["extension"],
                modified_time=float(row["modified_time"]),
                score=score,
                snippet=f"Visual embedding similarity score {score:.3f}",
                normalized_path=row["normalized_path"],
                mode="visual",
                source="media:visual_embedding",
                metadata={
                    "extraction_source": "media:visual_embedding",
                    "media_backend": row["backend"],
                    "media_model_name": row["model_name"],
                },
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)
    return [
        SearchResult(
            result_id=index,
            file_id=result.file_id,
            file_name=result.file_name,
            path=result.path,
            extension=result.extension,
            modified_time=result.modified_time,
            score=result.score,
            snippet=result.snippet,
            normalized_path=result.normalized_path,
            mode=result.mode,
            source=result.source,
            metadata=result.metadata,
        )
        for index, result in enumerate(ranked[:limit], start=1)
    ]


def _iter_files(conn: sqlite3.Connection, extensions: set[str]) -> list[sqlite3.Row]:
    placeholders = ",".join("?" for _ in extensions)
    if not placeholders:
        return []
    return list(
        conn.execute(
            f"""
            SELECT id, path, extension
            FROM files
            WHERE lower(extension) IN ({placeholders})
            ORDER BY id
            """,
            tuple(sorted(extensions)),
        ).fetchall()
    )


def _availability(value: tuple[bool, str] | VisualStatus) -> tuple[bool, str]:
    if isinstance(value, VisualStatus):
        return value.available, value.message
    return bool(value[0]), str(value[1])


def _visual_install_hint(name: str) -> str | None:
    if name == "clip":
        return 'Install with python -m pip install -e ".[visual]".'
    return None


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
