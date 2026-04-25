"""Search package compatibility exports."""

from kgfs.db.latest_results import get_latest_result_path, save_latest_results
from kgfs.search.filters import SearchFilters
from kgfs.search.keyword import search, semantic_search, hybrid_search
from kgfs.search.query import build_fts_query
from kgfs.search.ranking import exact_phrase_relevance, filename_path_relevance, recent_modification_bonus
from kgfs.core.models import SearchResult

__all__ = [
    "SearchFilters",
    "SearchResult",
    "build_fts_query",
    "exact_phrase_relevance",
    "filename_path_relevance",
    "get_latest_result_path",
    "hybrid_search",
    "recent_modification_bonus",
    "save_latest_results",
    "search",
    "semantic_search",
]
