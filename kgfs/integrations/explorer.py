"""Explorer context-menu scaffold export."""

from __future__ import annotations

from pathlib import Path


def scaffold_explorer(output: Path) -> list[Path]:
    output.mkdir(parents=True, exist_ok=True)
    readme = output / "README.md"
    reg = output / "kgfs-explorer-template.reg"
    readme.write_text(
        "# KGFS Explorer Scaffold\n\nNo registry changes are applied automatically. Inspect the `.reg` template before using it manually.\n",
        encoding="utf-8",
    )
    reg.write_text(
        """Windows Registry Editor Version 5.00

; Template only. Edit paths before importing manually.
; Runs a local KGFS search from Explorer context-menu experiments.
""",
        encoding="utf-8",
    )
    return [readme, reg]
