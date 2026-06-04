from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from datanorma.core.ingest_protocol import SyncMode
from datanorma.resources.paths import DataPathsResource
from datanorma.sources.moysklad import _flatten_moysklad_row
from datanorma.sources.registry import create_source

pytestmark = pytest.mark.unit

_FIXTURES = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "moysklad"


def _load_fixture(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def test_check_without_token_fails(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    src = create_source("moysklad", paths=paths, source_config={})
    res = src.check()
    assert res.ok is False


def test_check_mock(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    body = {"rows": [{"meta": {"href": "x", "type": "organization"}}], "meta": {"size": 1}}
    with patch("datanorma.sources.moysklad.request_json", return_value=(200, body)):
        src = create_source("moysklad", paths=paths, source_config={"token": "tok"})
        res = src.check()
    assert res.ok is True


def test_discover_mock(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    row = {"id": "a", "updated": "2026-05-01 12:00:00", "name": "t"}

    def _get(method, url, **kwargs):
        return 200, {"rows": [row], "meta": {"size": 1}}

    with patch("datanorma.sources.moysklad.request_json", side_effect=_get):
        src = create_source("moysklad", paths=paths, source_config={"token": "tok"})
        catalog = src.discover()
        assert {s.name for s in catalog.streams} >= {"demand", "customerorder", "product", "counterparty"}


def test_read_mock(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    row = {"id": "a", "updated": "2026-05-01 12:00:00"}

    def _get(method, url, **kwargs):
        return 200, {"rows": [row], "meta": {"size": 1}}

    with patch("datanorma.sources.moysklad.request_json", side_effect=_get):
        src = create_source("moysklad", paths=paths, source_config={"token": "tok"})
        rows = list(src.read("demand", sync_mode="full_refresh"))
        assert len(rows) >= 1


def test_discover_includes_invoiceout_and_stock(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))

    def _get(method, url, **kwargs):
        if "report/stock/all" in url:
            return 200, _load_fixture("stock_all.json")
        return 200, {"rows": [{"id": "a", "updated": "2026-05-01 12:00:00", "name": "t"}], "meta": {"size": 1}}

    with patch("datanorma.sources.moysklad.request_json", side_effect=_get):
        src = create_source("moysklad", paths=paths, source_config={"token": "tok"})
        catalog = src.discover()
        names = {s.name for s in catalog.streams}
    assert names == {"demand", "customerorder", "product", "counterparty", "invoiceout", "stock"}


def test_read_customer_orders_paginated(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    page1 = _load_fixture("customer_orders_page1.json")
    page2 = _load_fixture("customer_orders_page2.json")

    def _get(method, url, *, params=None, **kwargs):
        off = (params or {}).get("offset", 0)
        if off == 0:
            return 200, page1
        if off == 500:
            return 200, page2
        return 200, {"meta": {"size": 0}, "rows": []}

    with patch("datanorma.sources.moysklad.request_json", side_effect=_get):
        src = create_source("moysklad", paths=paths, source_config={"token": "tok"})
        rows = list(src.read("customerorder", sync_mode="full_refresh"))
    assert len(rows) == 3
    # Уплощение применено: meta заменён на href, agent развёрнут.
    first = rows[0]
    assert "meta" not in first
    assert first["href"].endswith("/aaa")
    assert first["agent_name"] == "ООО Ромашка"


def test_read_incremental_filter(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    captured: dict = {}

    def _get(method, url, *, params=None, **kwargs):
        captured.update(params or {})
        return 200, {"meta": {"size": 0}, "rows": []}

    with patch("datanorma.sources.moysklad.request_json", side_effect=_get):
        src = create_source("moysklad", paths=paths, source_config={"token": "tok"})
        list(src.read("demand", sync_mode="incremental", last_cursor="1700000000000"))
    assert str(captured.get("filter", "")).startswith("updated>")


def test_stock_is_full_refresh_only(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))

    def _get(method, url, *, params=None, **kwargs):
        if "report/stock/all" in url:
            assert "filter" not in (params or {})
            return 200, _load_fixture("stock_all.json")
        return 200, {"rows": [{"id": "a", "updated": "2026-05-01 12:00:00"}], "meta": {"size": 1}}

    with patch("datanorma.sources.moysklad.request_json", side_effect=_get):
        src = create_source("moysklad", paths=paths, source_config={"token": "tok"})
        catalog = src.discover()
        stock = next(s for s in catalog.streams if s.name == "stock")
        assert SyncMode.full_refresh in stock.supported_sync_modes
        assert SyncMode.incremental not in stock.supported_sync_modes
        rows = list(src.read("stock", sync_mode="incremental", last_cursor="1700000000000"))
    assert rows and "meta" not in rows[0]
    assert rows[0]["href"].endswith("/p1")


def test_flatten_row_removes_meta() -> None:
    row = {
        "meta": {"href": "H", "type": "customerorder"},
        "id": "x",
        "agent": {"name": "A", "meta": {"href": "AH"}},
        "positions": {"meta": {"href": "PH", "size": 3}},
    }
    out = _flatten_moysklad_row(row)
    assert "meta" not in out
    assert out["href"] == "H"
    assert out["agent_name"] == "A"
    assert out["agent_href"] == "AH"
    assert "agent" not in out
    assert out["positions_href"] == "PH"
    assert "positions" not in out
