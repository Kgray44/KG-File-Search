from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from kgfs.ai import build_ai_context
from kgfs.cli import app
from kgfs.config import AISettings, KGFSConfig, SemanticSettings
from kgfs.database import connect_database, initialize_database, save_latest_results
from kgfs.indexing import index_configured_folders
from kgfs.models import SearchResult
from kgfs.search import search
from kgfs.search.citations import format_citation, format_citation_block
from kgfs.search.compare import compare_results
from kgfs.search.deep import deep_search, generate_query_variants
from kgfs.search.research import research_query
from kgfs.search.similar import similar_file, similar_from_result
from kgfs.search.timeline import timeline_search


runner = CliRunner()


class FakeEmbedder:
    model_name = "fake-local-model"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        lower = text.casefold()
        if any(term in lower for term in ("motor", "torque", "rotational")):
            return [1.0, 0.0, 0.0]
        if any(term in lower for term in ("speaker", "crossover", "filter")):
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]


def _make_corpus(tmp_path: Path, *, semantic: bool = False):
    root = tmp_path / "docs"
    root.mkdir()
    motor = root / "motor torque lab.md"
    motor.write_text(
        "Motor torque calculations used current, radius, and rotational force.",
        encoding="utf-8",
    )
    speaker = root / "speaker crossover.md"
    speaker.write_text(
        "Speaker crossover design uses capacitors, inductors, and filter slopes.",
        encoding="utf-8",
    )
    active = root / "active crossover notes.md"
    active.write_text(
        "Active crossover design notes mention op amps and speaker filter stages.",
        encoding="utf-8",
    )
    config = KGFSConfig(
        indexed_folders=[root],
        database_path=tmp_path / "kgfs.sqlite3",
        semantic=SemanticSettings(
            enabled=semantic,
            model_name="fake-local-model",
            chunk_size_chars=80,
            chunk_overlap_chars=10,
        ),
    )
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    index_configured_folders(config, conn, semantic_embedder=FakeEmbedder() if semantic else None)
    return root, config, conn


def test_citations_format_local_result_ids_and_ocr_source(tmp_path: Path) -> None:
    result = SearchResult(
        result_id=3,
        file_id=8,
        file_name="scan.png",
        path=tmp_path / "scan.png",
        extension=".png",
        modified_time=1.0,
        score=0.75,
        snippet="visible motor torque",
        matched_chunk_id=42,
        mode="keyword",
        source="keyword",
        metadata={"extraction_source": "ocr", "ocr_source_kind": "image"},
    )

    assert format_citation(result) == "[3] scan.png (OCR, chunk 42)"
    assert "[3] scan.png" in format_citation_block([result])
    assert str(tmp_path) not in format_citation_block([result], include_paths=False)


def test_deep_search_keyword_only_expands_queries_fuses_candidates_and_saves_latest(tmp_path: Path) -> None:
    _, config, conn = _make_corpus(tmp_path)

    variants = generate_query_variants("active crossover design", max_variants=5)
    report = deep_search(conn, "active crossover design", config, limit=3, mode="keyword")
    latest = conn.execute("SELECT COUNT(*) AS count FROM latest_results").fetchone()["count"]

    assert variants[0] == "active crossover design"
    assert "active crossover" in variants
    assert report.results[0].file_name == "active crossover notes.md"
    assert "active crossover design" in report.variants
    assert report.results[0].metadata["deep_subqueries"]
    assert report.followups
    assert latest == len(report.results)


def test_similar_from_result_falls_back_to_keyword_similarity_and_excludes_self(tmp_path: Path) -> None:
    _, config, conn = _make_corpus(tmp_path)
    results = search(conn, "speaker crossover", limit=3)
    save_latest_results(conn, "speaker crossover", results)

    report = similar_from_result(conn, 1, config, limit=5)

    assert report.source.file_name == "speaker crossover.md"
    assert report.results
    assert all(result.file_id != report.source.file_id for result in report.results)
    assert all(result.score > 0 for result in report.results)
    assert report.results[0].score > 0
    assert report.results[0].metadata["similar_reason"]


def test_similar_from_result_uses_vectors_when_semantic_chunks_are_available(tmp_path: Path) -> None:
    _, config, conn = _make_corpus(tmp_path, semantic=True)
    results = search(conn, "motor torque", limit=3)
    save_latest_results(conn, "motor torque", results)

    report = similar_from_result(conn, 1, config, limit=5)

    assert report.strategy == "vector"
    assert all(result.file_id != report.source.file_id for result in report.results)


