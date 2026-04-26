"""Serializable models for KGFS local file intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DuplicateItem:
    file_id: int
    file_name: str
    path: Path
    size: int
    modified_time: float
    content_hash: str | None = None
    snippet: str = ""


@dataclass(frozen=True)
class DuplicateGroup:
    group_id: int
    kind: str
    items: list[DuplicateItem]
    score: float = 1.0
    evidence: list[str] = field(default_factory=list)
    reclaimable_size: int = 0


@dataclass(frozen=True)
class DuplicateReport:
    groups: list[DuplicateGroup]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VersionCandidate:
    file_id: int
    file_name: str
    path: Path
    modified_time: float
    score: float
    relationship: str
    evidence: list[str]


@dataclass(frozen=True)
class ProjectCandidate:
    id: int
    name: str
    score: float
    file_ids: list[int]
    evidence: list[str]
    accepted_project_id: int | None = None


@dataclass(frozen=True)
class GraphNode:
    id: str
    type: str
    label: str
    file_id: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    type: str
    weight: float
    evidence: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GraphResult:
    query: str | None
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class HealthIssue:
    severity: str
    title: str
    detail: str
    suggestion: str | None = None


@dataclass(frozen=True)
class HealthReport:
    summary: dict[str, Any]
    issues: list[HealthIssue]
    workflow_counts: dict[str, int]
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "issues": [issue.__dict__ for issue in self.issues],
            "workflow_counts": self.workflow_counts,
            "suggestions": self.suggestions,
        }


@dataclass(frozen=True)
class MetadataExportSummary:
    exported_items: int = 0
    restored_items: int = 0
    unmatched_items: int = 0
    path: Path | None = None
    warnings: list[str] = field(default_factory=list)
