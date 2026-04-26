"""Check that CLI, config, and schema surfaces are documented."""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from typer.main import get_command

from kgfs.cli import app
from kgfs.core.config import KGFSConfig
from kgfs.db.schema import initialize_database


@dataclass(frozen=True)
class DocsConsistencyReport:
    missing_cli_commands: list[str] = field(default_factory=list)
    missing_config_sections: list[str] = field(default_factory=list)
    missing_schema_tables: list[str] = field(default_factory=list)
    cli_commands: list[str] = field(default_factory=list)
    config_sections: list[str] = field(default_factory=list)
    schema_tables: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.missing_cli_commands or self.missing_config_sections or self.missing_schema_tables)

    def to_message(self) -> str:
        parts: list[str] = []
        if self.missing_cli_commands:
            parts.append("Missing CLI docs: " + ", ".join(f"kgfs {item}" for item in self.missing_cli_commands))
        if self.missing_config_sections:
            parts.append("Missing settings docs: " + ", ".join(f"`{item}`" for item in self.missing_config_sections))
        if self.missing_schema_tables:
            parts.append("Missing data-model docs: " + ", ".join(f"`{item}`" for item in self.missing_schema_tables))
        return "\n".join(parts) if parts else "Docs consistency checks passed."


def check_docs_consistency(root: Path) -> DocsConsistencyReport:
    docs_cli = (root / "docs" / "cli.md").read_text(encoding="utf-8")
    docs_settings = (root / "docs" / "settings.md").read_text(encoding="utf-8")
    docs_data_model = (root / "docs" / "data-model.md").read_text(encoding="utf-8")

    cli_commands = collect_cli_commands()
    config_sections = collect_config_sections()
    schema_tables = collect_schema_tables()

    return DocsConsistencyReport(
        missing_cli_commands=[command for command in cli_commands if f"kgfs {command}" not in docs_cli],
        missing_config_sections=[section for section in config_sections if f"`{section}`" not in docs_settings],
        missing_schema_tables=[table for table in schema_tables if f"`{table}`" not in docs_data_model],
        cli_commands=cli_commands,
        config_sections=config_sections,
        schema_tables=schema_tables,
    )


def collect_cli_commands() -> list[str]:
    root_command = get_command(app)
    commands: list[str] = []

    def walk(command, prefix: tuple[str, ...] = ()) -> None:
        children = getattr(command, "commands", None)
        if not children:
            return
        for name, child in sorted(children.items()):
            path = (*prefix, name)
            commands.append(" ".join(path))
            walk(child, path)

    walk(root_command)
    return commands


def collect_config_sections() -> list[str]:
    return sorted(KGFSConfig.model_fields)


def collect_schema_tables() -> list[str]:
    conn = sqlite3.connect(":memory:")
    try:
        initialize_database(conn)
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name").fetchall()
    finally:
        conn.close()
    return [
        str(row[0])
        for row in rows
        if not str(row[0]).startswith("sqlite_") and not str(row[0]).startswith("files_fts_")
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check KGFS docs against CLI/config/schema surfaces.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root.")
    args = parser.parse_args(argv)
    report = check_docs_consistency(args.root)
    print(report.to_message())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
