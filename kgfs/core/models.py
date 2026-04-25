"""Shared dataclasses used by KGFS modules."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileRecord:
    path: Path
    normalized_path: str
    file_name: str
    extension: str
    size: int
    modified_time: float
    content_hash: str | None
    extracted_text: str
    indexed_at: str
    platform_indexed_from: str
    extraction_status: str
    extraction_error: str | None
    modified_time_ns: int | None = None


@dataclass(frozen=True)
class IndexSummary:
    discovered: int = 0
    indexed: int = 0
    skipped_unchanged: int = 0
    failed: int = 0
    bytes_indexed: int = 0
    dry_run: bool = False


@dataclass(frozen=True)
class SearchResult:
    result_id: int
    file_id: int
    file_name: str
    path: Path
    extension: str
    modified_time: float
    score: float
    snippet: str


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    text: str
    start_char: int
    end_char: int
