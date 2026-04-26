from typer.main import get_command
from typer.testing import CliRunner

from kgfs.cli import app
from kgfs.config import KGFSConfig
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.search import SearchExecution, SearchMode

runner = CliRunner()


def test_cli_exposes_required_mvp_commands() -> None:
    command = get_command(app)

    assert {
        "init",
        "index",
        "search",
        "stats",
        "open",
        "reveal",
        "config",
        "doctor",
        "web",
        "semantic",
        "ask",
        "prune",
        "add-folder",
        "remove-folder",
        "list-folders",
        "reset-index",
        "rebuild",
        "semantic-index",
        "vector",
        "why",
        "ocr",
        "deep",
        "similar",
        "similar-file",
        "compare",
        "timeline",
        "research",
        "profile",
        "save-search",
        "run-search",
        "list-searches",
        "delete-search",
        "collection",
        "tag",
        "untag",
        "tags",
        "tagged",
        "tag-list",
        "note",
        "notes",
        "note-delete",
        "assignment",
        "project",
        "duplicates",
        "versions",
        "versions-file",
        "graph",
        "graph-export",
        "health",
        "metadata",
        "tui",
        "serve",
        "integrations",
        "tray",
        "media",
    }.issubset(command.commands.keys())


def test_doctor_reports_platform_paths_and_open_strategies(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("indexed_folders: []\n", encoding="utf-8")
    db_path = tmp_path / "kgfs.sqlite3"

    result = runner.invoke(
        app,
        ["doctor", "--config", str(config_path), "--database", str(db_path)],
    )

    assert result.exit_code == 0
    assert "Cache path" in result.output
    assert "Log path" in result.output
    assert "Open files" in result.output
    assert "Reveal files" in result.output


def test_index_prints_helpful_message_when_no_folders_configured(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("indexed_folders: []\n", encoding="utf-8")
    db_path = tmp_path / "kgfs.sqlite3"

    result = runner.invoke(app, ["index", "--config", str(config_path), "--database", str(db_path)])

    assert result.exit_code == 0
    assert "No indexed folders configured" in result.output
    assert not db_path.exists()


def test_index_refuses_risky_root_without_override(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("indexed_folders:\n  - /\n", encoding="utf-8")
    db_path = tmp_path / "kgfs.sqlite3"

    result = runner.invoke(app, ["index", "--config", str(config_path), "--database", str(db_path)])

    assert result.exit_code != 0
    assert "Refusing to index risky root" in result.output


def test_index_allows_risky_root_with_explicit_override(tmp_path, mocker) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("indexed_folders:\n  - /\n", encoding="utf-8")
    db_path = tmp_path / "kgfs.sqlite3"
    mocked_index = mocker.patch("kgfs.cli.commands.index.index_configured_folders")

    result = runner.invoke(
        app,
        ["index", "--config", str(config_path), "--database", str(db_path), "--allow-risky-root"],
    )

    assert result.exit_code == 0
    mocked_index.assert_called_once()


def test_ask_preview_prints_context_and_does_not_call_api(tmp_path, mocker) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
indexed_folders: []
ai:
  enabled: true
  require_confirmation: false
""",
        encoding="utf-8",
    )
    result_item = mocker.Mock()
    result_item.result_id = 1
    result_item.file_id = 1
    result_item.file_name = "notes.md"
    result_item.path = tmp_path / "notes.md"
    result_item.extension = ".md"
    result_item.modified_time = 1.0
    result_item.score = 0.5
    result_item.snippet = "preview snippet"
    mocker.patch("kgfs.cli.commands.search.search", return_value=[result_item])
    mocked_client = mocker.patch("kgfs.cli.commands.search.get_openai_client")

    result = runner.invoke(app, ["ask", "what is here?", "--config", str(config_path), "--preview-ai-context"])

    assert result.exit_code == 0
    assert "AI Context Preview" in result.output
    assert "preview snippet" in result.output
    mocked_client.assert_not_called()


def test_ai_disabled_prevents_api_call(tmp_path, mocker) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("indexed_folders: []\nai:\n  enabled: false\n", encoding="utf-8")
    mocked_client = mocker.patch("kgfs.cli.commands.search.get_openai_client")

    result = runner.invoke(app, ["ask", "what is here?", "--config", str(config_path)])

    assert result.exit_code != 0
    assert "AI Assist is disabled" in result.output
    mocked_client.assert_not_called()


def test_search_ai_rerank_preview_prints_context_and_does_not_call_api(tmp_path, mocker) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
indexed_folders: []
ai:
  enabled: true
  require_confirmation: false
""",
        encoding="utf-8",
    )
    result_item = mocker.Mock()
    result_item.result_id = 1
    result_item.file_id = 1
    result_item.file_name = "notes.md"
    result_item.path = tmp_path / "notes.md"
    result_item.extension = ".md"
    result_item.modified_time = 1.0
    result_item.score = 0.5
    result_item.snippet = "rerank preview snippet"
    registry = mocker.Mock()
    registry.search.return_value = SearchExecution(
        results=[result_item],
        mode_requested=SearchMode.AUTO,
        mode_used=SearchMode.KEYWORD,
    )
    mocker.patch("kgfs.cli.commands.search.build_default_search_registry", return_value=registry)
    mocked_client = mocker.patch("kgfs.cli.commands.search.get_openai_client")

    result = runner.invoke(
        app,
        ["search", "query", "--config", str(config_path), "--ai-rerank", "--preview-ai-context"],
    )

    assert result.exit_code == 0
    assert "AI Context Preview" in result.output
    assert "rerank preview snippet" in result.output
    mocked_client.assert_not_called()


def _indexed_search_fixture(tmp_path):
    root = tmp_path / "docs"
    root.mkdir()
    (root / "motor notes.md").write_text("motor torque calculations", encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(f"indexed_folders:\n  - {root.as_posix()!r}\n", encoding="utf-8")
    db_path = tmp_path / "kgfs.sqlite3"
    conn = connect_database(db_path)
    initialize_database(conn)
    index_configured_folders(KGFSConfig(indexed_folders=[root]), conn)
    conn.close()
    return config_path, db_path


def test_search_mode_keyword_works_from_cli(tmp_path) -> None:
    config_path, db_path = _indexed_search_fixture(tmp_path)

    result = runner.invoke(
        app,
        ["search", "motor torque", "--mode", "keyword", "--config", str(config_path), "--database", str(db_path)],
    )

    assert result.exit_code == 0
    assert "notes.md" in result.output


def test_search_mode_auto_works_from_cli(tmp_path) -> None:
    config_path, db_path = _indexed_search_fixture(tmp_path)

    result = runner.invoke(
        app,
        ["search", "motor torque", "--mode", "auto", "--config", str(config_path), "--database", str(db_path)],
    )

    assert result.exit_code == 0
    assert "notes.md" in result.output


def test_search_mode_semantic_unavailable_is_helpful(tmp_path) -> None:
    config_path, db_path = _indexed_search_fixture(tmp_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + "\nsemantic:\n  enabled: true\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["search", "motor torque", "--mode", "semantic", "--config", str(config_path), "--database", str(db_path)],
    )

    assert result.exit_code != 0
    assert "Semantic search is unavailable" in result.output


def test_why_explains_latest_keyword_result(tmp_path) -> None:
    config_path, db_path = _indexed_search_fixture(tmp_path)
    search_result = runner.invoke(
        app,
        ["search", "motor torque", "--mode", "keyword", "--config", str(config_path), "--database", str(db_path)],
    )
    assert search_result.exit_code == 0

    result = runner.invoke(
        app,
        ["why", "1", "motor torque", "--config", str(config_path), "--database", str(db_path)],
    )

    assert result.exit_code == 0
    assert "Why result 1 matched" in result.output
    assert "motor notes.md" in result.output
    assert "Score breakdown" in result.output
    assert "keyword" in result.output.lower()
    assert "motor torque" in result.output.lower()


def test_why_unknown_result_id_is_helpful(tmp_path) -> None:
    config_path, db_path = _indexed_search_fixture(tmp_path)

    result = runner.invoke(
        app,
        ["why", "99", "motor torque", "--config", str(config_path), "--database", str(db_path)],
    )

    assert result.exit_code != 0
    assert "No latest search result found for ID 99" in result.output


def test_keyword_why_does_not_use_semantic_dependencies(tmp_path, mocker) -> None:
    config_path, db_path = _indexed_search_fixture(tmp_path)
    search_result = runner.invoke(
        app,
        ["search", "motor torque", "--mode", "keyword", "--config", str(config_path), "--database", str(db_path)],
    )
    assert search_result.exit_code == 0
    mocked_embedder = mocker.patch("kgfs.search.modes.semantic.get_embedder")

    result = runner.invoke(
        app,
        [
            "why",
            "1",
            "motor torque",
            "--mode",
            "keyword",
            "--config",
            str(config_path),
            "--database",
            str(db_path),
        ],
    )

    assert result.exit_code == 0
    mocked_embedder.assert_not_called()
