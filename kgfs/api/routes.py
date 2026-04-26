"""Routes for the local-only KGFS JSON API."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse

from kgfs.api.auth import APIAuthSettings, require_api_token
from kgfs.api.models import APIHealth, APIResult, APISearchResponse
from kgfs.core.platform_utils import open_file, reveal_file
from kgfs.db import get_database_stats
from kgfs.db.latest_results import get_latest_result_path, save_latest_results
from kgfs.intelligence.export import export_metadata
from kgfs.intelligence.graph import build_topic_graph
from kgfs.intelligence.health import build_health_report
from kgfs.search import SearchContext, SearchFilters, SearchModeError, SearchOptions, build_default_search_registry
from kgfs.search.deep import deep_search
from kgfs.search.research import research_query
from kgfs.workflows.collections import get_collection_items, list_collections
from kgfs.workflows.projects import get_project_items, list_projects
from kgfs.workflows.tags import list_all_tags, list_tagged_files


def build_router(runtime: Callable, auth_settings: APIAuthSettings):
    router = APIRouter()

    def auth_dependency(authorization: str | None = Header(default=None)) -> None:
        require_api_token(auth_settings, authorization)

    auth = Depends(auth_dependency)

    @router.get("/health", dependencies=[auth])
    def health():
        _, database, config, conn = runtime()
        try:
            stats = get_database_stats(conn, database)
            return APIHealth(
                local_only=True,
                file_actions_enabled=config.api.allow_file_actions,
                indexed_files=int(stats["total_files"]),
                schema_version=stats["schema_version"],
            )
        finally:
            conn.close()

    @router.get("/status", dependencies=[auth])
    def status():
        _, database, config, conn = runtime()
        try:
            health_report = build_health_report(conn, config, database_path=database)
            return health_report.to_dict()
        finally:
            conn.close()

    @router.get("/search", dependencies=[auth])
    def search_api(
        q: str,
        mode: str = "auto",
        limit: int = 10,
        ext: str = "",
        folder: str = "",
        after: str = "",
        before: str = "",
        failed_only: bool = False,
    ):
        _, _, config, conn = runtime()
        try:
            filters = SearchFilters(
                extensions=[ext] if ext else None,
                folder=folder or None,
                after=after or None,
                before=before or None,
                failed_only=failed_only,
            )
            try:
                options = SearchOptions(mode=mode, limit=max(1, min(limit, 100)), filters=filters)
                execution = build_default_search_registry().search(q, options, SearchContext(conn=conn, config=config))
            except SearchModeError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            save_latest_results(conn, q, execution.results)
            return APISearchResponse(
                query=q,
                mode_requested=execution.mode_requested.value,
                mode_used=execution.mode_used.value,
                warnings=execution.warnings,
                results=[_api_result(result) for result in execution.results],
            )
        finally:
            conn.close()

    @router.get("/deep", dependencies=[auth])
    def deep_api(q: str, limit: int = 10, mode: str = "auto"):
        _, _, config, conn = runtime()
        try:
            report = deep_search(conn, q, config, limit=limit, mode=mode)
            return {
                "query": q,
                "variants": report.variants,
                "followups": report.followups,
                "results": [_api_result(result) for result in report.results],
            }
        finally:
            conn.close()

    @router.get("/research", dependencies=[auth])
    def research_api(q: str, limit: int = 10, mode: str = "auto"):
        _, _, config, conn = runtime()
        try:
            brief = research_query(conn, q, config, limit=limit, mode=mode)
            return {
                "query": q,
                "citations": brief.citations,
                "related_terms": brief.related_terms,
                "followups": brief.followups,
                "gaps": brief.gaps,
                "results": [_api_result(result) for result in brief.results],
            }
        finally:
            conn.close()

    @router.get("/file/{file_id}", dependencies=[auth])
    def file_api(file_id: int):
        _, _, _, conn = runtime()
        try:
            row = conn.execute(
                """
                SELECT id, file_name, path, extension, size, modified_time, extraction_source
                FROM files
                WHERE id = ?
                """,
                (file_id,),
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="File is not indexed.")
            return dict(row)
        finally:
            conn.close()

    @router.get("/collections", dependencies=[auth])
    def collections_api():
        _, _, _, conn = runtime()
        try:
            return [collection.__dict__ for collection in list_collections(conn)]
        finally:
            conn.close()

    @router.get("/collections/{name}", dependencies=[auth])
    def collection_api(name: str):
        _, _, _, conn = runtime()
        try:
            return [_workflow_item_response(item) for item in get_collection_items(conn, name)]
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        finally:
            conn.close()

    @router.get("/tags", dependencies=[auth])
    def tags_api(tag: str = ""):
        _, _, _, conn = runtime()
        try:
            if tag:
                return [_api_result(result) for result in list_tagged_files(conn, tag)]
            return list_all_tags(conn)
        finally:
            conn.close()

    @router.get("/projects", dependencies=[auth])
    def projects_api(name: str = ""):
        _, _, _, conn = runtime()
        try:
            if name:
                return [_workflow_item_response(item) for item in get_project_items(conn, name)]
            return [project.__dict__ for project in list_projects(conn)]
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        finally:
            conn.close()

    @router.get("/graph", dependencies=[auth])
    def graph_api(q: str):
        _, _, config, conn = runtime()
        try:
            graph = build_topic_graph(conn, q, config)
            return {
                "query": graph.query,
                "nodes": [node.__dict__ for node in graph.nodes],
                "edges": [edge.__dict__ for edge in graph.edges],
                "warnings": graph.warnings,
            }
        finally:
            conn.close()

    @router.get("/metadata/export", dependencies=[auth])
    def metadata_export_api():
        _, _, _, conn = runtime()
        try:
            return JSONResponse(export_metadata(conn))
        finally:
            conn.close()

    @router.post("/open/{result_id}", dependencies=[auth])
    def open_api(result_id: int):
        return _file_action(runtime, result_id, action="open")

    @router.post("/reveal/{result_id}", dependencies=[auth])
    def reveal_api(result_id: int):
        return _file_action(runtime, result_id, action="reveal")

    return router


def _api_result(result) -> APIResult:
    source = str(result.metadata.get("extraction_source", "") if result.metadata else "")
    return APIResult(
        result_id=result.result_id,
        file_id=result.file_id,
        file_name=result.file_name,
        path=str(result.path),
        extension=result.extension,
        score=float(result.score),
        snippet=result.snippet,
        mode=str(result.mode or ""),
        source=source or None,
    )


def _workflow_item_response(item) -> dict:
    return {
        "id": item.id,
        "file_id": item.file_id,
        "result_id": item.result_id,
        "file_name": item.file_name,
        "path": str(item.path),
        "extension": item.extension,
        "modified_time": item.modified_time,
        "note": item.note,
        "role": item.role,
    }


def _file_action(runtime: Callable, result_id: int, *, action: str):
    _, _, config, conn = runtime()
    try:
        if not config.api.allow_file_actions:
            raise HTTPException(status_code=403, detail="KGFS API file actions are disabled by config.")
        path = get_latest_result_path(conn, result_id)
    finally:
        conn.close()
    if path is None:
        raise HTTPException(status_code=404, detail="Unknown latest result ID.")
    if action == "open":
        open_file(Path(path))
    else:
        reveal_file(Path(path))
    return {"ok": True, "result_id": result_id, "action": action}
