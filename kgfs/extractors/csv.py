"""CSV extraction."""

from __future__ import annotations

import csv
from pathlib import Path

from kgfs.extractors.base import ExtractionResult, failed, ok


def extract_csv(path: Path) -> ExtractionResult:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = csv.reader(handle)
            text = "\n".join(" ".join(cell.strip() for cell in row if cell.strip()) for row in rows)
        return ok(text)
    except UnicodeDecodeError:
        try:
            return ok(path.read_text(encoding="latin-1"))
        except OSError as exc:
            return failed(str(exc))
    except (OSError, csv.Error) as exc:
        return failed(str(exc))

