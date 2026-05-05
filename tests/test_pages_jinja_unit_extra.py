from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from datanorma.web import pages_jinja as pj
from datanorma.web.deps import AuthUser

pytestmark = pytest.mark.unit


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None

    def scalar(self):
        r = self.first()
        if isinstance(r, dict):
            return next(iter(r.values())) if r else None
        return r

    def scalar_one(self):
        v = self.scalar()
        if v is None:
            raise RuntimeError("no scalar")
        return v


def _req(path: str = "/app/test") -> Request:
    return Request({"type": "http", "method": "GET", "path": path, "headers": []})


def _fake_template(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        pj.templates,
        "TemplateResponse",
        lambda request, name, context, status_code=200: {"template": name, "status_code": status_code, "context": context},
    )


def test_basic_helpers_and_connection_cards() -> None:
    assert pj._safe_next(" /app/dashboard ") == "/app/dashboard"
    assert pj._safe_next("/wrong") == "/app/dashboard"
    assert pj._canonical_sales_columns()[0] == "source_system"
    assert pj._safe_export_value(Decimal("10.5")) == 10.5
    assert "T" in pj._safe_export_value(datetime(2026, 1, 1, tzinfo=timezone.utc))

    conn = MagicMock()
    now = datetime.now(timezone.utc)
    conn.execute.side_effect = [
        _Rows([{"last_success_at": now - timedelta(hours=1)}]),
        _Rows([{"last_success_at": now - timedelta(days=5)}]),
        _Rows([{"last_success_at": None}]),
    ]
    cards = pj._connection_cards(conn)
    assert len(cards) == 3
    assert cards[0]["badge"] == "success"
    assert cards[1]["badge"] == "warn"


def test_dashboard_connections_and_post_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_template(monkeypatch)
    monkeypatch.setattr(pj, "warehouse_table_sql", lambda: "canonical_sales")
    monkeypatch.setattr(pj, "_connection_cards", lambda _c: [{"code": "ozon"}])
    user = AuthUser("seed", frozenset({"platform_admin"}))
    conn = MagicMock()
    conn.execute.side_effect = [_Rows([{"n": 10}]), _Rows([{"max": None}]), _Rows([{"n": 1}]), _Rows([{"n": 2}]), _Rows([{"n": 3}])]
    out = pj.page_dashboard(_req("/app/dashboard"), user, conn)
    assert out["template"] == "dashboard.html"

    conn2 = MagicMock()
    conn2.execute.side_effect = [_Rows([{"integration_code": "ozon"}]), _Rows([{"id": 1}])]
    out2 = pj.page_connections(_req("/app/connections"), user, conn2)
    assert out2["template"] == "connections.html"

    with pytest.raises(HTTPException):
        pj.page_connections_post(_req(), user, MagicMock(), integration_code="", stream_name="", sync_mode="x", cursor_field="")


