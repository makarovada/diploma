"""JWT с claims: sub (username), roles (список имён ролей)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from datanorma.web.config import jwt_expire_hours, jwt_secret


def create_access_token(*, username: str, roles: list[str]) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=jwt_expire_hours())
    payload: dict[str, Any] = {
        "sub": username,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": exp,
    }
    return jwt.encode(payload, jwt_secret(), algorithm="HS256")


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, jwt_secret(), algorithms=["HS256"])
