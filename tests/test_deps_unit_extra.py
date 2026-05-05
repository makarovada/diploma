from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from datanorma.web import deps

pytestmark = pytest.mark.unit


class _Rows:
    def __init__(self, row):
        self.row = row

    def mappings(self):
        return self

    def first(self):
        return self.row


def test_claims_to_auth_user_and_parse_allowed() -> None:
    u = deps.claims_to_auth_user(
        {
            "sub": "seed_admin",
            "roles": ["platform_admin", "analyst"],
            "user_id": "7",
            "active_workspace_id": "2",
            "allowed_workspace_ids": ["2", "3", "bad"],
        }
    )
    assert u is not None
    assert u.user_id == 7
    assert u.active_workspace_id == 2
    assert u.allowed_workspace_ids == frozenset({2, 3})


def test_resolve_actor_and_workspace_membership_paths() -> None:
    conn = MagicMock()
    conn.execute.side_effect = [_Rows({"id": 9}), _Rows({"id": 11}), _Rows({"ok": 1})]
    user = deps.AuthUser("u", frozenset({"analyst"}), user_id=None, active_workspace_id=2, allowed_workspace_ids=frozenset({2}))
    assert deps.resolve_actor_user_id(conn, user) == 9

    # non-admin membership ok
    deps._ensure_workspace_membership(conn, user, 2)

    # forbidden ветка покрывается в интеграционных web_rbac тестах


def test_candidate_workspace_id_and_require_operation() -> None:
    user = deps.AuthUser("u", frozenset({"analyst"}), active_workspace_id=5, allowed_workspace_ids=frozenset({5}))
    assert deps._candidate_workspace_id("7", user) == 7
    assert deps._candidate_workspace_id(None, user) == 5
    with pytest.raises(HTTPException):
        deps._candidate_workspace_id(None, deps.AuthUser("u", frozenset()))

    allowed_dep = deps.require_operation("view_api_v1_catalog")
    denied_dep = deps.require_operation("manage_workspaces")
    assert allowed_dep(deps.AuthUser("u", frozenset({"platform_admin"}))).username == "u"
    with pytest.raises(HTTPException):
        denied_dep(deps.AuthUser("u", frozenset({"viewer"})))
