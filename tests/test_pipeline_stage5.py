"""Этап 5: дедуп, склейка raw→canonical, ЦБ (Nominal), мок enrich без сети."""

from __future__ import annotations

import pytest

from datanorma.normalization.cbr_rates import amount_to_rub, coerce_currency_code, parse_cbr_daily_xml
from datanorma.normalization.to_canonical import _map_tabular_row, build_canonical_sales_rows


def test_parse_cbr_respects_nominal() -> None:
    xml = """<?xml version="1.0"?>
    <ValCurs Date="01.01.2025">
      <Valute>
        <CharCode>JPY</CharCode><Nominal>100</Nominal><Value>65,50</Value>
      </Valute>
    </ValCurs>"""
    rates = parse_cbr_daily_xml(xml)
    assert pytest.approx(rates["JPY"], rel=1e-9) == 0.655


def test_coerce_currency_code_rub_aliases() -> None:
    assert coerce_currency_code("rub") == "RUB"
    assert coerce_currency_code("₽") == "RUB"
    assert coerce_currency_code("USD") == "USD"


def test_amount_to_rub_with_nominal_rate() -> None:
    rates = {"JPY": 0.655}
    assert amount_to_rub(1000.0, "JPY", rates) == pytest.approx(655.0)


def test_map_tabular_1c_style_row() -> None:
    row = {
        "ДатаДокумента": "2025-02-01",
        "Номер": "DOC-1",
        "Контрагент": "Клиент",
        "СуммаДокумента": "1000,50",
        "Валюта": "rub",
        "Комментарий": "тест",
    }
    fm = {
        "ДатаДокумента": "event_datetime",
        "Номер": "source_record_id",
        "Контрагент": "counterparty_name",
        "СуммаДокумента": "amount",
        "Валюта": "currency_code",
        "Комментарий": "line_description",
    }
    out = _map_tabular_row(row, fm, "1c", fuzzy_threshold=0)
    assert out["source_record_id"] == "DOC-1"
    assert out["amount"] == pytest.approx(1000.50)
    assert out["currency_code"] == "RUB"


def test_dedup_same_source_record_id(monkeypatch: pytest.MonkeyPatch) -> None:
    import datanorma.normalization.to_canonical as tc

    def _noop_enrich(rows, fallback_rate_date=None, engine=None):
        return [dict(r) for r in rows], {"cbr_dates": []}

    monkeypatch.setattr(tc, "enrich_canonical_rows", _noop_enrich)

    raw_ozon = {
        "source_system": "ozon",
        "postings": [
            {
                "posting_number": "P1",
                "in_process_at": "2025-01-01T00:00:00Z",
                "status": "x",
                "products": [
                    {
                        "price": "10",
                        "quantity": 1,
                        "currency_code": "RUB",
                        "offer_id": "SKU",
                        "name": "A",
                    }
                ],
            },
            {
                "posting_number": "P1",
                "in_process_at": "2025-01-01T00:00:00Z",
                "status": "x",
                "products": [
                    {
                        "price": "99",
                        "quantity": 1,
                        "currency_code": "RUB",
                        "offer_id": "SKU",
                        "name": "B",
                    }
                ],
            },
        ],
    }
    raw_1c = {"source_system": "1c", "rows": []}
    raw_google = {"source_system": "google_sheet", "rows": []}

    mappings = {
        "version": 1,
        "canonical": "canonical_sales_v1",
        "sources": {
            "ozon": {"handler": "ozon_fbs_postings"},
            "1c": {"handler": "column_map", "fields": {}},
            "google_sheet": {"handler": "column_map", "fields": {}},
        },
    }

    rows, stats = build_canonical_sales_rows(raw_ozon, raw_1c, raw_google, mappings=mappings)
    assert stats["rows_in"] == 2
    assert stats["rows_after_dedup"] == 1
    assert len(rows) == 1


def test_build_merges_three_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    import datanorma.normalization.to_canonical as tc

    monkeypatch.setattr(
        tc,
        "enrich_canonical_rows",
        lambda rows, fallback_rate_date=None, engine=None: (
            [dict(r) for r in rows],
            {"cbr_dates": []},
        ),
    )

    raw_ozon = {
        "source_system": "ozon",
        "postings": [
            {
                "posting_number": "PX",
                "in_process_at": "2025-01-02T00:00:00Z",
                "status": "delivered",
                "products": [
                    {
                        "price": "1",
                        "quantity": 1,
                        "currency_code": "RUB",
                        "offer_id": "o1",
                        "name": "t",
                    }
                ],
            }
        ],
    }
    raw_1c = {
        "source_system": "1c",
        "rows": [
            {
                "ДатаДокумента": "2025-01-03",
                "Номер": "УТ-9",
                "Контрагент": "X",
                "СуммаДокумента": "500",
                "Валюта": "RUB",
                "Комментарий": "",
            }
        ],
    }
    raw_google = {
        "source_system": "google_sheet",
        "rows": [
            {
                "order_id": "GS-1",
                "order_date": "2025-01-04",
                "customer_name": "Y",
                "amount": "250",
                "currency": "RUB",
                "channel": "online",
            }
        ],
    }
    mappings = {
        "version": 1,
        "canonical": "canonical_sales_v1",
        "options": {"fuzzy_column_threshold": 0},
        "sources": {
            "ozon": {"handler": "ozon_fbs_postings"},
            "1c": {
                "handler": "column_map",
                "fuzzy_column_threshold": 0,
                "fields": {
                    "ДатаДокумента": "event_datetime",
                    "Номер": "source_record_id",
                    "Контрагент": "counterparty_name",
                    "СуммаДокумента": "amount",
                    "Валюта": "currency_code",
                    "Комментарий": "line_description",
                },
            },
            "google_sheet": {
                "handler": "column_map",
                "fuzzy_column_threshold": 0,
                "fields": {
                    "order_id": "source_record_id",
                    "order_date": "event_datetime",
                    "customer_name": "counterparty_name",
                    "amount": "amount",
                    "currency": "currency_code",
                    "channel": "channel",
                },
            },
        },
    }
    rows, stats = build_canonical_sales_rows(raw_ozon, raw_1c, raw_google, mappings=mappings)
    systems = {r["source_system"] for r in rows}
    assert systems == {"ozon", "1c", "google_sheet"}
    assert stats["per_source"]["ozon"]["rows"] == 1
    assert stats["per_source"]["1c"]["rows"] == 1
    assert stats["per_source"]["google_sheet"]["rows"] == 1
