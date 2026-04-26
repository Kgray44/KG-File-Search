"""Small serializable models for the local KGFS API."""

from __future__ import annotations

from pydantic import BaseModel


class APIHealth(BaseModel):
    ok: bool = True
    local_only: bool = True
    file_actions_enabled: bool = False
    indexed_files: int = 0
    schema_version: int | str = "unknown"


class APIResult(BaseModel):
    result_id: int
    file_id: int
    file_name: str
    path: str
    extension: str
    score: float
    snippet: str
    mode: str | None = None
    source: str | None = None


class APISearchResponse(BaseModel):
    query: str
    mode_requested: str
    mode_used: str
    warnings: list[str]
    results: list[APIResult]
