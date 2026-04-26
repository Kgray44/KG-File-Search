"""Lightweight result explanation helpers."""

from __future__ import annotations

from kgfs.search.options import SearchMode
from kgfs.search.result import SearchExplanation, SearchResult


def explain_result(
    result: SearchResult,
    query: str,
    *,
    mode_used: SearchMode | str | None = None,
    notes: list[str] | None = None,
) -> SearchExplanation:
    mode = SearchMode.coerce(mode_used or result.mode or SearchMode.KEYWORD)
    breakdown = result.score_breakdown or {"final": result.score}
    summary = build_score_explanation(query, result, breakdown)
    explanation_notes = list(notes or [])
    extraction_source = str(result.metadata.get("extraction_source", "") if result.metadata else "")
    if extraction_source.startswith("ocr"):
        explanation_notes.append("This result matched OCR-derived text stored in the local KGFS index.")
    if extraction_source.startswith("media:"):
        explanation_notes.append("This result matched media-derived text stored in the local KGFS index.")
    return SearchExplanation(
        mode=mode,
        summary=summary,
        score_breakdown=breakdown,
        result_id=result.result_id,
        file_name=result.file_name,
        path=result.path,
        final_score=breakdown.get("final", result.score),
        snippet=result.snippet,
        notes=explanation_notes,
    )


def build_score_explanation(query: str, result: SearchResult, breakdown: dict[str, float]) -> str:
    useful_components = {
        key: value
        for key, value in breakdown.items()
        if key not in {"final", "bm25"} and value > 0
    }
    if not useful_components:
        return f"Result matched '{query}' with a final score of {result.score:.3f}."
    strongest = max(useful_components.items(), key=lambda item: item[1])[0].replace("_", " ")
    return (
        f"Result matched '{query}' mainly through {strongest} relevance, "
        f"with supporting local score components shown below."
    )
