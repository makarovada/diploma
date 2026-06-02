"""Object-level grants API для source / destination / connection."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.engine import Connection

from datanorma.web.deps import WorkspacePrincipal, get_conn, require_permission
from datanorma.web.permission_catalog import (
    PERM_CONNECTION_READ,
    PERM_DESTINATION_READ,
    PERM_SOURCE_READ,
)
from datanorma.web.permission_service import (
    ResourceRef,
    can_manage_resource_grants,
    create_resource_grant,
    delete_resource_grant,
    list_resource_grants,
)
from datanorma.web.elt_repo import get_connection, get_destination, get_source


class GrantCreateBody(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    level: str = Field(pattern=r"^(view|edit|manage)$")


def _ensure_resource_exists(
    conn: Connection, *, workspace_id: int, resource_type: str, resource_id: int
) -> None:
    if resource_type == "source":
        row = get_source(conn, workspace_id=workspace_id, source_id=resource_id)
    elif resource_type == "destination":
        row = get_destination(conn, workspace_id=workspace_id, destination_id=resource_id)
    elif resource_type == "connection":
        row = get_connection(conn, workspace_id=workspace_id, connection_id=resource_id)
    else:
        raise HTTPException(status_code=400, detail={"error_code": "invalid_resource_type"})
    if row is None:
        raise HTTPException(status_code=404, detail={"error_code": "resource_not_found"})


def _register_grants_for(v1: APIRouter, resource_type: str, read_perm: str) -> None:
    @v1.get(f"/{resource_type}s/{{resource_id}}/grants")
    def list_grants(
        resource_id: int,
        conn: Annotated[Connection, Depends(get_conn)],
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(read_perm, resource_type=resource_type))],
    ) -> dict[str, Any]:
        _ensure_resource_exists(
            conn, workspace_id=principal.workspace_id, resource_type=resource_type, resource_id=resource_id
        )
        items = list_resource_grants(
            conn,
            workspace_id=principal.workspace_id,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        return {"items": items}

    @v1.post(f"/{resource_type}s/{{resource_id}}/grants", status_code=status.HTTP_201_CREATED)
    def add_grant(
        resource_id: int,
        body: GrantCreateBody,
        conn: Annotated[Connection, Depends(get_conn)],
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(read_perm, resource_type=resource_type))],
    ) -> dict[str, Any]:
        _ensure_resource_exists(
            conn, workspace_id=principal.workspace_id, resource_type=resource_type, resource_id=resource_id
        )
        ref = ResourceRef(resource_type=resource_type, resource_id=resource_id)
        if not can_manage_resource_grants(principal.auth_ctx, conn, resource=ref):
            raise HTTPException(status_code=403, detail={"error_code": "grant_forbidden"})
        from datanorma.web.workspace_repo import find_user_id_by_username

        grantee_id = find_user_id_by_username(conn, body.username)
        if grantee_id is None:
            raise HTTPException(status_code=404, detail={"error_code": "user_not_found"})
        row = create_resource_grant(
            conn,
            workspace_id=principal.workspace_id,
            resource_type=resource_type,
            resource_id=resource_id,
            grantee_user_id=grantee_id,
            level=body.level,
            granted_by_user_id=principal.user_id,
        )
        return {"item": row}

    @v1.delete(
        f"/{resource_type}s/{{resource_id}}/grants/{{grantee_user_id}}",
        status_code=status.HTTP_204_NO_CONTENT,
        response_class=Response,
    )
    def remove_grant(
        resource_id: int,
        grantee_user_id: int,
        conn: Annotated[Connection, Depends(get_conn)],
        principal: Annotated[WorkspacePrincipal, Depends(require_permission(read_perm, resource_type=resource_type))],
    ) -> Response:
        ref = ResourceRef(resource_type=resource_type, resource_id=resource_id)
        if not can_manage_resource_grants(principal.auth_ctx, conn, resource=ref):
            raise HTTPException(status_code=403, detail={"error_code": "grant_forbidden"})
        if not delete_resource_grant(
            conn,
            workspace_id=principal.workspace_id,
            resource_type=resource_type,
            resource_id=resource_id,
            grantee_user_id=grantee_user_id,
        ):
            raise HTTPException(status_code=404, detail={"error_code": "grant_not_found"})
        return Response(status_code=status.HTTP_204_NO_CONTENT)


def register_resource_grant_routes(v1: APIRouter) -> None:
    _register_grants_for(v1, "source", PERM_SOURCE_READ)
    _register_grants_for(v1, "destination", PERM_DESTINATION_READ)
    _register_grants_for(v1, "connection", PERM_CONNECTION_READ)
