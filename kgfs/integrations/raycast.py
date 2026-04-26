"""Raycast scaffold export."""

from __future__ import annotations

from pathlib import Path


def export_raycast(output: Path) -> list[Path]:
    output.mkdir(parents=True, exist_ok=True)
    script = output / "kgfs-search.sh"
    readme = output / "README.md"
    script.write_text(
        """#!/usr/bin/env bash
# Raycast script command scaffold for KGFS.
# @raycast.schemaVersion 1
# @raycast.title KGFS Search
# @raycast.mode fullOutput
# @raycast.argument1 { "type": "text", "placeholder": "query" }
kgfs search "$1" --mode auto
""",
        encoding="utf-8",
    )
    readme.write_text(
        "# KGFS Raycast Scaffold\n\nImport this folder as a Raycast script command directory. It calls `kgfs search` locally.\n",
        encoding="utf-8",
    )
    return [script, readme]
