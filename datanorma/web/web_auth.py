"""Cookie + JWT для серверных страниц Jinja2."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request

from datanorma.web.deps import AuthUser
from datanorma.web.jwt_util import decode_token

COOKIE_NAME = "datanorma_access_token"


class WebAuthRequired(Exception):
    """Редирект на /app/login (обработчик в main)."""

    def __init__(self, path: str = "") -> None:
        self.path = path or ""


def token_from_cookie(request: Request) -> str | None:
    v = request.cookies.get(COOKIE_NAME)
    return v.strip() if v else None


def auth_user_from_token(token: str) -> AuthUser | None:
    try:
        payload = decode_token(token)
    except jwt.InvalidTokenError:
        return None
    username = payload.get("sub")
    if not username or not isinstance(username, str):
        return None
    roles_raw = payload.get("roles") or []
    if not isinstance(roles_raw, list):
        roles_raw = []
    return AuthUser(username=username, roles=frozenset(str(x) for x in roles_raw))


def get_web_user_optional(request: Request) -> AuthUser | None:
    tok = token_from_cookie(request)
    if not tok:
        return None
    return auth_user_from_token(tok)


def get_web_user(request: Request) -> AuthUser:
    u = get_web_user_optional(request)
    if u is None:
        raise WebAuthRequired(request.url.path)
    return u


def web_user_dep(request: Request) -> AuthUser:
    return get_web_user(request)


def require_web_op(operation: str):
    def _dep(user: Annotated[AuthUser, Depends(web_user_dep)]) -> AuthUser:
        if not user.can(operation):
            raise HTTPException(
                status_code=403,
                detail=f"Нет прав на операцию «{operation}». Войдите под другой ролью.",
            )
        return user

    return _dep