def test_samples_password_and_sources_pages(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _fake_template(monkeypatch)
    user = AuthUser("seed", frozenset({"platform_admin"}))
    conn = MagicMock()
    conn.execute.return_value = _Rows([{"id": 1, "_ingest_extracted_at": None, "_ingest_meta": {}, "payload": {"a": 1}}])
    out = pj.page_connection_sample(_req(), "ozon", user, conn)
    assert out["template"] == "samples_preview.html"
    with pytest.raises(HTTPException):
        pj.page_connection_sample(_req(), "bad", user, conn)

    @dataclass
    class _DbUser:
        id: int
        username: str
        password_hash: str
        roles: list[str]

    monkeypatch.setattr(pj, "load_user_by_username", lambda *_a, **_k: _DbUser(1, "seed", "hash", ["platform_admin"]))
    monkeypatch.setattr(pj, "verify_password", lambda old, _h: old == "old")
    monkeypatch.setattr(pj, "hash_password", lambda p: f"h:{p}")
    bad = pj.page_password_post(_req(), user, MagicMock(), old_password="bad", new_password="new-pass")
    assert bad["status_code"] == 400
    short = pj.page_password_post(_req(), user, MagicMock(), old_password="old", new_password="123")
    assert short["status_code"] == 400
    ok_conn = MagicMock()
    ok = pj.page_password_post(_req(), user, ok_conn, old_password="old", new_password="new-pass")
    assert ok["template"] == "account_password.html"

    monkeypatch.setattr(pj, "_default_connector_builder_yaml", lambda: "version: 1")
    monkeypatch.setattr(
        pj,
        "create_source",
        lambda *_a, **_k: SimpleNamespace(
            check=lambda: SimpleNamespace(ok=True, message="ok", details={}),
            discover=lambda: SimpleNamespace(model_dump=lambda **_x: {"streams": []}),
        ),
    )
    monkeypatch.setattr(pj, "DataPathsResource", lambda: SimpleNamespace())
    new_get = pj.page_sources_new_get(_req(), user)
    new_post = pj.page_sources_new_post(_req(), user, source_kind="rest_builder", yaml_body="")
    assert new_get["template"] == "sources_new.html"
    assert new_post["template"] == "sources_new.html"


def test_mappings_runs_and_reference_pages(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _fake_template(monkeypatch)
    user = AuthUser("seed", frozenset({"platform_admin"}))
    conn = MagicMock()
    monkeypatch.setattr(pj, "resolve_workspace_id", lambda *_a, **_k: 1)
    monkeypatch.setattr(pj, "list_profiles", lambda *_a, **_k: [{"id": 1, "name": "default"}])
    monkeypatch.setattr(pj, "list_versions", lambda *_a, **_k: [{"id": 11}])
    out = pj.page_mappings(_req(), user, conn)
    assert out["template"] == "mappings_list.html"

    p = tmp_path / "mappings.yaml"
    p.write_text("sources: {ozon: {stream: orders}}", encoding="utf-8")
    monkeypatch.setattr(pj, "_mappings_yaml_path", lambda: p)
    out2 = pj.page_mappings_editor_get(_req(), user)
    assert out2["template"] == "mappings_editor.html"
    monkeypatch.setattr(pj, "create_draft_version", lambda *_a, **_k: {"id": 5, "profile_id": 2})
    monkeypatch.setattr(pj, "publish_version", lambda *_a, **_k: {"id": 6})
    monkeypatch.setattr(pj, "activate_profile_version", lambda *_a, **_k: None)
    post = pj.page_mappings_editor_post(_req(), user, conn, yaml_content="sources: {ozon: {stream: orders}}", action="publish_activate")
    assert post["template"] == "mappings_editor.html"

    monkeypatch.setattr(pj, "refresh_recent_sync_runs", lambda *_a, **_k: [{"id": 1, "status": "running"}])
    conn.execute.return_value = _Rows([{"id": 1, "integration_code": "ozon", "stream_name": "orders"}])
    runs = pj.page_runs(_req(), user, conn)
    assert runs["template"] == "runs_list.html"
    monkeypatch.setattr(pj, "get_sync_run", lambda *_a, **_k: {"id": 1, "status": "running"})
    monkeypatch.setattr(pj, "refresh_sync_run_status", lambda *_a, **_k: {"id": 1, "status": "success"})
    run = pj.page_run_detail(_req(), 1, user, conn)
    assert run["template"] == "run_detail.html"

    conn.execute.return_value = _Rows([{"code": "RUB", "name": "Ruble"}])
    curr = pj.page_ref_curr(_req(), user, conn)
    srcs = pj.page_ref_sources(_req(), user, conn)
    assert curr["template"] == "ref_currencies.html"
    assert srcs["template"] == "ref_sources.html"


def test_exports_admin_schedule_and_trigger(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_template(monkeypatch)
    user = AuthUser("seed", frozenset({"platform_admin"}))
    conn = MagicMock()
    monkeypatch.setattr(
        pj,
        "_fetch_canonical_sales_rows",
        lambda *_a, **_k: [{"source_system": "ozon", "source_record_id": "1", "event_datetime": datetime.now(timezone.utc), "amount": 10, "amount_rub": 10, "currency_code": "RUB", "channel": "mp", "status": "ok", "loaded_at": datetime.now(timezone.utc)}],
    )
    csv_resp = pj.page_export_csv(_req(), user, conn, limit=1)
    json_resp = pj.page_export_json(_req(), user, conn, limit=1)
    xml_resp = pj.page_export_xml(_req(), user, conn, limit=1)
    xlsx_resp = pj.page_export_xlsx(_req(), user, conn, limit=1)
    assert "canonical_sales.csv" in csv_resp.headers.get("content-disposition", "")
    assert "canonical_sales.json" in json_resp.headers.get("content-disposition", "")
    assert "canonical_sales.xml" in xml_resp.headers.get("content-disposition", "")
    assert "canonical_sales.xlsx" in xlsx_resp.headers.get("content-disposition", "")

    monkeypatch.setattr(pj, "list_users_with_roles", lambda *_a, **_k: [{"id": 1, "username": "seed"}])
    monkeypatch.setattr(pj, "list_roles", lambda *_a, **_k: [{"id": 1, "name": "platform_admin"}])
    admin = pj.page_admin_users(_req(), user, conn)
    roles = pj.page_user_roles_get(_req(), user, conn)
    assert admin["template"] == "admin_users.html"
    assert roles["template"] == "admin_user_roles.html"
    monkeypatch.setattr(pj, "record_audit_event", lambda *_a, **_k: None)
    monkeypatch.setattr(pj, "get_engine_cached", lambda: object())
    monkeypatch.setattr(pj, "resolve_actor_user_id", lambda *_a, **_k: 1)
    role_post = pj.page_user_roles_post(_req(), user, conn, user_id=1, role_id=1, action="add")
    assert role_post.status_code == 303

    conn.execute.return_value = _Rows([{"config_value": "0 5 * * *"}])
    sch_get = pj.page_schedule_get(_req(), user, conn)
    sch_post = pj.page_schedule_post(_req(), user, conn, cron="*/5 * * * *")
    assert sch_get["template"] == "settings_schedule.html"
    assert sch_post.status_code == 303

    monkeypatch.setattr(pj, "resolve_connection", lambda *_a, **_k: (_ for _ in ()).throw(pj.SyncRunError("bad conn")))
    fail = pj.page_run_trigger(_req(), user, conn, connection_id=1, note="")
    assert fail["status_code"] == 422
    monkeypatch.setattr(pj, "resolve_connection", lambda *_a, **_k: (10, 5, "ozon", "orders"))
    monkeypatch.setattr(pj, "create_sync_run", lambda *_a, **_k: {"id": 77})
    monkeypatch.setattr(pj, "launch_dagster_run", lambda *_a, **_k: SimpleNamespace(run_id="dag-77"))
    monkeypatch.setattr(pj, "mark_sync_run_running", lambda *_a, **_k: None)
    ok = pj.page_run_trigger(_req(), user, conn, connection_id=1, note="")
    assert ok.status_code == 303