def test_similar_file_requires_indexed_path_and_does_not_modify_source(tmp_path: Path) -> None:
    root, config, conn = _make_corpus(tmp_path)
    indexed = root / "motor torque lab.md"
    before = indexed.read_bytes()
    missing = root / "unindexed.md"
    missing.write_text("unindexed text", encoding="utf-8")

    report = similar_file(conn, indexed, config, limit=3)

    assert report.source.file_name == "motor torque lab.md"
    assert indexed.read_bytes() == before
    try:
        similar_file(conn, missing, config)
    except ValueError as exc:
        assert "not indexed" in str(exc)
    else:
        raise AssertionError("Expected unindexed file to fail helpfully")


def test_compare_results_reports_shared_and_unique_terms(tmp_path: Path) -> None:
    _, config, conn = _make_corpus(tmp_path)
    results = search(conn, "crossover", limit=3)
    save_latest_results(conn, "crossover", results)

    comparison = compare_results(conn, 1, 2, config)

    assert comparison.left.file_name != comparison.right.file_name
    assert "crossover" in comparison.shared_terms
    assert comparison.left_unique_terms or comparison.right_unique_terms
    assert 0.0 <= comparison.text_similarity <= 1.0


def test_timeline_search_sorts_results_by_modified_time_and_respects_filters(tmp_path: Path) -> None:
    _, config, conn = _make_corpus(tmp_path)
    rows = conn.execute("SELECT id, file_name FROM files").fetchall()
    for row in rows:
        mtime = 1000.0 if "motor" in row["file_name"] else 2000.0
        conn.execute("UPDATE files SET modified_time = ? WHERE id = ?", (mtime, row["id"]))
    conn.commit()

    report = timeline_search(conn, "crossover", config, limit=5, group="year")

    assert report.items
    assert report.items == sorted(report.items, key=lambda item: item.modified_time)
    assert report.groups
    assert all(
        "crossover" in item.snippet.casefold() or "crossover" in item.file_name.casefold() for item in report.items
    )


def test_research_query_returns_local_citations_terms_and_followups_without_ai(tmp_path: Path, mocker) -> None:
    _, config, conn = _make_corpus(tmp_path)
    mocked_client = mocker.patch("kgfs.ai.get_openai_client")

    report = research_query(conn, "speaker crossover", config, limit=5)

    assert report.results
    assert "[1]" in report.citations
    assert "crossover" in report.related_terms
    assert "bold" not in report.related_terms
    assert report.followups
    mocked_client.assert_not_called()


def test_ai_context_uses_local_citations_and_ocr_labels(tmp_path: Path) -> None:
    result = SearchResult(
        result_id=1,
        file_id=1,
        file_name="scan.png",
        path=tmp_path / "scan.png",
        extension=".png",
        modified_time=1.0,
        score=1.0,
        snippet="OCR snippet about motor torque",
        metadata={"extraction_source": "ocr", "ocr_source_kind": "image"},
    )

    context = build_ai_context("where is torque?", [result], AISettings(enabled=True), home=tmp_path)

    assert "Citation: [1] scan.png (OCR)" in context
    assert str(tmp_path) not in context


def test_advanced_cli_help_and_project_local_workflow(tmp_path: Path) -> None:
    for command in ("deep", "similar", "similar-file", "compare", "timeline", "research"):
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0

    root = tmp_path / "docs"
    root.mkdir()
    source = root / "motor.md"
    source.write_text("motor torque calculations and rotational force", encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    db_path = tmp_path / "kgfs.sqlite3"
    config_path.write_text(f"indexed_folders:\n  - {root.as_posix()!r}\n", encoding="utf-8")
    before = source.read_bytes()

    index_result = runner.invoke(app, ["index", "--config", str(config_path), "--database", str(db_path)])
    deep_result = runner.invoke(app, ["deep", "motor torque", "--config", str(config_path), "--database", str(db_path)])
    search_result = runner.invoke(
        app, ["search", "motor torque", "--config", str(config_path), "--database", str(db_path)]
    )
    similar_result = runner.invoke(app, ["similar", "1", "--config", str(config_path), "--database", str(db_path)])
    timeline_result = runner.invoke(
        app, ["timeline", "motor", "--config", str(config_path), "--database", str(db_path)]
    )
    research_result = runner.invoke(
        app, ["research", "motor torque", "--config", str(config_path), "--database", str(db_path)]
    )

    assert index_result.exit_code == 0
    assert deep_result.exit_code == 0
    assert "Deep Search" in deep_result.output
    assert search_result.exit_code == 0
    assert similar_result.exit_code == 0
    assert timeline_result.exit_code == 0
    assert research_result.exit_code == 0
    assert source.read_bytes() == before
    assert not list(root.glob("*.kgfs*"))
    assert not list(root.glob("*.sidecar*"))
