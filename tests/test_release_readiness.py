from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from kgfs.cli import app
from kgfs.version import __version__
from kgfs.database import connect_database, initialize_database

runner = CliRunner()


def test_version_command_and_global_version_option_report_same_version() -> None:
    command_result = runner.invoke(app, ["version"])
    option_result = runner.invoke(app, ["--version"])

    assert command_result.exit_code == 0
    assert option_result.exit_code == 0
    assert f"KGFS {__version__}" in command_result.output
    assert f"KGFS {__version__}" in option_result.output


def test_doctor_and_capabilities_include_version(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("indexed_folders: []\n", encoding="utf-8")
    db_path = tmp_path / "kgfs.sqlite3"

    doctor_result = runner.invoke(app, ["doctor", "--config", str(config_path), "--database", str(db_path)])
    capabilities_result = runner.invoke(
        app,
        ["capabilities", "--config", str(config_path), "--database", str(db_path)],
    )

    assert doctor_result.exit_code == 0
    assert "KGFS version" in doctor_result.output
    assert __version__ in doctor_result.output
    assert capabilities_result.exit_code == 0
    assert "KGFS version" in capabilities_result.output
    assert __version__ in capabilities_result.output


def test_quickstart_command_prints_safe_first_run_path() -> None:
    result = runner.invoke(app, ["quickstart"])

    assert result.exit_code == 0
    assert "kgfs init" in result.output
    assert "indexed_folders: []" in result.output
    assert "never indexes the whole drive" in result.output
    assert "examples/sample-corpus" in result.output


def test_capabilities_command_reports_feature_families(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
indexed_folders: []
semantic:
  enabled: false
ocr:
  enabled: false
media:
  enabled: false
ai:
  enabled: false
api:
  enabled: false
integrations:
  enabled: true
""",
        encoding="utf-8",
    )
    db_path = tmp_path / "kgfs.sqlite3"

    result = runner.invoke(
        app,
        ["capabilities", "--config", str(config_path), "--database", str(db_path)],
    )

    assert result.exit_code == 0
    for label in (
        "Keyword search",
        "Semantic search",
        "Vector backends",
        "OCR",
        "Media",
        "AI Assist",
        "Local API",
        "TUI",
        "Tray and integrations",
    ):
        assert label in result.output
    assert "sqlite_scan" in result.output


def test_release_candidate_support_files_exist_and_are_safe() -> None:
    sample_dir = Path("examples/sample-corpus")
    issue_template_dir = Path(".github/ISSUE_TEMPLATE")

    assert sample_dir.exists()
    assert (sample_dir / "README.md").exists()
    assert "artificial" in (sample_dir / "README.md").read_text(encoding="utf-8").lower()
    assert not any(path.suffix.lower() in {".sqlite", ".db", ".log"} for path in sample_dir.rglob("*"))

    for name in (
        "bug_report.yml",
        "feature_request.yml",
        "packaging_install_issue.yml",
        "search_quality_issue.yml",
        "security_privacy_concern.yml",
    ):
        assert (issue_template_dir / name).exists()


def test_db_check_reports_integrity_schema_foreign_keys_and_orphans(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("indexed_folders: []\n", encoding="utf-8")
    db_path = tmp_path / "kgfs.sqlite3"
    conn = connect_database(db_path)
    initialize_database(conn)
    conn.close()

    result = runner.invoke(
        app,
        ["db", "check", "--config", str(config_path), "--database", str(db_path)],
    )

    assert result.exit_code == 0
    assert "SQLite integrity" in result.output
    assert "ok" in result.output.lower()
    assert "Schema version" in result.output
    assert "Foreign keys" in result.output
    assert "Orphaned metadata" in result.output
    assert "Artifact sanity" in result.output


def test_db_check_reports_missing_database_without_creating_it(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("indexed_folders: []\n", encoding="utf-8")
    db_path = tmp_path / "missing.sqlite3"

    result = runner.invoke(
        app,
        ["db", "check", "--config", str(config_path), "--database", str(db_path)],
    )

    assert result.exit_code != 0
    assert "Database does not exist" in result.output
    assert not db_path.exists()


def test_docs_consistency_checker_covers_cli_settings_and_schema_docs() -> None:
    from scripts.check_docs_consistency import check_docs_consistency

    report = check_docs_consistency(Path.cwd())

    assert report.ok, report.to_message()
    assert "capabilities" in report.cli_commands
    assert "db" in report.cli_commands
    assert "media" in report.config_sections
    assert "media_text" in report.schema_tables


def test_docs_consistency_checker_detects_missing_entries(tmp_path: Path) -> None:
    from scripts.check_docs_consistency import DocsConsistencyReport

    report = DocsConsistencyReport(
        missing_cli_commands=["capabilities"],
        missing_config_sections=["media"],
        missing_schema_tables=["media_text"],
        cli_commands=["capabilities"],
        config_sections=["media"],
        schema_tables=["media_text"],
    )

    assert not report.ok
    message = report.to_message()
    assert "capabilities" in message
    assert "media" in message
    assert "media_text" in message
