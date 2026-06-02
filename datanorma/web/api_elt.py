"""REST API v1: source, destination, connection (доменная модель Фазы 4)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.engine import Connection

from datanorma.destinations.base import WriteMode
from datanorma.destinations.registry import destination_check, destination_write
from datanorma.resources.paths import DataPathsResource
from datanorma.sources.registry import create_source
from datanorma.web.audit_repo import record_audit_event
from datanorma.web.deps import (
    WorkspacePrincipal,
    get_conn,
    get_engine_cached,
    require_permission,
    resolve_actor_user_id,
)
from datanorma.web.permission_catalog import (
    PERM_CONNECTION_CREATE,
    PERM_CONNECTION_DELETE,
    PERM_CONNECTION_READ,
    PERM_CONNECTION_SYNC_RUN,
    PERM_CONNECTION_UPDATE,
    PERM_DESTINATION_CREATE,
    PERM_DESTINATION_DELETE,
    PERM_DESTINATION_READ,
    PERM_DESTINATION_UPDATE,
    PERM_SOURCE_CREATE,
    PERM_SOURCE_DELETE,
    PERM_SOURCE_READ,
    PERM_SOURCE_UPDATE,
)
from datanorma.web.permission_service import (
    ensure_owner_manage_grant,
    filter_rows_by_visibility,
)
from datanorma.web.request_audit import client_ip, client_user_agent
from datanorma.web.google_oauth import register_google_oauth_routes
from datanorma.web.elt_repo import (
    EltRepoError,
    create_connection_row,
    create_destination_row,
    create_source_row,
    delete_connection_row,
    delete_destination_row,
    delete_source_row,
    get_connection,
    get_destination,
    get_source,
    list_connections,
    list_destinations,
    list_sources,
    patch_connection_row,
    public_connection_payload,
    public_destination_payload,
    public_source_payload,
    save_connection_stream_rules,
    touch_destination_checked,
    touch_source_checked,
    update_connection_row,
    update_destination_row,
    update_source_row,
)
from datanorma.web.connector_schema_meta import connector_schema_meta
from datanorma.web.mapping_profiles import MappingProfileError, resolve_workspace_id
from datanorma.web.sync_launch import (
    build_sync_audit_payload,
    launch_sync_run_via_dagster,
    run_sync_inline_fallback,
)
from datanorma.web.sync_runs import (
    SyncRunError,
    create_sync_run,
    mark_sync_run_failed,
)
from sqlalchemy import text


def _audit_elt(
    conn: Connection,
    request: Request | None,
    user: WorkspacePrincipal,
    *,
    workspace_id: int,
    action: str,
    resource_type: str | None,
    resource_id: str | None,
    result: str = "success",
    payload: dict[str, Any] | None = None,
) -> None:
    record_audit_event(
        get_engine_cached(),
        workspace_id=workspace_id,
        actor_user_id=user.user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        result=result,
        payload=payload,
        ip_address=client_ip(request),
        user_agent=client_user_agent(request),
    )


def get_elt_workspace_id(conn: Connection, principal: WorkspacePrincipal, workspace_code: str = "main") -> int:
    """Публичная обёртка: workspace из principal (X-Workspace-Id)."""
    _ = workspace_code
    return principal.workspace_id


class SourceCreateBody(BaseModel):
    workspace_code: str = Field(default="main", min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    connector_code: str = Field(min_length=1, max_length=64)
    config: dict[str, Any] = Field(default_factory=dict)


class SourcePatchBody(BaseModel):
    workspace_code: str = Field(default="main", min_length=1, max_length=64)
    name: str | None = Field(default=None, max_length=255)
    connector_code: str | None = Field(default=None, max_length=64)
    config: dict[str, Any] | None = None
    status: str | None = Field(default=None, max_length=32)


class DestinationCreateBody(BaseModel):
    workspace_code: str = Field(default="main", min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    connector_code: str = Field(min_length=1, max_length=64)
    config: dict[str, Any] = Field(default_factory=dict)


class DestinationPatchBody(BaseModel):
    workspace_code: str = Field(default="main", min_length=1, max_length=64)
    name: str | None = Field(default=None, max_length=255)
    connector_code: str | None = Field(default=None, max_length=64)
    config: dict[str, Any] | None = None
    status: str | None = Field(default=None, max_length=32)


class DestinationWriteBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    workspace_code: str = Field(default="main", min_length=1, max_length=64)
    stream_name: str = Field(min_length=1, max_length=128)
    records: list[dict[str, Any]] = Field(default_factory=list)
    stream_schema: dict[str, Any] = Field(default_factory=dict, alias="schema")
    mode: str = Field(
        default="append",
        pattern="^(append|full_refresh|upsert|replace_table)$",
    )


class ConnectionStreamBody(BaseModel):
    stream_name: str = Field(min_length=1, max_length=128)
    sync_mode: str = Field(default="full_refresh", pattern="^(full_refresh|incremental)$")
    destination_sync_mode: str | None = Field(
        default=None,
        pattern="^(append|overwrite|append_dedup|refresh_overwrite|refresh_append)$",
    )
    cursor_field: str | None = Field(default=None, max_length=256)
    primary_key: str | None = Field(default=None, max_length=512)
    is_enabled: bool = True
    mapping_profile_id: int | None = None


class ConnectionColumnRuleBody(BaseModel):
    source_field: str = Field(min_length=1, max_length=256)
    target_field: str = Field(min_length=1, max_length=256)
    type: str = Field(default="string", max_length=64)
    required: bool = False
    entity: str | None = Field(default=None, max_length=128)


class ConnectionCreateBody(BaseModel):
    workspace_code: str = Field(default="main", min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    source_id: int = Field(ge=1)
    destination_id: int = Field(ge=1)
    schedule_cron: str | None = Field(default=None, max_length=128)
    timezone: str = Field(default="UTC", max_length=64)
    streams: list[ConnectionStreamBody] = Field(default_factory=list)
    column_rules: list[ConnectionColumnRuleBody] = Field(default_factory=list)
    wizard_meta: dict[str, Any] | None = None


class ConnectionPatchBody(BaseModel):
    workspace_code: str = Field(default="main", min_length=1, max_length=64)
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    status: str | None = Field(default=None, max_length=32)
    schedule_cron: str | None = Field(default=None, max_length=128)
    timezone: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None


def register_elt_routes(v1: APIRouter) -> None:
    @v1.get("/sources")
    def elt_sources_list(
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_SOURCE_READ))],
        conn: Annotated[Connection, Depends(get_conn)],
        workspace_code: str = "main",
    ) -> dict[str, Any]:
        _ = workspace_code
        wid = principal.workspace_id
        rows = [public_source_payload(r) for r in list_sources(conn, workspace_id=wid)]
        rows = filter_rows_by_visibility(principal.auth_ctx, conn, resource_type="source", rows=rows)
        return {"items": rows}

    @v1.post("/sources", status_code=status.HTTP_201_CREATED)
    def elt_sources_create(
        body: SourceCreateBody,
        request: Request,
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_SOURCE_CREATE))],
        conn: Annotated[Connection, Depends(get_conn)],
    ) -> dict[str, Any]:
        wid = principal.workspace_id
        row = create_source_row(
            conn,
            workspace_id=wid,
            name=body.name,
            connector_code=body.connector_code,
            config=body.config,
            created_by=principal.user.username,
            created_by_user_id=principal.user_id,
        )
        pl = public_source_payload(row)
        ensure_owner_manage_grant(
            conn,
            workspace_id=wid,
            resource_type="source",
            resource_id=int(pl["id"]),
            owner_user_id=principal.user_id,
        )
        _audit_elt(
            conn,
            request,
            principal,
            workspace_id=wid,
            action="source_create",
            resource_type="source",
            resource_id=str(pl.get("id")),
            payload={"name": body.name, "connector_code": body.connector_code},
        )
        return {"item": pl}

    @v1.get("/sources/{source_id}")
    def elt_sources_get(
        source_id: int,
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_SOURCE_READ, resource_type="source"))],
        conn: Annotated[Connection, Depends(get_conn)],
        workspace_code: str = "main",
    ) -> dict[str, Any]:
        wid = principal.workspace_id
        row = get_source(conn, workspace_id=wid, source_id=source_id)
        if row is None:
            raise HTTPException(status_code=404, detail={"error_code": "source_not_found"})
        return {"item": public_source_payload(row)}

    @v1.patch("/sources/{source_id}")
    def elt_sources_patch(
        source_id: int,
        body: SourcePatchBody,
        request: Request,
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_SOURCE_UPDATE, resource_type="source"))],
        conn: Annotated[Connection, Depends(get_conn)],
    ) -> dict[str, Any]:
        wid = principal.workspace_id
        row = update_source_row(
            conn,
            workspace_id=wid,
            source_id=source_id,
            name=body.name,
            connector_code=body.connector_code,
            config=body.config,
            status=body.status,
        )
        if row is None:
            raise HTTPException(status_code=404, detail={"error_code": "source_not_found"})
        pl = public_source_payload(row)
        _audit_elt(
            conn,
            request,
            principal,
            workspace_id=wid,
            action="source_update",
            resource_type="source",
            resource_id=str(source_id),
            payload={"name": pl.get("name")},
        )
        return {"item": pl}

    @v1.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
    def elt_sources_delete(
        source_id: int,
        request: Request,
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_SOURCE_DELETE, resource_type="source"))],
        conn: Annotated[Connection, Depends(get_conn)],
        workspace_code: str = "main",
    ) -> Response:
        wid = principal.workspace_id
        n = conn.execute(
            text("SELECT COUNT(*) FROM connection WHERE source_id = :sid AND workspace_id = :wid"),
            {"sid": source_id, "wid": wid},
        ).scalar_one()
        if int(n) > 0:
            raise HTTPException(
                status_code=409,
                detail={"error_code": "source_in_use", "message": "Источник используется в connection"},
            )
        if not delete_source_row(conn, workspace_id=wid, source_id=source_id):
            raise HTTPException(status_code=404, detail={"error_code": "source_not_found"})
        _audit_elt(
            conn,
            request,
            principal,
            workspace_id=wid,
            action="source_delete",
            resource_type="source",
            resource_id=str(source_id),
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @v1.post("/sources/{source_id}/check")
    def elt_sources_check(
        source_id: int,
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_SOURCE_READ, resource_type="source"))],
        conn: Annotated[Connection, Depends(get_conn)],
        workspace_code: str = "main",
    ) -> dict[str, Any]:
        wid = principal.workspace_id
        row = get_source(conn, workspace_id=wid, source_id=source_id)
        if row is None:
            raise HTTPException(status_code=404, detail={"error_code": "source_not_found"})
        cfg = public_source_payload(row)["config"]
        cc = str(row["connector_code"]).strip().lower().replace("-", "_")
        paths = DataPathsResource()
        yaml_text = cfg.get("yaml_body") or cfg.get("connector_builder_yaml")
        if cc == "rest_builder" and not (yaml_text and str(yaml_text).strip()):
            raise HTTPException(
                status_code=422,
                detail={"error_code": "config_invalid", "message": "Для rest_builder нужен config.yaml_body"},
            )
        try:
            src = create_source(
                cc,
                paths=paths,
                yaml_text=str(yaml_text) if yaml_text else None,
                source_config=cfg,
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail={"error_code": "unknown_connector", "message": str(e)}) from e
        cr = src.check()
        touch_source_checked(conn, workspace_id=wid, source_id=source_id)
        return {"ok": cr.ok, "message": cr.message, "details": cr.details}

    @v1.post("/sources/{source_id}/discover")
    def elt_sources_discover(
        source_id: int,
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_SOURCE_READ, resource_type="source"))],
        conn: Annotated[Connection, Depends(get_conn)],
        workspace_code: str = "main",
    ) -> dict[str, Any]:
        wid = principal.workspace_id
        row = get_source(conn, workspace_id=wid, source_id=source_id)
        if row is None:
            raise HTTPException(status_code=404, detail={"error_code": "source_not_found"})
        cfg = public_source_payload(row)["config"]
        cc = str(row["connector_code"]).strip().lower().replace("-", "_")
        paths = DataPathsResource()
        yaml_text = cfg.get("yaml_body") or cfg.get("connector_builder_yaml")
        if cc == "rest_builder" and not (yaml_text and str(yaml_text).strip()):
            raise HTTPException(
                status_code=422,
                detail={"error_code": "config_invalid", "message": "Для rest_builder нужен config.yaml_body"},
            )
        try:
            src = create_source(
                cc,
                paths=paths,
                yaml_text=str(yaml_text) if yaml_text else None,
                source_config=cfg,
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail={"error_code": "unknown_connector", "message": str(e)}) from e
        catalog = src.discover()
        stream_count = len(catalog.streams or [])
        meta = connector_schema_meta(cc, discovered_stream_count=stream_count)
        return {
            "catalog": catalog.model_dump(mode="json"),
            "layout": meta["layout"],
            "entity_labels": meta["entity_labels"],
            "stream_defaults": meta["stream_defaults"],
        }

    @v1.get("/destinations")
    def elt_destinations_list(
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_DESTINATION_READ))],
        conn: Annotated[Connection, Depends(get_conn)],
        workspace_code: str = "main",
    ) -> dict[str, Any]:
        wid = principal.workspace_id
        rows = [public_destination_payload(r) for r in list_destinations(conn, workspace_id=wid)]
        rows = filter_rows_by_visibility(principal.auth_ctx, conn, resource_type="destination", rows=rows)
        return {"items": rows}

    @v1.post("/destinations", status_code=status.HTTP_201_CREATED)
    def elt_destinations_create(
        body: DestinationCreateBody,
        request: Request,
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_DESTINATION_CREATE))],
        conn: Annotated[Connection, Depends(get_conn)],
    ) -> dict[str, Any]:
        wid = principal.workspace_id
        row = create_destination_row(
            conn,
            workspace_id=wid,
            name=body.name,
            connector_code=body.connector_code,
            config=body.config,
            created_by=principal.user.username,
            created_by_user_id=principal.user_id,
        )
        pl = public_destination_payload(row)
        ensure_owner_manage_grant(
            conn,
            workspace_id=wid,
            resource_type="destination",
            resource_id=int(pl["id"]),
            owner_user_id=principal.user_id,
        )
        _audit_elt(
            conn,
            request,
            principal,
            workspace_id=wid,
            action="destination_create",
            resource_type="destination",
            resource_id=str(pl.get("id")),
            payload={"name": body.name, "connector_code": body.connector_code},
        )
        return {"item": pl}

    @v1.get("/destinations/{destination_id}")
    def elt_destinations_get(
        destination_id: int,
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_DESTINATION_READ, resource_type="destination"))],
        conn: Annotated[Connection, Depends(get_conn)],
        workspace_code: str = "main",
    ) -> dict[str, Any]:
        wid = principal.workspace_id
        row = get_destination(conn, workspace_id=wid, destination_id=destination_id)
        if row is None:
            raise HTTPException(status_code=404, detail={"error_code": "destination_not_found"})
        return {"item": public_destination_payload(row)}

    @v1.patch("/destinations/{destination_id}")
    def elt_destinations_patch(
        destination_id: int,
        body: DestinationPatchBody,
        request: Request,
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_DESTINATION_UPDATE, resource_type="destination"))],
        conn: Annotated[Connection, Depends(get_conn)],
    ) -> dict[str, Any]:
        wid = principal.workspace_id
        row = update_destination_row(
            conn,
            workspace_id=wid,
            destination_id=destination_id,
            name=body.name,
            connector_code=body.connector_code,
            config=body.config,
            status=body.status,
        )
        if row is None:
            raise HTTPException(status_code=404, detail={"error_code": "destination_not_found"})
        pl = public_destination_payload(row)
        _audit_elt(
            conn,
            request,
            principal,
            workspace_id=wid,
            action="destination_update",
            resource_type="destination",
            resource_id=str(destination_id),
            payload={"name": pl.get("name")},
        )
        return {"item": pl}

    @v1.delete("/destinations/{destination_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
    def elt_destinations_delete(
        destination_id: int,
        request: Request,
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_DESTINATION_DELETE, resource_type="destination"))],
        conn: Annotated[Connection, Depends(get_conn)],
        workspace_code: str = "main",
    ) -> Response:
        wid = principal.workspace_id
        n = conn.execute(
            text("SELECT COUNT(*) FROM connection WHERE destination_id = :did AND workspace_id = :wid"),
            {"did": destination_id, "wid": wid},
        ).scalar_one()
        if int(n) > 0:
            raise HTTPException(
                status_code=409,
                detail={"error_code": "destination_in_use", "message": "Приёмник используется в connection"},
            )
        if not delete_destination_row(conn, workspace_id=wid, destination_id=destination_id):
            raise HTTPException(status_code=404, detail={"error_code": "destination_not_found"})
        _audit_elt(
            conn,
            request,
            principal,
            workspace_id=wid,
            action="destination_delete",
            resource_type="destination",
            resource_id=str(destination_id),
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @v1.post("/destinations/{destination_id}/check")
    def elt_destinations_check(
        destination_id: int,
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_DESTINATION_READ, resource_type="destination"))],
        conn: Annotated[Connection, Depends(get_conn)],
        workspace_code: str = "main",
    ) -> dict[str, Any]:
        wid = principal.workspace_id
        row = get_destination(conn, workspace_id=wid, destination_id=destination_id)
        if row is None:
            raise HTTPException(status_code=404, detail={"error_code": "destination_not_found"})
        cc = str(row["connector_code"]).strip().lower().replace("-", "_")
        cfg = public_destination_payload(row)["config"]
        try:
            cr = destination_check(cc, cfg)
        except ValueError as e:
            touch_destination_checked(conn, workspace_id=wid, destination_id=destination_id)
            raise HTTPException(
                status_code=422,
                detail={"error_code": "unknown_destination", "message": str(e)},
            ) from e
        touch_destination_checked(conn, workspace_id=wid, destination_id=destination_id)
        return {"ok": cr.ok, "message": cr.message, "details": cr.details}

    @v1.post("/destinations/{destination_id}/write")
    def elt_destinations_write(
        destination_id: int,
        body: DestinationWriteBody,
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_DESTINATION_UPDATE, resource_type="destination"))],
        conn: Annotated[Connection, Depends(get_conn)],
    ) -> dict[str, Any]:
        wid = principal.workspace_id
        row = get_destination(conn, workspace_id=wid, destination_id=destination_id)
        if row is None:
            raise HTTPException(status_code=404, detail={"error_code": "destination_not_found"})
        cc = str(row["connector_code"]).strip().lower().replace("-", "_")
        cfg = public_destination_payload(row)["config"]
        wm = WriteMode(body.mode)
        try:
            wr = destination_write(
                cc,
                stream_name=body.stream_name,
                records=body.records,
                schema=body.stream_schema,
                mode=wm,
                config=cfg,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail={"error_code": "unknown_destination", "message": str(e)},
            ) from e
        if not wr.ok:
            raise HTTPException(
                status_code=422,
                detail={
                    "error_code": "destination_write_failed",
                    "message": wr.message,
                    "details": wr.details,
                },
            )
        return {
            "ok": True,
            "message": wr.message,
            "rows_written": wr.rows_written,
            "details": wr.details,
        }

    @v1.get("/connections")
    def elt_connections_list(
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_CONNECTION_READ))],
        conn: Annotated[Connection, Depends(get_conn)],
        workspace_code: str = "main",
    ) -> dict[str, Any]:
        wid = principal.workspace_id
        rows = list_connections(conn, workspace_id=wid)
        rows = filter_rows_by_visibility(principal.auth_ctx, conn, resource_type="connection", rows=rows)
        return {"items": [public_connection_payload(conn, r) for r in rows]}

    @v1.post("/connections", status_code=status.HTTP_201_CREATED)
    def elt_connections_create(
        body: ConnectionCreateBody,
        request: Request,
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_CONNECTION_CREATE))],
        conn: Annotated[Connection, Depends(get_conn)],
    ) -> dict[str, Any]:
        wid = principal.workspace_id
        try:
            item = create_connection_row(
                conn,
                workspace_id=wid,
                name=body.name,
                description=body.description,
                source_id=body.source_id,
                destination_id=body.destination_id,
                schedule_cron=body.schedule_cron,
                timezone=body.timezone,
                streams=[s.model_dump() for s in body.streams],
                column_rules=[c.model_dump() for c in body.column_rules],
                wizard_meta=body.wizard_meta,
                created_by=principal.user.username,
                created_by_user_id=principal.user_id,
            )
        except EltRepoError as e:
            raise HTTPException(status_code=422, detail={"error_code": "invalid_connection", "message": str(e)}) from e
        ensure_owner_manage_grant(
            conn,
            workspace_id=wid,
            resource_type="connection",
            resource_id=int(item["id"]),
            owner_user_id=principal.user_id,
        )
        _audit_elt(
            conn,
            request,
            principal,
            workspace_id=wid,
            action="connection_create",
            resource_type="connection",
            resource_id=str(item.get("id")),
            payload={"name": body.name},
        )
        return {"item": public_connection_payload(conn, item)}

    @v1.get("/connections/{connection_id}")
    def elt_connections_get(
        connection_id: int,
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_CONNECTION_READ, resource_type="connection"))],
        conn: Annotated[Connection, Depends(get_conn)],
        workspace_code: str = "main",
    ) -> dict[str, Any]:
        wid = principal.workspace_id
        row = get_connection(conn, workspace_id=wid, connection_id=connection_id)
        if row is None:
            raise HTTPException(status_code=404, detail={"error_code": "connection_not_found"})
        return {"item": public_connection_payload(conn, row)}

    @v1.patch("/connections/{connection_id}")
    def elt_connections_patch(
        connection_id: int,
        body: ConnectionPatchBody,
        request: Request,
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_CONNECTION_UPDATE, resource_type="connection"))],
        conn: Annotated[Connection, Depends(get_conn)],
    ) -> dict[str, Any]:
        wid = principal.workspace_id
        patch_fields = body.model_dump(exclude_unset=True)
        patch_fields.pop("workspace_code", None)
        row = patch_connection_row(
            conn,
            workspace_id=wid,
            connection_id=connection_id,
            fields=patch_fields,
        )
        if row is None:
            raise HTTPException(status_code=404, detail={"error_code": "connection_not_found"})
        _audit_elt(
            conn,
            request,
            principal,
            workspace_id=wid,
            action="connection_update",
            resource_type="connection",
            resource_id=str(connection_id),
            payload={"status": row.get("status"), "is_active": row.get("is_active")},
        )
        return {"item": row}

    @v1.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
    def elt_connections_delete(
        connection_id: int,
        request: Request,
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_CONNECTION_DELETE, resource_type="connection"))],
        conn: Annotated[Connection, Depends(get_conn)],
        workspace_code: str = "main",
    ) -> Response:
        wid = principal.workspace_id
        if not delete_connection_row(conn, workspace_id=wid, connection_id=connection_id):
            raise HTTPException(status_code=404, detail={"error_code": "connection_not_found"})
        _audit_elt(
            conn,
            request,
            principal,
            workspace_id=wid,
            action="connection_delete",
            resource_type="connection",
            resource_id=str(connection_id),
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @v1.post("/connections/{connection_id}/trigger", status_code=status.HTTP_202_ACCEPTED)
    def elt_connections_trigger(
        connection_id: int,
        request: Request,
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_CONNECTION_SYNC_RUN, resource_type="connection"))],
        conn: Annotated[Connection, Depends(get_conn)],
        workspace_code: str = "main",
    ) -> dict[str, Any]:
        wid = principal.workspace_id
        crow = conn.execute(
            text(
                "SELECT id, source_id FROM connection WHERE id = :id AND workspace_id = :wid"
            ),
            {"id": connection_id, "wid": wid},
        ).mappings().first()
        if crow is None:
            raise HTTPException(status_code=404, detail={"error_code": "connection_not_found"})
        src_row = get_source(conn, workspace_id=wid, source_id=int(crow["source_id"]))
        if src_row is None:
            raise HTTPException(status_code=404, detail={"error_code": "source_not_found"})
        integration_code = str(src_row["connector_code"]).strip()

        row = create_sync_run(
            conn,
            connection_id=None,
            domain_connection_id=connection_id,
            integration_code=integration_code,
            stream_name="*",
            triggered_by=principal.user.username,
            note=None,
            workspace_id=wid,
        )
        run_id = int(row["id"])
        try:
            row = launch_sync_run_via_dagster(
                conn=conn,
                run_id=run_id,
                integration_code=integration_code,
                stream_name="*",
                triggered_by=principal.user.username,
            )
            _audit_elt(
                conn,
                request,
                principal,
                workspace_id=wid,
                action="trigger_sync",
                resource_type="sync_run",
                resource_id=str(run_id),
                payload=build_sync_audit_payload(
                    execution_mode="dagster",
                    connection_id=connection_id,
                    integration_code=integration_code,
                    dagster_run_id=row.get("dagster_run_id"),
                ),
            )
            return {
                "status": "accepted",
                "message": "Sync run accepted and launched",
                "run_id": run_id,
                "sync_run": row,
                "execution_mode": "dagster",
            }
        except SyncRunError as dagster_exc:
            try:
                row, summary = run_sync_inline_fallback(
                    conn=conn,
                    run_id=run_id,
                    workspace_id=wid,
                    domain_connection_id=connection_id,
                    dagster_error=dagster_exc,
                )
            except Exception as inline_exc:
                row = mark_sync_run_failed(conn, run_id=run_id, message=str(inline_exc))
                _audit_elt(
                    conn,
                    request,
                    principal,
                    workspace_id=wid,
                    action="trigger_sync",
                    resource_type="sync_run",
                    resource_id=str(run_id),
                    result="failure",
                    payload=build_sync_audit_payload(
                        execution_mode="inline_fallback",
                        connection_id=connection_id,
                        integration_code=integration_code,
                        dagster_error=str(dagster_exc),
                        error=str(inline_exc),
                    ),
                )
                raise HTTPException(
                    status_code=502,
                    detail={
                        "error_code": "elt_sync_failed",
                        "error_message": str(inline_exc),
                        "run_id": run_id,
                    },
                ) from inline_exc

            _audit_elt(
                conn,
                request,
                principal,
                workspace_id=wid,
                action="trigger_sync",
                resource_type="sync_run",
                resource_id=str(run_id),
                payload=build_sync_audit_payload(
                    execution_mode="inline_fallback",
                    connection_id=connection_id,
                    integration_code=integration_code,
                    dagster_error=str(dagster_exc),
                    elt_summary=summary or {},
                ),
            )
            return {
                "status": "accepted",
                "message": "Sync completed via inline fallback",
                "run_id": run_id,
                "sync_run": row,
                "summary": summary or {},
                "execution_mode": "inline_fallback",
            }
        except Exception as exc:
            row = mark_sync_run_failed(conn, run_id=run_id, message=str(exc))
            _audit_elt(
                conn,
                request,
                principal,
                workspace_id=wid,
                action="trigger_sync",
                resource_type="sync_run",
                resource_id=str(run_id),
                result="failure",
                payload=build_sync_audit_payload(
                    execution_mode="dagster",
                    connection_id=connection_id,
                    integration_code=integration_code,
                    error=str(exc),
                ),
            )
            raise HTTPException(
                status_code=502,
                detail={
                    "error_code": "dagster_launch_failed",
                    "error_message": str(exc),
                    "run_id": run_id,
                },
            ) from exc

    @v1.post("/connections/{connection_id}/pause")
    def elt_connections_pause(
        connection_id: int,
        request: Request,
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_CONNECTION_UPDATE, resource_type="connection"))],
        conn: Annotated[Connection, Depends(get_conn)],
        workspace_code: str = "main",
    ) -> dict[str, Any]:
        wid = principal.workspace_id
        row = update_connection_row(
            conn,
            workspace_id=wid,
            connection_id=connection_id,
            is_active=False,
            status="paused",
        )
        if row is None:
            raise HTTPException(status_code=404, detail={"error_code": "connection_not_found"})
        _audit_elt(
            conn,
            request,
            principal,
            workspace_id=wid,
            action="connection_pause",
            resource_type="connection",
            resource_id=str(connection_id),
        )
        return {"item": row}

    @v1.post("/connections/{connection_id}/resume")
    def elt_connections_resume(
        connection_id: int,
        request: Request,
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(PERM_CONNECTION_UPDATE, resource_type="connection"))],
        conn: Annotated[Connection, Depends(get_conn)],
        workspace_code: str = "main",
    ) -> dict[str, Any]:
        wid = principal.workspace_id
        row = update_connection_row(
            conn,
            workspace_id=wid,
            connection_id=connection_id,
            is_active=True,
            status="active",
        )
        if row is None:
            raise HTTPException(status_code=404, detail={"error_code": "connection_not_found"})
        _audit_elt(
            conn,
            request,
            principal,
            workspace_id=wid,
            action="connection_resume",
            resource_type="connection",
            resource_id=str(connection_id),
        )
        return {"item": row}

    register_google_oauth_routes(v1)
