from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datanorma.web import elt_repo as repo

pytestmark = pytest.mark.unit


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows

    def one(self):
        return self.rows[0]

    def __bool__(self):
        return bool(self.rows)


_CONN_LIST_ROW = {
    "id": 11,
    "workspace_id": 1,
    "name": "C",
    "description": None,
    "source_id": 1,
    "destination_id": 2,
    "status": "active",
    "schedule_cron": None,
    "timezone": "UTC",
    "is_active": True,
    "created_by": None,
    "created_at": None,
    "updated_at": None,
    "wizard_meta": None,
    "stream_count": 1,
    "source_name": "S",
    "source_connector_code": "ozon",
    "destination_name": "D",
    "destination_connector_code": "postgres",
}
_CONN_GET_ROW = {k: v for k, v in _CONN_LIST_ROW.items() if k != "stream_count"}
_STREAM_ROW = {
    "id": 21,
    "connection_id": 11,
    "stream_name": "orders",
    "sync_mode": "incremental",
    "cursor_field": "updated_at",
    "primary_key": None,
    "is_enabled": True,
    "cursor_value": None,
    "mapping_profile_id": None,
}


def test_config_helpers_and_public_payloads() -> None:
    assert repo._config_load('{"a":1}') == {"a": 1}
    assert repo._config_load("bad-json") == {}
    assert repo._config_dump({"a": 1}).startswith("{")
    assert repo._config_dump(None) == "{}"

    src = repo.public_source_payload({"id": 1, "config_encrypted": '{"x":1}'})
    dst = repo.public_destination_payload({"id": 2, "config_encrypted": '{"y":2}'})
    assert src["config"]["x"] == 1
    assert dst["config"]["y"] == 2


def test_list_get_and_delete_helpers() -> None:
    conn = MagicMock()
    conn.execute.side_effect = [
        _Rows([{"id": 1, "workspace_id": 1}]),
        _Rows([{"id": 1, "workspace_id": 1}]),
        _Rows([{"id": 1}]),
    ]
    assert repo.list_sources(conn, workspace_id=1)[0]["id"] == 1
    assert repo.get_source(conn, workspace_id=1, source_id=1)["id"] == 1
    assert repo.delete_source_row(conn, workspace_id=1, source_id=1) is True


def test_create_connection_row_and_sync_state(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    monkeypatch.setattr(repo, "get_source", lambda *_a, **_k: {"id": 1, "connector_code": "ozon"})
    monkeypatch.setattr(repo, "get_destination", lambda *_a, **_k: {"id": 2, "connector_code": "postgres"})
    monkeypatch.setattr(repo, "get_connection", lambda *_a, **_k: {"id": 10, "streams": [{"stream_name": "orders"}]})
    monkeypatch.setattr(repo, "ensure_sync_state_for_stream", lambda *_a, **_k: None)
    conn.execute.side_effect = [
        _Rows([{"id": 10, "workspace_id": 1}]),  # connection insert
        _Rows([{"id": 20}]),  # connection_stream insert
    ]
    out = repo.create_connection_row(
        conn,
        workspace_id=1,
        name="C1",
        description=None,
        source_id=1,
        destination_id=2,
        schedule_cron=None,
        timezone="UTC",
        streams=[{"stream_name": "orders", "sync_mode": "incremental", "cursor_field": "updated_at"}],
        created_by="seed",
    )
    assert out["id"] == 10


def test_create_connection_row_raises_when_missing_entities(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    monkeypatch.setattr(repo, "get_source", lambda *_a, **_k: None)
    with pytest.raises(repo.EltRepoError, match="source not found"):
        repo.create_connection_row(
            conn,
            workspace_id=1,
            name="C2",
            description=None,
            source_id=1,
            destination_id=2,
            schedule_cron=None,
            timezone="UTC",
            streams=[],
            created_by="seed",
        )


def test_destinations_connections_and_touch_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    conn.execute.side_effect = [
        _Rows([{"id": 2, "workspace_id": 1}]),
        _Rows([{"id": 2, "workspace_id": 1, "name": "D", "connector_code": "csv", "config_encrypted": "{}", "status": "active"}]),
        _Rows([{"id": 2, "workspace_id": 1, "name": "D", "connector_code": "csv", "config_encrypted": "{}", "status": "active"}]),
        _Rows([{"id": 2, "workspace_id": 1, "name": "D2", "connector_code": "csv", "config_encrypted": "{}", "status": "active"}]),
        _Rows([{"id": 2}]),
    ]
    assert repo.list_destinations(conn, workspace_id=1)[0]["id"] == 2
    assert repo.get_destination(conn, workspace_id=1, destination_id=2)["id"] == 2
    assert repo.update_destination_row(conn, workspace_id=1, destination_id=2, name="D2")["id"] == 2
    assert repo.delete_destination_row(conn, workspace_id=1, destination_id=2) is True

    conn2 = MagicMock()
    conn2.execute.side_effect = [
        _Rows([_CONN_LIST_ROW]),
        _Rows([_CONN_GET_ROW]),
        _Rows([_STREAM_ROW]),
        _Rows([{"1": 1}]),
        _Rows([]),
        _Rows([_CONN_GET_ROW]),
        _Rows([_STREAM_ROW]),
        _Rows([{"id": 11}]),
    ]
    assert repo.list_connections(conn2, workspace_id=1)[0]["id"] == 11
    assert repo.get_connection(conn2, workspace_id=1, connection_id=11)["streams"][0]["stream_name"] == "orders"
    assert repo.update_connection_row(conn2, workspace_id=1, connection_id=11, status="paused")["id"] == 11
    assert repo.delete_connection_row(conn2, workspace_id=1, connection_id=11) is True

    conn3 = MagicMock()
    conn3.execute.side_effect = [_Rows([{"id": 1}]), _Rows([{"id": 1}]), _Rows([{"id": 1}])]
    repo.ensure_sync_state_for_stream(
        conn3,
        integration_code="ozon",
        stream_name="orders",
        sync_mode="incremental",
        cursor_field="updated_at",
        connection_stream_id=21,
    )
    repo.touch_source_checked(conn3, workspace_id=1, source_id=1)
    repo.touch_destination_checked(conn3, workspace_id=1, destination_id=2)
