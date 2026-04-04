"""Unit-тесты нормализации (этап 3): ЦБ, даты, fuzzy, enrich."""

from __future__ import annotations

from datetime import date

import pytest

from datanorma.normalization.cbr_rates import amount_to_rub, parse_cbr_daily_xml
from datanorma.normalization.dates_msk import format_msk_iso, parse_to_datetime
from datanorma.normalization.enrich import enrich_canonical_rows
from datanorma.normalization.to_canonical import _lookup_row_value, _map_tabular_row
from datanorma.normalization.units import normalize_unit_label


def test_parse_cbr_daily_xml_usd_nominal() -> None:
    xml = """<?xml version="1.0" encoding="windows-1251"?>
    <ValCurs Date="29.03.2026">
      <Valute ID="R01235">
        <NumCode>840</NumCode><CharCode>USD</CharCode><Nominal>1</Nominal>
        <Name>US Dollar</Name><Value>90,1234</Value>
      </Valute>
      <Valute ID="R01239">
        <NumCode>978</NumCode><CharCode>EUR</CharCode><Nominal>1</Nominal>
        <Name>Euro</Name><Value>98,50</Value>
      </Valute>
    </ValCurs>"""
    rates = parse_cbr_daily_xml(xml)
    assert pytest.approx(rates["USD"], rel=1e-6) == 90.1234
    assert pytest.approx(rates["EUR"], rel=1e-6) == 98.50


def test_amount_to_rub_and_rub_passthrough() -> None:
    r = {"USD": 100.0}
    assert amount_to_rub(2.0, "USD", r) == 200.0
    assert amount_to_rub(50.0, "RUB", {}) == 50.0
    assert amount_to_rub(1.0, "XXX", {}) is None


def test_parse_to_datetime_msk_naive_date() -> None:
    dt = parse_to_datetime("2025-03-15")
    assert dt is not None
    assert format_msk_iso(dt) is not None
    assert "+03:00" in format_msk_iso(dt) or "-03:00" not in format_msk_iso(dt)


def test_normalize_unit_label() -> None:
    assert normalize_unit_label("шт") == "pcs"
    assert normalize_unit_label("  КГ ") == "kg"


def test_fuzzy_column_lookup() -> None:
    # Опечатка в имени колонки; fuzzy сопоставляет с ожидаемым ключом из маппинга.
    row = {"order_dat": "2025-01-10", "order_id": "X-1"}
    v = _lookup_row_value(row, "order_date", fuzzy_threshold=85)
    assert v == "2025-01-10"


def test_enrich_amount_rub_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    import datanorma.normalization.enrich as enrich_mod

    monkeypatch.setattr(enrich_mod, "get_cbr_rates_map", lambda _d: {"USD": 100.0})

    rows = [
        {
            "source_system": "t",
            "source_record_id": "1",
            "event_datetime": "2025-01-15",
            "amount": 2.5,
            "currency_code": "USD",
            "counterparty_name": None,
            "channel": None,
            "line_description": None,
            "status": None,
        }
    ]
    out, meta = enrich_canonical_rows(rows, fallback_rate_date=date(2025, 1, 15))
    assert out[0]["amount_rub"] == 250.0
    assert "cbr_dates" in meta
    assert out[0]["normalization_meta"]["cbr_rate_date"] == "2025-01-15"
