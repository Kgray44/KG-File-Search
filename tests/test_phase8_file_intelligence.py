from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from kgfs.cli import app
from kgfs.config import KGFSConfig, SemanticSettings
from kgfs.database import connect_database, initialize_database, save_latest_results
from kgfs.indexing import index_configured_folders
from kgfs.migrations import CURRENT_SCHEMA_VERSION, get_schema_version
from kgfs.search import search
from kgfs.workflows.collections import add_results_to_collection, create_collection, get_collection_items
from kgfs.workflows.notes import add_note, list_notes
from kgfs.workflows.projects import get_project, get_project_items
from kgfs.workflows.saved_searches import list_saved_searches, save_search
from kgfs.workflows.tags import list_file_tags, tag_result


runner = CliRunner()


class FakeEmbedder:
    model_name = "fake-local-model"

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            lower = text.casefold()
            if "motor" in lower or "torque" in lower or "robotics" in lower:
                vectors.append([1.0, 0.0, 0.0])
            elif "crossover" in lower or "speaker" in lower or "filter" in lower:
                vectors.append([0.0, 1.0, 0.0])
            else:
                vectors.append([0.0, 0.0, 1.0])
        return vectors


def _make_intelligence_corpus(tmp_path: Path, *, semantic: bool = False):
    root = tmp_path / "docs"
    project = root / "robotics"
    audio = root / "audio"
    project.mkdir(parents=True)
    audio.mkdir()
    files = {
        project / "motor torque lab draft.md": "Motor torque derivation for robotics lab with radius force current.",
        project / "motor torque lab final.md": "Motor torque derivation for robotics lab with radius force current and final notes.",
        project / "motor torque lab copy.md": "Motor torque derivation for robotics lab with radius force current and final notes.",
        project / "motor data.csv": "time,torque\n1,2\n",
        audio / "speaker crossover notes.md": "Speaker crossover filter design and op amp buffers.",
        audio / "speaker crossover copy.md": "Speaker crossover filter design and op amp buffers.",
    }
    for path, text in files.items():
        path.write_text(text, encoding="utf-8")
    config = KGFSConfig(
        indexed_folders=[root],
        database_path=tmp_path / "kgfs.sqlite3",
        semantic=SemanticSettings(
            enabled=semantic,
            model_name="fake-local-model",
            chunk_size_chars=160,
            chunk_overlap_chars=0,
        ),
    )
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    index_configured_folders(config, conn, semantic_embedder=FakeEmbedder() if semantic else None)
    return root, config, conn


def _save_latest(conn, query: str = "motor torque"):
    results = search(conn, query, limit=10)
    save_latest_results(conn, query, results)
    return results


def test_schema_and_config_include_phase8_defaults(tmp_path: Path) -> None:
    from kgfs.intelligence.models import DuplicateGroup, HealthReport

    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)

    tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
    config = KGFSConfig()

    assert get_schema_version(conn) == CURRENT_SCHEMA_VERSION
    assert {"graph_edges", "project_candidates", "metadata_backups"}.issubset(tables)
    assert config.intelligence.duplicate_min_semantic_score == 0.92
    assert config.metadata.auto_backup_before_reset is True
    assert DuplicateGroup
    assert HealthReport


def test_exact_and_semantic_duplicates_are_local_and_non_destructive(tmp_path: Path) -> None:
    from kgfs.intelligence.duplicates import find_exact_duplicates, find_semantic_duplicates

    root, config, conn = _make_intelligence_corpus(tmp_path, semantic=True)
    before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}

    exact = find_exact_duplicates(conn)
    semantic = find_semantic_duplicates(conn, config, min_score=0.9)

    assert any({"motor torque lab final.md", "motor torque lab copy.md"}.issubset({item.file_name for item in group.items}) for group in exact.groups)
    assert exact.groups[0].reclaimable_size > 0
    assert any(group.score >= 0.9 for group in semantic.groups)
    assert {path: path.read_bytes() for path in root.rglob("*") if path.is_file()} == before
    assert not list(root.rglob("*.kgfs*"))


def test_semantic_duplicates_report_missing_vectors_helpfully(tmp_path: Path) -> None:
    from kgfs.intelligence.duplicates import find_semantic_duplicates

    _, config, conn = _make_intelligence_corpus(tmp_path, semantic=False)

    report = find_semantic_duplicates(conn, config, min_score=0.9)

    assert report.groups == []
    assert any("vector" in warning.casefold() or "semantic" in warning.casefold() for warning in report.warnings)


def test_version_finder_detects_likely_versions_from_latest_result(tmp_path: Path) -> None:
    from kgfs.intelligence.versions import find_versions_for_result

    _, config, conn = _make_intelligence_corpus(tmp_path)
    latest = _save_latest(conn, "motor torque final")
    result_id = next(result.result_id for result in latest if result.file_name == "motor torque lab final.md")

    candidates = find_versions_for_result(conn, result_id, config)

    assert candidates
    assert candidates[0].score >= config.intelligence.version_min_similarity
    assert any("draft" in candidate.file_name for candidate in candidates)
    assert any("same folder" in " ".join(candidate.evidence).casefold() for candidate in candidates)


