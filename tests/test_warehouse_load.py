"""Тесты подготовки строк для warehouse (без обязательного PostgreSQL)."""

from __future__ import annotations

from datetime import date, datetime, timezone

from datanorma.warehouse.load import _parse_date, _parse_ts, _row_to_payload


def test_parse_ts_iso_z() -> None:
    dt = _parse_ts("2025-01-10T12:00:00Z")
    assert dt is not None
    assert dt.tzinfo is not None


def test_parse_date_iso() -> None:
    assert _parse_date("2025-03-15") == date(2025, 3, 15)


def test_row_to_payload_skips_empty_keys() -> None:
    now = datetime.now(timezone.utc)
    assert _row_to_payload({"source_system": "", "source_record_id": "1"}, now) is None
    assert _row_to_payload({"source_system": "1c", "source_record_id": ""}, now) is None


def test_row_to_payload_maps_fields() -> None:
    now = datetime.now(timezone.utc)
    p = _row_to_payload(
        {
            "source_system": "ozon",
            "source_record_id": "p:sku",
            "event_datetime": "2025-01-01T00:00:00+03:00",
            "amount": 10.5,
            "amount_rub": 10.5,
            "currency_code": "RUB",
            "channel": "marketplace",
            "status": "ok",
            "cbr_rate_date": "2025-01-01",
            "line_unit_normalized": None,
            "counterparty_name": None,
            "line_description": "x",
        },
        now,
    )
    assert p is not None
    assert p["source_system"] == "ozon"
    assert p["amount_rub"] == 10.5
    assert p["currency_code"] == "RUB"
    assert p["_ingest_loaded_at"] == now


def test_row_to_payload_includes_business_columns() -> None:
    now = datetime.now(timezone.utc)
    p = _row_to_payload(
        {
            "source_system": "ozon",
            "source_record_id": "x",
            "event_datetime": "2025-01-01T00:00:00+03:00",
            "amount": 1,
            "amount_rub": 1,
            "currency_code": "RUB",
            "person_family_name": "Иванов",
            "contact_phone_e164": "+79031234567",
            "contact_email": "a@b.co",
            "country_code": "ru",
            "order_status_code": "DONE",
            "line_unit_normalized": None,
            "counterparty_name": None,
            "line_description": None,
            "channel": None,
            "status": None,
            "cbr_rate_date": "2025-01-01",
        },
        now,
    )
    assert p is not None
    assert p["person_family_name"] == "Иванов"
    assert p["contact_phone_e164"] == "+79031234567"
    assert p["contact_email"] == "a@b.co"
    assert p["country_code"] == "RU"
    assert p["order_status_code"] == "DONE"
