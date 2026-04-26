from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from kgfs.cli import app
from kgfs.config import KGFSConfig
from kgfs.database import connect_database, initialize_database, save_latest_results
from kgfs.indexing import index_configured_folders
from kgfs.migrations import CURRENT_SCHEMA_VERSION, get_schema_version
from kgfs.search import search
from kgfs.workflows.assignments import assignment_working_set
from kgfs.workflows.collections import (
    add_results_to_collection,
    create_collection,
    export_collection_markdown,
    get_collection_items,
    remove_files_from_collection,
)
from kgfs.workflows.notes import add_note, delete_note, list_notes
from kgfs.workflows.profiles import create_profile, delete_profile, get_profile, profile_search
from kgfs.workflows.projects import add_results_to_project, create_project, project_search, remove_files_from_project
from kgfs.workflows.saved_searches import delete_saved_search, list_saved_searches, run_saved_search, save_search
from kgfs.workflows.tags import list_all_tags, list_file_tags, list_tagged_files, tag_result, untag_result


runner = CliRunner()


def _make_workflow_corpus(tmp_path: Path):
    root = tmp_path / "docs"
    root.mkdir()
    motor = root / "motor torque lab.md"
    motor.write_text("Motor torque derivation for robotics lab with current radius and force.", encoding="utf-8")
    circuits = root / "circuits op amp notes.md"
    circuits.write_text("Op amp gain notes include Thevenin equivalent and lab report details.", encoding="utf-8")
    data = root / "motor data.csv"
    data.write_text("time,torque\n1,2\n", encoding="utf-8")
    config = KGFSConfig(indexed_folders=[root], database_path=tmp_path / "kgfs.sqlite3")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    index_configured_folders(config, conn)
    return root, config, conn


def _latest(conn, query: str = "motor torque"):
    results = search(conn, query, limit=10)
    save_latest_results(conn, query, results)
    return results


def test_schema_initializes_workflow_tables_and_version(tmp_path: Path) -> None:
    conn = connect_database(tmp_path / "kgfs.sqlite3")

    initialize_database(conn)

    tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
    assert get_schema_version(conn) == CURRENT_SCHEMA_VERSION
    assert {
        "profiles",
        "saved_searches",
        "collections",
        "collection_items",
        "tags",
        "file_tags",
        "file_notes",
        "projects",
        "project_items",
        "assignment_runs",
    }.issubset(tables)


def test_profiles_can_be_created_searched_and_deleted_without_touching_files(tmp_path: Path) -> None:
    root, config, conn = _make_workflow_corpus(tmp_path)
    source = root / "circuits op amp notes.md"
    before = source.read_bytes()

    create_profile(
        conn,
        "school",
        folders=[root],
        extensions=[".md"],
        default_mode="keyword",
        boost_terms=["lab"],
    )
    report = profile_search(conn, "school", "op amp gain", config, limit=5)
    delete_profile(conn, "school")

    assert get_profile(conn, "school") is None
    assert report.results
    assert all(result.extension == ".md" for result in report.results)
    assert report.results[0].file_name == "circuits op amp notes.md"
    assert source.read_bytes() == before


def test_saved_searches_store_filters_run_and_save_latest_results(tmp_path: Path) -> None:
    _, config, conn = _make_workflow_corpus(tmp_path)

    save_search(conn, "motor lab", "motor torque", mode="keyword", filters={"extensions": [".md"]})
    report = run_saved_search(conn, "motor lab", config, limit=5)
    saved = list_saved_searches(conn)
    latest_count = conn.execute("SELECT COUNT(*) AS count FROM latest_results").fetchone()["count"]
    delete_saved_search(conn, "motor lab")

    assert saved[0].name == "motor lab"
    assert report.results
    assert all(result.extension == ".md" for result in report.results)
    assert latest_count == len(report.results)
    assert list_saved_searches(conn) == []


def test_collections_group_latest_results_export_and_remove_without_source_sidecars(tmp_path: Path) -> None:
    root, _, conn = _make_workflow_corpus(tmp_path)
    _latest(conn, "motor torque")
    before = {path.name: path.read_bytes() for path in root.iterdir() if path.is_file()}

    create_collection(conn, "Motor Project")
    add_summary = add_results_to_collection(conn, "Motor Project", [1])
    items = get_collection_items(conn, "Motor Project")
    exported = export_collection_markdown(conn, "Motor Project")
    assert items[0].result_id == 1
    assert items[0].file_id != 1

    remove_files_from_collection(conn, "Motor Project", [1])
    remaining = get_collection_items(conn, "Motor Project")

    assert add_summary.added >= 1
    assert "[1]" in exported
    assert "Motor Project" in exported
    assert remaining == []
    assert {path.name: path.read_bytes() for path in root.iterdir() if path.is_file()} == before
    assert not list(root.glob("*.kgfs*"))


