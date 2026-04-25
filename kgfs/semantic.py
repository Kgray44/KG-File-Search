"""Local semantic search helpers.

Embeddings are generated locally with sentence-transformers when semantic search
is enabled. KGFS stores vectors in SQLite BLOB columns; no cloud API is used.
"""

from __future__ import annotations

import math
import sqlite3
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from kgfs.config import SemanticSettings
from kgfs.models import TextChunk


class SemanticUnavailableError(RuntimeError):
    """Raised when semantic search is enabled but local embedding support is missing."""


class Embedder(Protocol):
    model_name: str

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""


@dataclass(frozen=True)
class SemanticStatus:
    enabled: bool
    available: bool
    message: str


class SentenceTransformerEmbedder:
    def __init__(self, settings: SemanticSettings) -> None:
        self.model_name = settings.model_name
        self._batch_size = settings.batch_size
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise SemanticUnavailableError(
                "sentence-transformers is not installed. Install with: python -m pip install -e \".[semantic]\""
            ) from exc

        try:
            self._model = SentenceTransformer(
                settings.model_name,
                local_files_only=settings.local_files_only,
            )
        except TypeError as exc:
            raise SemanticUnavailableError(
                "This sentence-transformers version does not support local_files_only. "
                "Upgrade sentence-transformers or use a local model path."
            ) from exc

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = self._model.encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [[float(value) for value in row] for row in embeddings]


def get_semantic_status(settings_or_enabled: SemanticSettings | bool) -> SemanticStatus:
    if isinstance(settings_or_enabled, bool):
        enabled = settings_or_enabled
        settings = SemanticSettings(enabled=enabled)
    else:
        settings = settings_or_enabled
        enabled = settings.enabled

    if not enabled:
        return SemanticStatus(
            enabled=False,
            available=False,
            message="Semantic search is disabled. Enable it in config.yaml after installing kg-file-search[semantic].",
        )
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        return SemanticStatus(
            enabled=True,
            available=False,
            message="Install semantic dependencies with: python -m pip install -e \".[semantic]\"",
        )
    local_only = "local files only" if settings.local_files_only else "model download allowed by sentence-transformers"
    return SemanticStatus(
        enabled=True,
        available=True,
        message=f"Semantic dependencies are available ({settings.model_name}, {local_only}).",
    )


def get_embedder(settings: SemanticSettings, embedder: Embedder | None = None) -> Embedder:
    return embedder if embedder is not None else SentenceTransformerEmbedder(settings)


def semantic_model_name(settings: SemanticSettings, embedder: Embedder | None = None) -> str:
    return getattr(embedder, "model_name", settings.model_name)


def chunk_text(text: str, *, chunk_size_chars: int, chunk_overlap_chars: int) -> list[TextChunk]:
    if not text:
        return []

    chunk_size = max(1, chunk_size_chars)
    overlap = max(0, min(chunk_overlap_chars, chunk_size - 1))
    chunks: list[TextChunk] = []
    start = 0

    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(
                TextChunk(
                    chunk_index=len(chunks),
                    text=chunk,
                    start_char=start,
                    end_char=end,
                )
            )
        if end >= len(text):
            break
        start = end - overlap

    return chunks


def vector_to_blob(vector: list[float]) -> bytes:
    if not vector:
        return b""
    return struct.pack(f"<{len(vector)}f", *[float(value) for value in vector])


def unpack_vector(blob: bytes, dimension: int) -> list[float]:
    if dimension <= 0:
        return []
    return list(struct.unpack(f"<{dimension}f", blob))


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def replace_file_chunks(
    conn: sqlite3.Connection,
    *,
    file_id: int,
    chunks: list[TextChunk],
    embeddings: list[list[float]],
    model_name: str,
) -> int:
    conn.execute("DELETE FROM chunks WHERE file_id = ? AND model_name = ?", (file_id, model_name))
    created_at = datetime.now(timezone.utc).isoformat()
    rows = []
    for chunk, embedding in zip(chunks, embeddings):
        rows.append(
            (
                file_id,
                chunk.chunk_index,
                chunk.text,
                vector_to_blob(embedding),
                len(embedding),
                chunk.start_char,
                chunk.end_char,
                model_name,
                created_at,
            )
        )
    conn.executemany(
        """
        INSERT INTO chunks(
            file_id, chunk_index, text, embedding, embedding_dim,
            start_char, end_char, model_name, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)
