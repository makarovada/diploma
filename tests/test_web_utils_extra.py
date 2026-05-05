from __future__ import annotations

from datetime import datetime, timezone

import jwt
import pytest
from starlette.requests import Request

from datanorma.config import clear_settings_cache
from datanorma.web import config as web_config
from datanorma.web import jwt_util, request_audit, sql_util

pytestmark = pytest.mark.unit


def test_sql_util_safe_ident_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Settings:
        datanorma_warehouse_table = "orders_2026"
        datanorma_typed_table = "typed_orders"

    monkeypatch.setattr(sql_util, "get_settings", lambda: _Settings())
    assert sql_util.warehouse_table_sql() == "orders_2026"
    assert sql_util.typed_table_sql() == "typed_orders"

    _Settings.datanorma_warehouse_table = "bad-name;drop"
    _Settings.datanorma_typed_table = "bad name"
    assert sql_util.warehouse_table_sql() == "canonical_sales"
    assert sql_util.typed_table_sql() == "typed_canonical_sales"


def test_request_audit_ip_and_user_agent() -> None:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [
            (b"x-forwarded-for", b"10.0.0.2, 10.0.0.3"),
            (b"user-agent", b"pytest-agent"),
        ],
        "client": ("127.0.0.1", 1234),
    }
    req = Request(scope)
    assert request_audit.client_ip(req) == "10.0.0.2"
    assert request_audit.client_user_agent(req) == "pytest-agent"
    assert request_audit.client_ip(None) is None
    assert request_audit.client_user_agent(None) is None


def test_web_config_dev_and_production(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_cache()
    monkeypatch.setenv("DATANORMA_ENVIRONMENT", "development")
    monkeypatch.delenv("DATANORMA_JWT_SECRET", raising=False)
    monkeypatch.delenv("DATANORMA_CORS_ORIGINS", raising=False)
    assert web_config.jwt_secret() == "dev-insecure-change-me"
    assert "http://localhost:5173" in web_config.cors_allow_origins()

    clear_settings_cache()
    monkeypatch.setenv("DATANORMA_ENVIRONMENT", "production")
    monkeypatch.setenv("DATANORMA_JWT_SECRET", "super-secret")
    monkeypatch.setenv("DATANORMA_CORS_ORIGINS", "https://app.example.com")
    web_config.validate_security_at_startup()
    assert web_config.jwt_secret() == "super-secret"


def test_jwt_create_decode_with_workspace_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jwt_util, "jwt_secret", lambda: "test-secret")
    monkeypatch.setattr(jwt_util, "jwt_expire_hours", lambda: 1)
    token = jwt_util.create_access_token(
        username="seed_admin",
        roles=["platform_admin"],
        user_id=42,
        active_workspace_id=7,
        allowed_workspace_ids=[7, 8],
    )
    payload = jwt_util.decode_token(token)
    assert payload["sub"] == "seed_admin"
    assert payload["roles"] == ["platform_admin"]
    assert payload["user_id"] == 42
    assert payload["active_workspace_id"] == 7
    assert payload["allowed_workspace_ids"] == [7, 8]
    assert payload["iat"] <= int(datetime.now(timezone.utc).timestamp())

    # sanity-check token is real HS256 JWT
    decoded = jwt.decode(token, "test-secret", algorithms=["HS256"])
    assert decoded["sub"] == "seed_admin"
