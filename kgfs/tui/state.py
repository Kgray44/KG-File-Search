"""Small TUI state containers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TUIState:
    query: str = ""
    mode: str = "auto"
    selected_result_id: int | None = None
