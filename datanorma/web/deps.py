"""FastAPI: JWT Bearer, соединение с БД, проверка операций RBAC."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine

from datanorma.web.config import database_url
from datanorma.web.jwt_util import decode_token
from datanorma.web.rbac_matrix import OPERATION_ROLES

security = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthUser:
    username: str
    roles: frozenset[str]

    def can(self, operation: str) -> bool:
        allowed = OPERATION_ROLES.get(operation, ())
        return bool(self.roles.intersection(allowed))


@lru_cache(maxsize=1)
def get_engine_cached() -> Engine:
    return create_engine(database_url(), pool_pre_ping=True)


def get_conn() -> Connection:
    with get_engine_cached().begin() as conn:
        yield conn


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
    username = payload.get("sub")
    if not username or not isinstance(username, str):
        raise HTTPException(status_code=401, detail="В токене нет sub")
    roles_raw = payload.get("roles") or []
    if not isinstance(roles_raw, list):
        roles_raw = []
    return AuthUser(username=username, roles=frozenset(str(x) for x in roles_raw))


def require_operation(operation: str):
    def _dep(user: Annotated[AuthUser, Depends(get_current_user)]) -> AuthUser:
        if not user.can(operation):
            raise HTTPException(
                status_code=403,
                detail={"operation": operation, "message": "Недостаточно прав для этой операции"},
            )
        return user

    return _dep
