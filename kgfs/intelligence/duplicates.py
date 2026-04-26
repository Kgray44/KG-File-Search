"""Duplicate detection for indexed KGFS files."""

from __future__ import annotations

import sqlite3
import struct
from pathlib import Path

from kgfs.core.config import KGFSConfig
from kgfs.intelligence.models import DuplicateGroup, DuplicateItem, DuplicateReport
from kgfs.search.semantic import cosine_similarity, unpack_vector
from kgfs.search.snippets import make_snippet


def find_exact_duplicates(conn: sqlite3.Connection) -> DuplicateReport:
    """Group exact duplicate indexed files by content hash.

    This is read-only analysis. It never deletes, moves, or edits source files.
    """

    rows = conn.execute(
        """
        SELECT content_hash, COUNT(*) AS count
        FROM files
        WHERE content_hash IS NOT NULL AND content_hash != ''
        GROUP BY content_hash
        HAVING COUNT(*) > 1
        ORDER BY count DESC, content_hash
        """
    ).fetchall()
    groups: list[DuplicateGroup] = []
    for group_id, row in enumerate(rows, start=1):
        items = [_duplicate_item(file_row) for file_row in _files_for_hash(conn, row["content_hash"])]
        reclaimable = max(0, sum(item.size for item in items) - max((item.size for item in items), default=0))
        groups.append(
            DuplicateGroup(
                group_id=group_id,
                kind="exact",
                items=items,
                score=1.0,
                evidence=[f"same content hash {row['content_hash']}"],
                reclaimable_size=reclaimable,
            )
        )
    missing_hashes = conn.execute(
        "SELECT COUNT(*) AS count FROM files WHERE content_hash IS NULL OR content_hash = ''"
    ).fetchone()["count"]
    warnings = []
    if missing_hashes:
        warnings.append("Some files do not have hashes; run kgfs index --verify-hashes for stronger duplicate checks.")
    return DuplicateReport(groups=groups, warnings=warnings)


def find_semantic_duplicates(
    conn: sqlite3.Connection,
    config: KGFSConfig,
    *,
    min_score: float | None = None,
) -> DuplicateReport:
    """Find near-duplicate files using existing local semantic chunk vectors."""

    threshold = min_score if min_score is not None else config.intelligence.duplicate_min_semantic_score
    vectors = _file_vectors(conn, config.semantic.model_name)
    if len(vectors) < 2:
        return DuplicateReport(
            groups=[],
            warnings=["Semantic duplicate detection needs existing semantic vectors. Run kgfs vector rebuild first."],
        )

    parent: dict[int, int] = {file_id: file_id for file_id in vectors}
    evidence: dict[tuple[int, int], float] = {}
    file_ids = sorted(vectors)
    for index, left_id in enumerate(file_ids):
        for right_id in file_ids[index + 1 :]:
            score = cosine_similarity(vectors[left_id], vectors[right_id])
            if score >= threshold:
                _union(parent, left_id, right_id)
                evidence[(left_id, right_id)] = score

    grouped: dict[int, set[int]] = {}
    for file_id in file_ids:
        root = _find(parent, file_id)
        grouped.setdefault(root, set()).add(file_id)

    groups: list[DuplicateGroup] = []
    for file_set in grouped.values():
        if len(file_set) < 2:
            continue
        group_pairs = [
            score for (left_id, right_id), score in evidence.items() if left_id in file_set and right_id in file_set
        ]
        rows = _files_by_ids(conn, sorted(file_set))
        items = [_duplicate_item(row, query=" ".join(_shared_name_terms(rows))) for row in rows]
        groups.append(
            DuplicateGroup(
                group_id=len(groups) + 1,
                kind="semantic",
                items=items,
                score=max(group_pairs) if group_pairs else threshold,
                evidence=["similar semantic chunk vectors"],
                reclaimable_size=0,
            )
        )
    groups.sort(key=lambda group: group.score, reverse=True)
    return DuplicateReport(groups=groups, warnings=[])


def _duplicate_item(row, *, query: str = "") -> DuplicateItem:
    text = row["extracted_text"] if "extracted_text" in row.keys() else ""
    return DuplicateItem(
        file_id=int(row["id"]),
        file_name=row["file_name"],
        path=Path(row["path"]),
        size=int(row["size"]),
        modified_time=float(row["modified_time"]),
        content_hash=row["content_hash"],
        snippet=make_snippet(text or "", query or row["file_name"], highlight=False),
    )


def _files_for_hash(conn: sqlite3.Connection, content_hash: str) -> list:
    return conn.execute(
        """
        SELECT id, file_name, path, size, modified_time, content_hash, extracted_text
        FROM files
        WHERE content_hash = ?
        ORDER BY path
        """,
        (content_hash,),
    ).fetchall()


def _files_by_ids(conn: sqlite3.Connection, file_ids: list[int]) -> list:
    if not file_ids:
        return []
    placeholders = ",".join("?" for _ in file_ids)
    return conn.execute(
        f"""
        SELECT id, file_name, path, size, modified_time, content_hash, extracted_text
        FROM files
        WHERE id IN ({placeholders})
        ORDER BY path
        """,
        file_ids,
    ).fetchall()


def _file_vectors(conn: sqlite3.Connection, model_name: str) -> dict[int, list[float]]:
    rows = conn.execute(
        """
        SELECT file_id, embedding, embedding_dim
        FROM chunks
        WHERE model_name = ?
        ORDER BY file_id, chunk_index
        """,
        (model_name,),
    ).fetchall()
    by_file: dict[int, list[list[float]]] = {}
    for row in rows:
        try:
            vector = unpack_vector(row["embedding"], int(row["embedding_dim"]))
        except (struct.error, ValueError):
            continue
        if vector:
            by_file.setdefault(int(row["file_id"]), []).append(vector)
    averaged: dict[int, list[float]] = {}
    for file_id, vectors in by_file.items():
        dimension = len(vectors[0])
        if dimension == 0:
            continue
        averaged[file_id] = [sum(vector[index] for vector in vectors) / len(vectors) for index in range(dimension)]
    return averaged


def _shared_name_terms(rows: list) -> list[str]:
    if not rows:
        return []
    term_sets = [set(str(row["file_name"]).casefold().replace(".", " ").split()) for row in rows]
    shared = set.intersection(*term_sets) if term_sets else set()
    return sorted(shared)


def _find(parent: dict[int, int], value: int) -> int:
    while parent[value] != value:
        parent[value] = parent[parent[value]]
        value = parent[value]
    return value


def _union(parent: dict[int, int], left: int, right: int) -> None:
    left_root = _find(parent, left)
    right_root = _find(parent, right)
    if left_root != right_root:
        parent[right_root] = left_root
