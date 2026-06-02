"""API workspace: список, создание, участники, права."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.engine import Connection

from datanorma.web.deps import (
    AuthUser,
    WorkspacePrincipal,
    WorkspacePrincipalFromPath,
    get_conn,
    get_current_user,
    resolve_actor_user_id,
)
from datanorma.web.permission_catalog import PERM_WORKSPACE_MEMBERS_MANAGE, PERM_WORKSPACE_PERMISSIONS_GRANT, catalog_payload
from datanorma.web.permission_service import effective_permissions_for_user, list_member_permissions, set_member_permissions
from datanorma.web.workspace_repo import (
    add_workspace_member,
    create_workspace,
    find_user_id_by_username,
    get_workspace,
    list_workspace_members,
    list_workspaces_for_user,
    remove_workspace_member,
)


class WorkspaceCreateBody(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=255)


class MemberAddBody(BaseModel):
    username: str = Field(min_length=1, max_length=128)


class MemberPermissionsBody(BaseModel):
    permissions: list[str] = Field(default_factory=list)


def register_workspace_routes(v1: APIRouter) -> None:
    @v1.get("/permissions/catalog")
    def permissions_catalog() -> dict[str, Any]:
        return {"items": catalog_payload()}

    @v1.get("/workspaces")
    def workspaces_list(
        conn: Annotated[Connection, Depends(get_conn)],
        user: Annotated[AuthUser, Depends(get_current_user)],
    ) -> dict[str, Any]:
        uid = resolve_actor_user_id(conn, user)
        if uid is None:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        rows = list_workspaces_for_user(conn, user_id=uid)
        items = []
        for r in rows:
            is_admin, perms = effective_permissions_for_user(
                conn, user_id=uid, workspace_id=int(r["id"])
            )
            items.append(
                {
                    "id": r["id"],
                    "code": r["code"],
                    "name": r["name"],
                    "is_admin": bool(r.get("is_admin")) or is_admin,
                    "permissions": perms,
                }
            )
        return {"items": items}

    @v1.post("/workspaces", status_code=status.HTTP_201_CREATED)
    def workspaces_create(
        body: WorkspaceCreateBody,
        conn: Annotated[Connection, Depends(get_conn)],
        user: Annotated[AuthUser, Depends(get_current_user)],
    ) -> dict[str, Any]:
        uid = resolve_actor_user_id(conn, user)
        if uid is None:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        try:
            row = create_workspace(
                conn,
                code=body.code,
                name=body.name,
                created_by_user_id=uid,
            )
        except Exception as exc:
            if "uq_workspace" in str(exc).lower() or "unique" in str(exc).lower():
                raise HTTPException(
                    status_code=409,
                    detail={"error_code": "workspace_code_exists", "message": "Код пространства уже занят"},
                ) from exc
            raise
        from datanorma.web.permission_catalog import ALL_PERMISSION_CODES

        return {
            "item": {
                "id": row["id"],
                "code": row["code"],
                "name": row["name"],
                "is_admin": True,
                "permissions": list(ALL_PERMISSION_CODES),
            }
        }

    @v1.get("/workspaces/{workspace_id}/members")
    def workspace_members_list(
        workspace_id: int,
        conn: Annotated[Connection, Depends(get_conn)],
        _: Annotated[WorkspacePrincipal, Depends(WorkspacePrincipalFromPath(PERM_WORKSPACE_MEMBERS_MANAGE))],
    ) -> dict[str, Any]:
        if get_workspace(conn, workspace_id=workspace_id) is None:
            raise HTTPException(status_code=404, detail={"error_code": "workspace_not_found"})
        members = list_workspace_members(conn, workspace_id=workspace_id)
        out = []
        for m in members:
            perms = list_member_permissions(conn, workspace_id=workspace_id, user_id=int(m["user_id"]))
            out.append({**m, "permissions": perms})
        return {"items": out}

    @v1.post("/workspaces/{workspace_id}/members", status_code=status.HTTP_201_CREATED)
    def workspace_members_add(
        workspace_id: int,
        body: MemberAddBody,
        conn: Annotated[Connection, Depends(get_conn)],
        _: Annotated[WorkspacePrincipal, Depends(WorkspacePrincipalFromPath(PERM_WORKSPACE_MEMBERS_MANAGE))],
    ) -> dict[str, Any]:
        if get_workspace(conn, workspace_id=workspace_id) is None:
            raise HTTPException(status_code=404, detail={"error_code": "workspace_not_found"})
        uid = find_user_id_by_username(conn, body.username)
        if uid is None:
            raise HTTPException(status_code=404, detail={"error_code": "user_not_found"})
        add_workspace_member(conn, workspace_id=workspace_id, user_id=uid)
        return {"user_id": uid, "username": body.username.strip()}

    @v1.delete(
        "/workspaces/{workspace_id}/members/{member_user_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        response_class=Response,
    )
    def workspace_members_remove(
        workspace_id: int,
        member_user_id: int,
        conn: Annotated[Connection, Depends(get_conn)],
        _: Annotated[WorkspacePrincipal, Depends(WorkspacePrincipalFromPath(PERM_WORKSPACE_MEMBERS_MANAGE))],
    ) -> Response:
        try:
            if not remove_workspace_member(conn, workspace_id=workspace_id, user_id=member_user_id):
                raise HTTPException(status_code=404, detail={"error_code": "member_not_found"})
        except ValueError as exc:
            if str(exc) == "last_admin":
                raise HTTPException(
                    status_code=409,
                    detail={"error_code": "last_admin", "message": "Нельзя удалить последнего администратора"},
                ) from exc
            raise
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @v1.get("/workspaces/{workspace_id}/members/{member_user_id}/permissions")
    def workspace_member_permissions_get(
        workspace_id: int,
        member_user_id: int,
        conn: Annotated[Connection, Depends(get_conn)],
        _: Annotated[WorkspacePrincipal, Depends(WorkspacePrincipalFromPath(PERM_WORKSPACE_PERMISSIONS_GRANT))],
    ) -> dict[str, Any]:
        perms = list_member_permissions(conn, workspace_id=workspace_id, user_id=member_user_id)
        return {"user_id": member_user_id, "permissions": perms}

    @v1.put("/workspaces/{workspace_id}/members/{member_user_id}/permissions")
    def workspace_member_permissions_put(
        workspace_id: int,
        member_user_id: int,
        body: MemberPermissionsBody,
        conn: Annotated[Connection, Depends(get_conn)],
        _: Annotated[WorkspacePrincipal, Depends(WorkspacePrincipalFromPath(PERM_WORKSPACE_PERMISSIONS_GRANT))],
    ) -> dict[str, Any]:
        set_member_permissions(
            conn,
            workspace_id=workspace_id,
            user_id=member_user_id,
            permission_codes=body.permissions,
        )
        return {"user_id": member_user_id, "permissions": body.permissions}
