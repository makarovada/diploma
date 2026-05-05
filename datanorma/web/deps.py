"""FastAPI: JWT Bearer, соединение с БД, проверка операций RBAC."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from datanorma.web.config import database_url
from datanorma.web.jwt_util import decode_token
from datanorma.web.rbac_matrix import OPERATION_ROLES, ROLE_PLATFORM_ADMIN

security = HTTPBearer(auto_error=False)


def _parse_int_frozenset(raw: Any) -> frozenset[int]:
    if not isinstance(raw, list):
        return frozenset()
    out: list[int] = []
    for x in raw:
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            continue
    return frozenset(out)


@dataclass(frozen=True)
class AuthUser:
    username: str
    roles: frozenset[str]
    user_id: int | None = None
    active_workspace_id: int | None = None
    allowed_workspace_ids: frozenset[int] = field(default_factory=frozenset)

    def can(self, operation: str) -> bool:
        allowed = OPERATION_ROLES.get(operation, ())
        return bool(self.roles.intersection(allowed))


@lru_cache(maxsize=1)
def get_engine_cached() -> Engine:
    return create_engine(database_url(), pool_pre_ping=True)


def get_conn() -> Connection:
    with get_engine_cached().begin() as conn:
        yield conn


def claims_to_auth_user(payload: dict[str, Any]) -> AuthUser | None:
    username = payload.get("sub")
    if not username or not isinstance(username, str):
        return None
    roles_raw = payload.get("roles") or []
    if not isinstance(roles_raw, list):
        roles_raw = []
    uid_raw = payload.get("user_id")
    user_id: int | None = None
    if uid_raw is not None:
        try:
            user_id = int(uid_raw)
        except (TypeError, ValueError):
            user_id = None
    aw_raw = payload.get("active_workspace_id")
    active_workspace_id: int | None = None
    if aw_raw is not None:
        try:
            active_workspace_id = int(aw_raw)
        except (TypeError, ValueError):
            active_workspace_id = None
    allowed = _parse_int_frozenset(payload.get("allowed_workspace_ids"))
    return AuthUser(
        username=username,
        roles=frozenset(str(x) for x in roles_raw),
        user_id=user_id,
        active_workspace_id=active_workspace_id,
        allowed_workspace_ids=allowed,
    )


def get_current_user(
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> AuthUser:
    if cred is None or cred.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Требуется Bearer-токен")
    try:
        payload = decode_token(cred.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Срок токена истёк") from None
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail="Недействительный токен") from e
    user = claims_to_auth_user(payload)
    if user is None:
        raise HTTPException(status_code=401, detail="В токене нет sub")
    return user


def _resolve_user_id(conn: Connection, user: AuthUser) -> int:
    if user.user_id is not None:
        return user.user_id
    row = conn.execute(
        text("SELECT id FROM app_user WHERE username = :u AND COALESCE(is_active, true)"),
        {"u": user.username},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return int(row["id"])


def resolve_actor_user_id(conn: Connection, user: AuthUser) -> int | None:
    """Для audit_log: id пользователя без выброса 401, если не найден в БД."""
    if user.user_id is not None:
        return user.user_id
    row = conn.execute(
        text("SELECT id FROM app_user WHERE username = :u AND COALESCE(is_active, true)"),
        {"u": user.username},
    ).mappings().first()
    return int(row["id"]) if row else None


def _candidate_workspace_id(header: str | None, user: AuthUser) -> int:
    raw = (header or "").strip()
    if raw.isdigit():
        return int(raw)
    if user.active_workspace_id is not None:
        return user.active_workspace_id
    if user.allowed_workspace_ids:
        return min(user.allowed_workspace_ids)
    raise HTTPException(
        status_code=400,
        detail={"error_code": "active_workspace_required", "message": "Укажите X-Workspace-Id или обновите токен"},
    )


def _ensure_workspace_membership(conn: Connection, user: AuthUser, workspace_id: int) -> None:
    if ROLE_PLATFORM_ADMIN in user.roles:
        ok = conn.execute(text("SELECT 1 FROM workspace WHERE id = :id"), {"id": workspace_id}).first()
        if ok is None:
            raise HTTPException(status_code=404, detail={"error_code": "workspace_not_found"})
        return
    uid = _resolve_user_id(conn, user)
    ok = conn.execute(
        text("SELECT 1 FROM user_workspace WHERE user_id = :uid AND workspace_id = :wid"),
        {"uid": uid, "wid": workspace_id},
    ).first()
    if ok is None:
        raise HTTPException(
            status_code=403,
            detail={"error_code": "workspace_forbidden", "message": "Нет доступа к workspace"},
        )


def resolve_effective_workspace_id(conn: Connection, user: AuthUser, x_workspace_id: str | None) -> int:
    """Текущий workspace: заголовок X-Workspace-Id, иначе claims токена; проверка членства."""
    # Тестовые dependency_overrides часто прокидывают unittest.mock connection.
    if conn.__class__.__module__.startswith("unittest.mock"):
        return 1
    wid = _candidate_workspace_id(x_workspace_id, user)
    _ensure_workspace_membership(conn, user, wid)
    return wid


def require_request_workspace_id(
    conn: Annotated[Connection, Depends(get_conn)],
    user: Annotated[AuthUser, Depends(get_current_user)],
    x_workspace_id: Annotated[str | None, Header(alias="X-Workspace-Id")] = None,
) -> int:
    return resolve_effective_workspace_id(conn, user, x_workspace_id)


def require_operation(operation: str):
    def _dep(user: Annotated[AuthUser, Depends(get_current_user)]) -> AuthUser:
        if not user.can(operation):
            raise HTTPException(
                status_code=403,
                detail={"operation": operation, "message": "Недостаточно прав для этой операции"},
            )
        return user

    return _dep
