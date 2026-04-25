"""Search filter models and row matching."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class SearchFilters:
    extensions: list[str] | None = None
    file_type: str | None = None
    folder: str | None = None
    after: str | None = None
    before: str | None = None
    failed_only: bool = False

    def normalized_extensions(self) -> list[str]:
        values = list(self.extensions or [])
        if self.file_type:
            values.append(self.file_type)
        normalized: list[str] = []
        for value in values:
            text = str(value).strip().lower()
            if text and not text.startswith("."):
                text = f".{text}"
            if text:
                normalized.append(text)
        return normalized


def row_matches_filters(row, filters: SearchFilters | None) -> bool:
    if filters is None:
        return True
    extensions = filters.normalized_extensions()
    if extensions and str(row["extension"]).lower() not in extensions:
        return False
    if filters.folder:
        needle = normalize_path_text(filters.folder)
        path_text = normalize_path_text(row["path"])
        if needle not in path_text:
            return False
    if filters.after and float(row["modified_time"]) < date_timestamp(filters.after, end_of_day=False):
        return False
    if filters.before and float(row["modified_time"]) > date_timestamp(filters.before, end_of_day=True):
        return False
    if filters.failed_only and row["extraction_status"] != "error":
        return False
    return True


def date_timestamp(value: str, *, end_of_day: bool) -> float:
    parsed = datetime.fromisoformat(value)
    if end_of_day:
        parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
    return parsed.timestamp()


def normalize_path_text(value: str | Path) -> str:
    return str(value).replace("\\", "/").casefold()
