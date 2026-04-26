"""Local KGFS citation formatting."""

from __future__ import annotations

from kgfs.core.models import SearchResult


def format_citation(result: SearchResult, *, include_paths: bool = False, include_score: bool = False) -> str:
    """Return a compact local citation for a KGFS search result."""

    label = f"[{result.result_id}] {result.file_name}"
    details: list[str] = []
    source = str(result.metadata.get("extraction_source", "") if result.metadata else "")
    if source.startswith("ocr"):
        kind = str(result.metadata.get("ocr_source_kind", "") if result.metadata else "")
        details.append("OCR PDF" if kind == "pdf" else "OCR")
    if result.matched_chunk_id is not None:
        details.append(f"chunk {result.matched_chunk_id}")
    if include_score:
        details.append(f"score {result.score:.3f}")
    if details:
        label = f"{label} ({', '.join(details)})"
    if include_paths:
        label = f"{label}\n    {result.path}"
    return label


def format_citation_block(
    results: list[SearchResult],
    *,
    include_paths: bool = False,
    include_scores: bool = False,
) -> str:
    return "\n".join(
        format_citation(result, include_paths=include_paths, include_score=include_scores) for result in results
    )
