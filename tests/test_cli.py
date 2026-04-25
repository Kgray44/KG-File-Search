from typer.main import get_command
from typer.testing import CliRunner

from kgfs.cli import app

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
