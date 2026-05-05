"""JWT с claims: sub (username), roles (список имён ролей)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from datanorma.web.config import jwt_expire_hours, jwt_secret


def create_access_token(
    *,
    username: str,
    roles: list[str],
    user_id: int | None = None,
    active_workspace_id: int | None = None,
    allowed_workspace_ids: list[int] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=jwt_expire_hours())
    payload: dict[str, Any] = {
        "sub": username,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": exp,
    }
    if user_id is not None:
        payload["user_id"] = user_id
    if active_workspace_id is not None:
        payload["active_workspace_id"] = active_workspace_id
    if allowed_workspace_ids is not None:
        payload["allowed_workspace_ids"] = allowed_workspace_ids
    return jwt.encode(payload, jwt_secret(), algorithm="HS256")


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, jwt_secret(), algorithms=["HS256"])
