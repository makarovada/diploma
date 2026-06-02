"""Unit tests for workspace permission service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datanorma.web.permission_catalog import PERM_SOURCE_READ, PERM_SOURCE_UPDATE
from datanorma.web.permission_service import (
    ResourceRef,
    WorkspaceAuthContext,
    authorize,
    grant_level_covers,
)


def test_grant_level_covers() -> None:
    assert grant_level_covers("manage", "view")
    assert grant_level_covers("edit", "view")
    assert not grant_level_covers("view", "edit")


def test_authorize_workspace_permission() -> None:
    ctx = WorkspaceAuthContext(user_id=2, workspace_id=1, is_admin=False, permissions=frozenset({PERM_SOURCE_READ}))
    conn = MagicMock()
    assert authorize(ctx, conn, permission=PERM_SOURCE_READ)
    assert not authorize(ctx, conn, permission=PERM_SOURCE_UPDATE)


def test_authorize_admin_bypass() -> None:
    ctx = WorkspaceAuthContext(user_id=2, workspace_id=1, is_admin=True)
    conn = MagicMock()
    assert authorize(ctx, conn, permission=PERM_SOURCE_UPDATE, resource=ResourceRef("source", 99))


def test_authorize_resource_grant() -> None:
    ctx = WorkspaceAuthContext(user_id=5, workspace_id=1, is_admin=False, permissions=frozenset())
    conn = MagicMock()
    conn.execute.return_value.mappings.return_value.first.side_effect = [
        None,  # owner
        {"level": "edit"},  # grant
    ]
    ref = ResourceRef("source", 10)
    assert authorize(ctx, conn, permission=PERM_SOURCE_UPDATE, resource=ref)