def test_tags_and_notes_attach_to_files_and_prune_with_files(tmp_path: Path) -> None:
    root, _, conn = _make_workflow_corpus(tmp_path)
    results = _latest(conn, "motor torque")
    source = next(result for result in results if result.file_name == "motor torque lab.md")

    tag_result(conn, source.result_id, ["robotics", "Torque"])
    note = add_note(conn, source.result_id, "Torque derivation is here.")

    assert list_file_tags(conn, source.result_id) == ["robotics", "torque"]
    assert list_notes(conn, source.result_id)[0].note == "Torque derivation is here."
    assert list_tagged_files(conn, "torque")
    assert "robotics" in list_all_tags(conn)

    untag_result(conn, source.result_id, ["torque"])
    delete_note(conn, note.id)

    assert list_file_tags(conn, source.result_id) == ["robotics"]
    assert list_notes(conn, source.result_id) == []
    (root / "motor torque lab.md").unlink()
    from kgfs.prune import prune_stale_files

    prune_stale_files(conn)
    assert (
        conn.execute("SELECT COUNT(*) AS count FROM file_tags WHERE file_id = ?", (source.file_id,)).fetchone()["count"]
        == 0
    )


def test_assignment_and_projects_work_locally_without_modifying_sources(tmp_path: Path) -> None:
    root, config, conn = _make_workflow_corpus(tmp_path)
    _latest(conn, "motor torque")
    before = {path.name: path.read_bytes() for path in root.iterdir() if path.is_file()}

    assignment = assignment_working_set(conn, "motor torque", config, create_collection_name="Motor Assignment")
    create_project(conn, "Robotics")
    add_results_to_project(conn, "Robotics", [1])
    project_report = project_search(conn, "Robotics", "torque", config)
    remove_files_from_project(conn, "Robotics", [1])

    assert assignment.results
    assert "notes" in assignment.categories or "data" in assignment.categories
    assert "open top result" in " ".join(assignment.next_actions).lower()
    assert get_collection_items(conn, "Motor Assignment")
    assert project_report.results
    assert all("motor" in result.file_name.casefold() for result in project_report.results)
    assert project_search(conn, "Robotics", "torque", config).results == []
    assert {path.name: path.read_bytes() for path in root.iterdir() if path.is_file()} == before


def test_phase7_cli_commands_project_local_workflow(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    source = root / "motor.md"
    source.write_text("motor torque derivation for robotics lab", encoding="utf-8")
    before = source.read_bytes()
    config_path = tmp_path / "config.yaml"
    db_path = tmp_path / "kgfs.sqlite3"
    config_path.write_text(f"indexed_folders:\n  - {root.as_posix()!r}\n", encoding="utf-8")

    for command in ("profile", "save-search", "collection", "tag", "note", "assignment", "project"):
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0

    assert runner.invoke(app, ["index", "--config", str(config_path), "--database", str(db_path)]).exit_code == 0
    assert (
        runner.invoke(
            app, ["search", "motor torque", "--config", str(config_path), "--database", str(db_path)]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["profile", "create", "school", "--ext", ".md", "--config", str(config_path), "--database", str(db_path)],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["profile", "search", "school", "motor torque", "--config", str(config_path), "--database", str(db_path)],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["save-search", "motor lab", "motor torque", "--config", str(config_path), "--database", str(db_path)]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["run-search", "motor lab", "--config", str(config_path), "--database", str(db_path)]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["collection", "create", "Motor Project", "--config", str(config_path), "--database", str(db_path)]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["collection", "add", "Motor Project", "1", "--config", str(config_path), "--database", str(db_path)]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["tag", "1", "robotics", "torque", "--config", str(config_path), "--database", str(db_path)]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["note", "1", "Torque derivation is here.", "--config", str(config_path), "--database", str(db_path)]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["assignment", "motor torque", "--config", str(config_path), "--database", str(db_path)]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["project", "create", "Robotics", "--config", str(config_path), "--database", str(db_path)]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["project", "add", "Robotics", "1", "--config", str(config_path), "--database", str(db_path)]
        ).exit_code
        == 0
    )
    project_search_result = runner.invoke(
        app, ["project", "search", "Robotics", "torque", "--config", str(config_path), "--database", str(db_path)]
    )

    assert project_search_result.exit_code == 0
    assert "motor.md" in project_search_result.output
    assert source.read_bytes() == before
    assert not list(root.glob("*.kgfs*"))