def test_project_inference_candidates_and_acceptance_are_metadata_only(tmp_path: Path) -> None:
    from kgfs.intelligence.projects import accept_project_candidate, infer_project_candidates, list_project_candidates

    root, config, conn = _make_intelligence_corpus(tmp_path)
    before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}

    inferred = infer_project_candidates(conn, config, persist=True)
    candidates = list_project_candidates(conn)
    accepted = accept_project_candidate(conn, candidates[0].id, name="Robotics")

    assert inferred
    assert candidates[0].file_ids
    assert accepted.added >= 2
    assert get_project(conn, "Robotics") is not None
    assert get_project_items(conn, "Robotics")
    assert {path: path.read_bytes() for path in root.rglob("*") if path.is_file()} == before


def test_graph_health_and_metadata_roundtrip(tmp_path: Path) -> None:
    from kgfs.intelligence.export import export_metadata, import_metadata
    from kgfs.intelligence.graph import build_topic_graph, export_graph_markdown
    from kgfs.intelligence.health import build_health_report

    root, config, conn = _make_intelligence_corpus(tmp_path)
    latest = _save_latest(conn, "motor torque")
    result_id = latest[0].result_id
    save_search(conn, "motor lab", "motor torque")
    create_collection(conn, "Motor Project")
    add_results_to_collection(conn, "Motor Project", [result_id])
    tag_result(conn, result_id, ["robotics", "torque"])
    add_note(conn, result_id, "Torque derivation is here.")

    graph = build_topic_graph(conn, "motor torque", config)
    markdown = export_graph_markdown(graph)
    health = build_health_report(conn, config, database_path=tmp_path / "kgfs.sqlite3")
    payload = export_metadata(conn)

    assert any(node.type == "file" for node in graph.nodes)
    assert "motor torque" in markdown
    assert health.summary["indexed_files"] >= 1
    assert health.workflow_counts["collections"] == 1
    dumped = json.dumps(payload, ensure_ascii=False)
    assert "Torque derivation is here." in dumped
    assert "Motor torque derivation for robotics lab" not in dumped

    new_db = tmp_path / "kgfs-restored.sqlite3"
    restored = connect_database(new_db)
    initialize_database(restored)
    restored_config = config.model_copy(update={"database_path": new_db})
    index_configured_folders(restored_config, restored)
    summary = import_metadata(restored, payload, yes=True)

    assert summary.restored_items > 0
    assert summary.unmatched_items == 0
    assert list_saved_searches(restored)[0].name == "motor lab"
    restored_latest = _save_latest(restored, "motor torque")
    restored_result_id = restored_latest[0].result_id
    assert "torque" in list_file_tags(restored, restored_result_id)
    assert list_notes(restored, restored_result_id)[0].note == "Torque derivation is here."
    assert get_collection_items(restored, "Motor Project")
    counts_before_second_import = {
        table: restored.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"]
        for table in ("saved_searches", "collections", "collection_items", "tags", "file_tags", "file_notes", "projects")
    }

    second_summary = import_metadata(restored, payload, yes=True)

    assert second_summary.unmatched_items == 0
    assert {
        table: restored.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"]
        for table in counts_before_second_import
    } == counts_before_second_import


def test_phase8_cli_commands_project_local_workflow(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    source = root / "motor torque v1.md"
    duplicate = root / "motor torque copy.md"
    final = root / "motor torque v2 final.md"
    source.write_text("motor torque derivation for robotics", encoding="utf-8")
    duplicate.write_text("motor torque derivation for robotics", encoding="utf-8")
    final.write_text("motor torque derivation for robotics final update", encoding="utf-8")
    before = {path.name: path.read_bytes() for path in root.iterdir()}
    config_path = tmp_path / "config.yaml"
    db_path = tmp_path / "kgfs.sqlite3"
    config_path.write_text(f"indexed_folders:\n  - {root.as_posix()!r}\n", encoding="utf-8")
    export_path = tmp_path / "kgfs-metadata-test.json"

    for command in ("duplicates", "versions", "graph", "health", "metadata", "project"):
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0

    assert runner.invoke(app, ["index", "--config", str(config_path), "--database", str(db_path)]).exit_code == 0
    assert runner.invoke(app, ["search", "motor torque", "--config", str(config_path), "--database", str(db_path)]).exit_code == 0
    assert runner.invoke(app, ["duplicates", "--config", str(config_path), "--database", str(db_path)]).exit_code == 0
    assert runner.invoke(app, ["versions", "1", "--config", str(config_path), "--database", str(db_path)]).exit_code == 0
    assert runner.invoke(app, ["project", "infer", "--config", str(config_path), "--database", str(db_path)]).exit_code == 0
    assert runner.invoke(app, ["project", "candidates", "--config", str(config_path), "--database", str(db_path)]).exit_code == 0
    assert runner.invoke(app, ["graph", "motor torque", "--config", str(config_path), "--database", str(db_path)]).exit_code == 0
    health_result = runner.invoke(app, ["health", "--json", "--config", str(config_path), "--database", str(db_path)])
    assert health_result.exit_code == 0
    assert "indexed_files" in health_result.output
    assert runner.invoke(app, ["metadata", "export", "--output", str(export_path), "--config", str(config_path), "--database", str(db_path)]).exit_code == 0

    assert export_path.exists()
    assert {path.name: path.read_bytes() for path in root.iterdir()} == before
    assert not list(root.glob("*.kgfs*"))
