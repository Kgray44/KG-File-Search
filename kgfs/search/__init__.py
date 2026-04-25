"""Search package compatibility exports."""

from kgfs.db.latest_results import get_latest_result_path, get_latest_result_record, save_latest_results
from kgfs.search.backends import (
    BackendAvailability,
    VectorIndexStatus,
    VectorSearchHit,
    VectorSearchOptions,
    get_vector_backend,
)
from kgfs.search.engine import SearchAvailability, SearchContext, SearchEngine
from kgfs.search.explain import build_score_explanation, explain_result
from kgfs.search.filters import SearchFilters
from kgfs.search.keyword import search, semantic_search, hybrid_search
from kgfs.search.options import SearchMode, SearchOptions
from kgfs.search.query import build_fts_query
from kgfs.search.ranking import exact_phrase_relevance, filename_path_relevance, recent_modification_bonus
from kgfs.search.registry import (
    SearchExecution,
    SearchModeError,
    SearchModeUnavailable,
    SearchRegistry,
    UnknownSearchMode,
    build_default_search_registry,
)
from kgfs.search.result import SearchExplanation, SearchResult

__all__ = [
    "SearchAvailability",
    "SearchContext",
    "SearchEngine",
    "SearchExecution",
    "SearchFilters",
    "SearchExplanation",
    "SearchMode",
    "SearchModeError",
    "SearchModeUnavailable",
    "SearchOptions",
    "SearchResult",
    "SearchRegistry",
    "UnknownSearchMode",
    "BackendAvailability",
    "VectorIndexStatus",
    "VectorSearchHit",
    "VectorSearchOptions",
    "build_fts_query",
    "build_default_search_registry",
    "build_score_explanation",
    "exact_phrase_relevance",
    "filename_path_relevance",
    "get_latest_result_path",
    "get_latest_result_record",
    "explain_result",
    "hybrid_search",
    "recent_modification_bonus",
    "save_latest_results",
    "search",
    "semantic_search",
    "get_vector_backend",
]
