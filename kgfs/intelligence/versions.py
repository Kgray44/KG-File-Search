"""Likely file-version detection for indexed KGFS files."""

from __future__ import annotations

import re
import sqlite3
from difflib import SequenceMatcher
from pathlib import Path

from kgfs.core.config import KGFSConfig
from kgfs.db.latest_results import get_latest_result_record
from kgfs.intelligence.models import VersionCandidate
from kgfs.search.similar import semantic_file_similarity, text_similarity

VERSION_TERMS = {"v1", "v2", "v3", "v4", "draft", "revised", "final", "final2", "copy"}


def find_versions_for_result(conn: sqlite3.Connection, result_id: int, config: KGFSConfig) -> list[VersionCandidate]:
    latest = get_latest_result_record(conn, result_id)
    if latest is None:
        raise ValueError(f"No latest search result found for ID {result_id}. Run kgfs search first.")
    return find_versions_for_file_id(conn, latest.file_id, config)


def find_versions_for_path(conn: sqlite3.Connection, path: Path, config: KGFSConfig) -> list[VersionCandidate]:
    resolved = path.expanduser()
    row = conn.execute("SELECT id FROM files WHERE path = ? OR normalized_path = ?", (str(resolved), str(resolved))).fetchone()
    if row is None:
        for candidate in conn.execute("SELECT id, path FROM files").fetchall():
            if Path(candidate["path"]) == resolved:
                row = candidate
                break
    if row is None:
        raise ValueError(f"File is not indexed: {path}")
    return find_versions_for_file_id(conn, int(row["id"]), config)


def find_versions_for_file_id(conn: sqlite3.Connection, file_id: int, config: KGFSConfig) -> list[VersionCandidate]:
    source = _file_row(conn, file_id)
    candidates: list[VersionCandidate] = []
    for row in conn.execute(
        """
        SELECT id, file_name, path, normalized_path, extension, size, modified_time, extracted_text
        FROM files
        WHERE id != ?
        """,
        (file_id,),
    ).fetchall():
        score, evidence = _version_score(conn, source, row, config)
        if score < config.intelligence.version_min_similarity:
            continue
        relationship = "newer" if float(row["modified_time"]) > float(source["modified_time"]) else "older"
        if abs(float(row["modified_time"]) - float(source["modified_time"])) < 1:
            relationship = "same-time"
        candidates.append(
            VersionCandidate(
                file_id=int(row["id"]),
                file_name=row["file_name"],
                path=Path(row["path"]),
                modified_time=float(row["modified_time"]),
                score=score,
                relationship=relationship,
                evidence=evidence,
            )
        )
    candidates.sort(key=lambda candidate: (-candidate.score, candidate.modified_time))
    return candidates


def _file_row(conn: sqlite3.Connection, file_id: int):
    row = conn.execute(
        """
        SELECT id, file_name, path, normalized_path, extension, size, modified_time, extracted_text
        FROM files
        WHERE id = ?
        """,
        (file_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"File record {file_id} no longer exists in the KGFS index.")
    return row


def _version_score(conn: sqlite3.Connection, source, candidate, config: KGFSConfig) -> tuple[float, list[str]]:
    source_stem = _clean_stem(source["file_name"])
    candidate_stem = _clean_stem(candidate["file_name"])
    name_similarity = SequenceMatcher(None, source_stem, candidate_stem).ratio()
    text_score = text_similarity(source["extracted_text"] or "", candidate["extracted_text"] or "")
    same_folder = Path(source["path"]).parent == Path(candidate["path"]).parent
    same_ext = source["extension"] == candidate["extension"]
    size_score = _size_similarity(int(source["size"]), int(candidate["size"]))
    semantic_score = semantic_file_similarity(
        conn,
        int(source["id"]),
        int(candidate["id"]),
        config.semantic.model_name,
    )
    semantic_component = semantic_score if semantic_score is not None else 0.0
    score = (
        name_similarity * 0.38
        + text_score * 0.25
        + size_score * 0.12
        + (0.12 if same_folder else 0.0)
        + (0.05 if same_ext else 0.0)
        + semantic_component * 0.08
    )
    evidence = [
        f"filename similarity {name_similarity:.2f}",
        f"text overlap {text_score:.2f}",
    ]
    if same_folder:
        evidence.append("same folder")
    if _has_version_marker(source["file_name"]) or _has_version_marker(candidate["file_name"]):
        evidence.append("version-like filename marker")
        score += 0.08
    if semantic_score is not None:
        evidence.append(f"semantic similarity {semantic_score:.2f}")
    return min(score, 1.0), evidence


def _clean_stem(file_name: str) -> str:
    stem = Path(file_name).stem.casefold()
    parts = [part for part in re.split(r"[\W_]+", stem) if part and part not in VERSION_TERMS]
    return " ".join(parts)


def _has_version_marker(file_name: str) -> bool:
    parts = set(re.split(r"[\W_]+", Path(file_name).stem.casefold()))
    return bool(parts & VERSION_TERMS) or bool(re.search(r"\bv\d+\b", Path(file_name).stem.casefold()))


def _size_similarity(left: int, right: int) -> float:
    if left <= 0 or right <= 0:
        return 0.0
    return min(left, right) / max(left, right)
