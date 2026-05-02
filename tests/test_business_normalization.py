"""Этап 3: ФИО, контакты, справочники статусов, enrich с SQLite dims."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text

from datanorma.normalization.contacts import normalize_email, normalize_phone_ru
from datanorma.normalization.enrich import enrich_canonical_rows
from datanorma.normalization.person_name import parse_person_name
from datanorma.normalization.references import (
    _country_codes_cache,
    _currency_codes_cache,
    _status_map_cache,
    _unit_codes_cache,
)
from datanorma.normalization.statuses import resolve_status


def _clear_ref_caches() -> None:
    _status_map_cache.clear()
    _country_codes_cache.clear()
    _unit_codes_cache.clear()
    _currency_codes_cache.clear()


@pytest.fixture
def dim_engine():
    _clear_ref_caches()
    eng = create_engine("sqlite+pysqlite:///:memory:", future=True)
    stmts = [
        "CREATE TABLE dim_status_map (dimension TEXT, source_system TEXT, raw_status TEXT, canonical_code TEXT)",
        "CREATE TABLE dim_country (code TEXT)",
        "CREATE TABLE dim_unit (code TEXT)",
        "CREATE TABLE dim_currency (code TEXT)",
        "INSERT INTO dim_status_map VALUES ('order', 'ozon', 'delivered', 'DONE')",
        "INSERT INTO dim_country VALUES ('RU')",
        "INSERT INTO dim_unit VALUES ('pcs')",
        "INSERT INTO dim_currency VALUES ('RUB')",
    ]
    with eng.begin() as c:
        for s in stmts:
            c.execute(text(s))
    yield eng
    _clear_ref_caches()


def test_parse_person_name_three_tokens() -> None:
    p = parse_person_name("иванов петр сергеевич")
    assert p["person_family_name"] == "Иванов"
    assert p["person_given_name"] == "Петр"
    assert p["person_patronymic"] == "Сергеевич"
    assert p["quality"] == "full"
    assert "Иванов" in (p.get("person_full_name") or "")


def test_parse_person_name_skips_llc() -> None:
    p = parse_person_name('ООО "Ромашка"')
    assert p["person_family_name"] is None
    assert p["quality"] == "unknown"


def test_normalize_phone_ru_variants() -> None:
    assert normalize_phone_ru("8 (903) 123-45-67") == "+79031234567"
    assert normalize_phone_ru("+7 903 123 45 67") == "+79031234567"
    assert normalize_phone_ru("9031234567") == "+79031234567"


def test_normalize_email() -> None:
    assert normalize_email("  Test@Example.COM ") == "test@example.com"
    assert normalize_email("not-an-email") is None


def test_resolve_status_uses_cache() -> None:
    cache = {("order", "ozon", "done"): "CLOSED"}
    assert resolve_status(None, "order", "ozon", "done", cache=cache) == "CLOSED"
    assert resolve_status(None, "order", "ozon", "missing", cache=cache) is None


def test_enrich_maps_order_status_from_dim(dim_engine, monkeypatch: pytest.MonkeyPatch) -> None:
    import datanorma.normalization.enrich as enrich_mod

    monkeypatch.setattr(enrich_mod, "get_cbr_rates_map", lambda _d: {"RUB": 1.0})
    rows = [
        {
            "source_system": "ozon",
            "source_record_id": "1",
            "event_datetime": "2025-01-15",
            "amount": 100,
            "currency_code": "RUB",
            "counterparty_name": None,
            "channel": None,
            "line_description": None,
            "status": "delivered",
        }
    ]
    out, _ = enrich_canonical_rows(rows, fallback_rate_date=date(2025, 1, 15), engine=dim_engine)
    assert out[0]["order_status_code"] == "DONE"
    fixes = out[0]["normalization_meta"].get("fixes") or []
    assert any(f.get("action") == "status_mapped" for f in fixes)


def test_normalization_fix_stats_api() -> None:
    from fastapi.testclient import TestClient

    from datanorma.web.deps import AuthUser, get_conn, get_current_user
    from datanorma.web.main import create_app

    conn = MagicMock()
    result = MagicMock()
    result.mappings.return_value.all.return_value = [
        {"action": "strip", "field": "currency_code", "cnt": 2},
        {"action": "number_cast", "field": "amount", "cnt": 1},
    ]
    conn.execute.return_value = result

    def _fake_conn():
        yield conn

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthUser("u", frozenset({"data_integrator"}))
    app.dependency_overrides[get_conn] = _fake_conn
    with TestClient(app) as client:
        r = client.get("/api/data/normalization-fix-stats?limit=10")
    assert r.status_code == 200
    data = r.json()
    assert data["rows"][0]["action"] == "strip"
    assert data["rows"][0]["cnt"] == 2
