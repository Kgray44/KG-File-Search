from __future__ import annotations

from pathlib import Path

import pytest

from kgfs.config import KGFSConfig, SemanticSettings
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.search.engine import SearchContext
from kgfs.search.options import SearchMode, SearchOptions
from kgfs.search.registry import SearchModeUnavailable, UnknownSearchMode, build_default_search_registry


class FakeEmbedder:
    model_name = "fake-local-model"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        lower = text.lower()
        if any(term in lower for term in ("torque", "rotational", "motor")):
            return [1.0, 0.0, 0.0]
        if any(term in lower for term in ("op amp", "op-amp", "thevenin")):
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]


def _make_index(tmp_path: Path, *, semantic_enabled: bool = False, build_chunks: bool = False):
    root = tmp_path / "docs"
    root.mkdir()
    (root / "motor torque.md").write_text("rotational force calculations for a motor lab", encoding="utf-8")
    (root / "circuits.md").write_text("Thevenin equivalent and op amp circuit notes", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    config = KGFSConfig(
        indexed_folders=[root],
        semantic=SemanticSettings(
            enabled=semantic_enabled,
            model_name="fake-local-model",
            chunk_size_chars=48,
            chunk_overlap_chars=8,
        ),
    )
    indexing_config = config if build_chunks else config.model_copy(update={"semantic": SemanticSettings(enabled=False)})
    index_configured_folders(indexing_config, conn, semantic_embedder=FakeEmbedder() if build_chunks else None)
    return conn, config


def test_registry_registers_core_search_modes(tmp_path: Path) -> None:
    conn, config = _make_index(tmp_path)
    registry = build_default_search_registry()
    context = SearchContext(conn=conn, config=config)

    assert registry.get(SearchMode.KEYWORD).name == SearchMode.KEYWORD
    assert registry.get(SearchMode.SEMANTIC).name == SearchMode.SEMANTIC
    assert registry.get(SearchMode.HYBRID).name == SearchMode.HYBRID
    assert registry.modes() == [SearchMode.KEYWORD, SearchMode.SEMANTIC, SearchMode.HYBRID]
    assert registry.available_modes(context) == [SearchMode.KEYWORD]


def test_registry_rejects_unknown_mode_with_helpful_error() -> None:
    registry = build_default_search_registry()

    with pytest.raises(UnknownSearchMode, match="Unknown search mode"):
        registry.get("deep")


def test_auto_mode_uses_keyword_when_semantic_is_disabled(tmp_path: Path) -> None:
    conn, config = _make_index(tmp_path)
    registry = build_default_search_registry()
    context = SearchContext(conn=conn, config=config)

    execution = registry.search("motor torque", SearchOptions(mode=SearchMode.AUTO), context)

    assert execution.mode_used == SearchMode.KEYWORD
    assert execution.warnings == []
    assert execution.results[0].mode == "keyword"
    assert execution.results[0].file_name == "motor torque.md"


def test_auto_mode_falls_back_to_keyword_with_warning_when_semantic_is_not_ready(tmp_path: Path) -> None:
    conn, config = _make_index(tmp_path, semantic_enabled=True, build_chunks=False)
    registry = build_default_search_registry()
    context = SearchContext(conn=conn, config=config)

    execution = registry.search("motor torque", SearchOptions(mode=SearchMode.AUTO), context)

    assert execution.mode_used == SearchMode.KEYWORD
    assert any("Semantic search is unavailable" in warning for warning in execution.warnings)
    assert execution.results[0].file_name == "motor torque.md"


def test_auto_mode_uses_hybrid_when_semantic_is_ready(tmp_path: Path) -> None:
    conn, config = _make_index(tmp_path, semantic_enabled=True, build_chunks=True)
    registry = build_default_search_registry()
    context = SearchContext(conn=conn, config=config, semantic_embedder=FakeEmbedder())

    execution = registry.search("motor torque", SearchOptions(mode=SearchMode.AUTO), context)

    assert execution.mode_used == SearchMode.HYBRID
    assert execution.results[0].mode == "hybrid"
    assert execution.results[0].file_name == "motor torque.md"


def test_keyword_engine_does_not_require_semantic_dependencies(tmp_path: Path, monkeypatch) -> None:
    conn, config = _make_index(tmp_path)
    registry = build_default_search_registry()
    context = SearchContext(conn=conn, config=config)
    monkeypatch.setattr(
        "kgfs.search.modes.semantic.get_embedder",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("semantic dependency was imported")),
    )

    execution = registry.search("motor torque", SearchOptions(mode=SearchMode.KEYWORD), context)

    assert execution.mode_used == SearchMode.KEYWORD
    assert execution.results[0].file_name == "motor torque.md"


def test_explicit_semantic_mode_reports_unavailable_when_not_ready(tmp_path: Path) -> None:
    conn, config = _make_index(tmp_path, semantic_enabled=True, build_chunks=False)
    registry = build_default_search_registry()
    context = SearchContext(conn=conn, config=config)

    with pytest.raises(SearchModeUnavailable, match="Semantic search is unavailable"):
        registry.search("motor torque", SearchOptions(mode=SearchMode.SEMANTIC), context)
