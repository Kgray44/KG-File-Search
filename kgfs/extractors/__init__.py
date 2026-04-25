"""Text extraction dispatch."""

from __future__ import annotations

from pathlib import Path

from kgfs.extractors.base import ExtractionResult, skipped
from kgfs.extractors.code import extract_code
from kgfs.extractors.csv import extract_csv
from kgfs.extractors.docx import extract_docx
from kgfs.extractors.markdown import extract_markdown
from kgfs.extractors.pdf import extract_pdf
from kgfs.extractors.text import extract_plain_text

TEXT_EXTENSIONS = {".txt", ".html", ".css", ".json"}
CODE_EXTENSIONS = {".py", ".js", ".ts"}


def extract_text(path: Path, *, pdf_max_pages: int = 250) -> ExtractionResult:
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return extract_plain_text(path)
    if suffix == ".md":
        return extract_markdown(path)
    if suffix in CODE_EXTENSIONS:
        return extract_code(path)
    if suffix == ".csv":
        return extract_csv(path)
    if suffix == ".pdf":
        return extract_pdf(path, max_pages=pdf_max_pages)
    if suffix == ".docx":
        return extract_docx(path)
    return skipped(f"Unsupported extension: {suffix}")

