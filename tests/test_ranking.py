from datetime import datetime, timezone
from pathlib import Path

from kgfs.config import KGFSConfig
from kgfs.config import HybridSettings
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.search import search
from kgfs.search.ranking import combine_hybrid_score


def test_filename_match_gets_modest_ranking_bonus(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "motor torque notes.md").write_text("ordinary lab notes", encoding="utf-8")
    (root / "random.md").write_text("motor torque motor torque motor torque", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    index_configured_folders(KGFSConfig(indexed_folders=[root]), conn)

    results = search(conn, "motor torque")

    assert results[0].file_name == "motor torque notes.md"


def test_exact_phrase_beats_weak_token_match(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "exact.md").write_text("speaker crossover design details", encoding="utf-8")
    (root / "weak.md").write_text(
        "speaker notes and unrelated crossover notes and unrelated design notes", encoding="utf-8"
    )
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    index_configured_folders(KGFSConfig(indexed_folders=[root]), conn)

    results = search(conn, "speaker crossover design")

    assert results[0].file_name == "exact.md"


def test_recent_bonus_does_not_overpower_relevance(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    relevant = root / "relevant.md"
    recent = root / "recent.md"
    relevant.write_text("pid control loop pid control loop", encoding="utf-8")
    recent.write_text("pid mention", encoding="utf-8")
    old_time = datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp()
    new_time = datetime.now(timezone.utc).timestamp()
    import os

    os.utime(relevant, (old_time, old_time))
    os.utime(recent, (new_time, new_time))
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    index_configured_folders(KGFSConfig(indexed_folders=[root]), conn)

    results = search(conn, "pid control loop")

    assert results[0].file_name == "relevant.md"


def test_hybrid_score_breakdown_contains_standard_components() -> None:
    final_score, breakdown = combine_hybrid_score(
        query="op amp gain",
        file_name="op amp notes.md",
        path="/classes/circuits/op amp notes.md",
        extracted_text="These notes explain op amp gain and feedback.",
        modified_time=datetime.now(timezone.utc).timestamp(),
        keyword_score_value=0.8,
        semantic_score_value=0.6,
        settings=HybridSettings(),
    )

    assert final_score == breakdown["final"]
    assert set(breakdown) == {
        "keyword",
        "semantic",
        "filename",
        "path",
        "exact_phrase",
        "recency",
        "final",
    }
    assert breakdown["filename"] > 0
    assert breakdown["path"] > 0
    assert breakdown["exact_phrase"] == 1.0


def test_negative_hybrid_weights_are_ignored_safely() -> None:
    final_score, breakdown = combine_hybrid_score(
        query="pid control",
        file_name="pid.md",
        path="/docs/pid.md",
        extracted_text="pid control notes",
        modified_time=datetime.now(timezone.utc).timestamp(),
        keyword_score_value=1.0,
        semantic_score_value=1.0,
        settings=HybridSettings(keyword_weight=-100, semantic_weight=1.0),
    )

    assert final_score >= 0
    assert breakdown["keyword"] == 1.0
    assert breakdown["semantic"] == 1.0
