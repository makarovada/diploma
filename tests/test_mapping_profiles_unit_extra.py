from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datanorma.web import mapping_profiles as mp

pytestmark = pytest.mark.unit


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def one(self):
        return self.rows[0]

    def all(self):
        return self.rows

    def scalar_one(self):
        r = self.rows[0]
        if isinstance(r, dict):
            return next(iter(r.values()))
        return r


def test_workspace_and_draft_publish_list_paths() -> None:
    conn = MagicMock()
    conn.execute.side_effect = [
        _Rows([{"id": 1}]),  # resolve_workspace_id
        _Rows([{"id": 10}]),  # _ensure_profile
        _Rows([{"n": 2}]),  # _next_version
        _Rows([{"id": 20, "profile_id": 10, "version": 3, "status": "draft", "rules_json": {}, "change_note": None, "created_at": "t", "created_by": "u"}]),  # draft
        _Rows([{"id": 20, "profile_id": 10, "version": 3, "status": "published", "rules_json": {}, "change_note": None, "created_at": "t", "created_by": "u"}]),  # publish
        _Rows([{"id": 1, "profile_name": "default"}]),  # list_profiles
        _Rows([{"id": 20, "version": 3}]),  # list_versions
    ]
    assert mp.resolve_workspace_id(conn, "main") == 1
    draft = mp.create_draft_version(
        conn,
        workspace_id=1,
        source_type="ozon",
        stream_name="orders",
        profile_name="default",
        rules_json={"stream": "orders"},
        created_by="seed",
    )
    assert draft["status"] == "draft"
    pub = mp.publish_version(conn, profile_id=10, version_id=20)
    assert pub["status"] == "published"
    assert mp.list_profiles(conn, workspace_id=1)[0]["id"] == 1
    assert mp.list_versions(conn, profile_id=10)[0]["id"] == 20


def test_activate_rollback_and_active_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    conn.execute.side_effect = [
        _Rows([{"id": 10, "workspace_id": 1, "source_type": "ozon", "stream_name": "orders"}]),  # profile
        _Rows([{"id": 20, "status": "published"}]),  # version
        _Rows([{"ok": 1}]),  # deactivate scope
        _Rows([{"id": 10, "is_active": True, "active_version_id": 20, "workspace_id": 1, "source_type": "ozon", "stream_name": "orders", "profile_name": "default", "updated_at": "t", "updated_by": "seed"}]),  # activate row
        _Rows([{"workspace_id": 1, "source_type": "ozon", "stream_name": "orders", "profile_name": "default", "rules_json": {"a": 1}, "version": 2}]),  # rollback src
        _Rows([{"rules_json": {"k": "v"}}]),  # get_active_source_rules
        _Rows([{"source_type": "ozon", "stream_name": "orders", "rules_json": {"k": "v"}}]),  # all active rules
    ]
    act = mp.activate_profile_version(conn, profile_id=10, version_id=20, updated_by="seed")
    assert act["active_version_id"] == 20
    monkeypatch.setattr(mp, "create_draft_version", lambda *_a, **_k: {"id": 31, "profile_id": 10})
    monkeypatch.setattr(mp, "publish_version", lambda *_a, **_k: {"id": 32, "profile_id": 10, "status": "published"})
    monkeypatch.setattr(mp, "activate_profile_version", lambda *_a, **_k: {"id": 10, "active_version_id": 32})
    rb = mp.rollback_to_version(conn, profile_id=10, version_id=20, updated_by="seed")
    assert rb["status"] == "published"
    assert mp.get_active_source_rules(conn, workspace_id=1, source_type="ozon", stream_name="orders") == {"k": "v"}
    all_rules = mp.get_all_active_source_rules(conn, workspace_id=1)
    assert all_rules[("ozon", "orders")] == {"k": "v"}


def test_publish_and_activate_errors() -> None:
    conn = MagicMock()
    conn.execute.side_effect = [_Rows([])]
    with pytest.raises(mp.MappingProfileError):
        mp.publish_version(conn, profile_id=1, version_id=2)

    conn2 = MagicMock()
    conn2.execute.side_effect = [_Rows([])]
    with pytest.raises(mp.MappingProfileError):
        mp.activate_profile_version(conn2, profile_id=1, version_id=2, updated_by="u")
