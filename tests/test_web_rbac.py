"""RBAC и JWT: без PostgreSQL (dependency overrides)."""

from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

from datanorma.web.deps import AuthUser, get_current_user
from datanorma.web.main import create_app
from datanorma.web.rbac_matrix import ALL_ROLES, OPERATION_ROLES, OPERATION_LABELS_RU, matrix_payload
from datanorma.web.passwords import hash_password, verify_password

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_password_bcrypt_roundtrip() -> None:
    h = hash_password("AnalystDemo2026")
    assert verify_password("AnalystDemo2026", h)
    assert not verify_password("wrong", h)


def test_password_legacy_sha256_hex() -> None:
    legacy = hashlib.sha256("AnalystDemo2026".encode("utf-8")).hexdigest()
    assert verify_password("AnalystDemo2026", legacy)
    assert not verify_password("wrong", legacy)


def test_matrix_has_label_for_every_operation() -> None:
    for op in OPERATION_ROLES:
        assert op in OPERATION_LABELS_RU, f"Нет подписи для {op}"
    for r in ALL_ROLES:
        assert any(r in roles for roles in OPERATION_ROLES.values()), f"Роль {r} ни на что не назначена"


def test_matrix_payload_shape() -> None:
    p = matrix_payload()
    assert len(p["roles"]) == 3
    assert len(p["operations"]) == len(OPERATION_ROLES)


def test_analyst_forbidden_admin_users(client: TestClient) -> None:
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: AuthUser("seed_analyst", frozenset({"analyst"}))
    r = client.get("/api/admin/users", headers={"Authorization": "Bearer t"})
    assert r.status_code == 403
    assert r.json()["detail"]["operation"] == "view_admin_users"


def test_analyst_allowed_permissions_catalog(client: TestClient) -> None:
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: AuthUser("seed_analyst", frozenset({"analyst"}))
    r = client.get("/api/v1/permissions/catalog", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    data = r.json()
    assert "items" in data


def test_integrator_forbidden_admin_users(client: TestClient) -> None:
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: AuthUser("seed_integrator", frozenset({"data_integrator"}))
    r = client.get("/api/admin/users", headers={"Authorization": "Bearer t"})
    assert r.status_code == 403


def test_admin_allowed_admin_users_mock_conn(client: TestClient) -> None:
    from datanorma.web import deps as deps_mod
    from sqlalchemy.engine import Connection
    from unittest.mock import MagicMock

    app = client.app
    app.dependency_overrides[get_current_user] = lambda: AuthUser("seed_admin", frozenset({"platform_admin"}))

    conn = MagicMock(spec=Connection)
    exec_result = MagicMock()
    exec_result.mappings.return_value = iter([])
    conn.execute.return_value = exec_result

    def fake_conn():
        yield conn

    app.dependency_overrides[deps_mod.get_conn] = fake_conn
    r = client.get("/api/admin/users", headers={"Authorization": "Bearer t"})
    app.dependency_overrides.pop(deps_mod.get_conn, None)
    assert r.status_code == 200
    assert "users" in r.json()
