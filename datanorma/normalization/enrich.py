"""Обогащение канонических строк: даты в MSK, amount_rub по ЦБ, единицы, бизнес-поля."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy.engine import Engine

from datanorma.normalization.cbr_rates import (
    amount_to_rub,
    coerce_currency_code,
    get_cbr_rates_map,
    today_msk,
)
from datanorma.normalization.contacts import normalize_email, normalize_phone_ru
from datanorma.normalization.dates_msk import format_msk_iso, parse_to_datetime
from datanorma.normalization.person_name import parse_person_name
from datanorma.normalization.references import (
    load_country_codes,
    load_currency_codes,
    load_dim_status_map,
    load_unit_codes,
    normalize_country_code,
)
from datanorma.normalization.statuses import resolve_status
from datanorma.normalization.units import normalize_unit_label


def _rate_date_for_row(row: dict[str, Any], fallback: date) -> date:
    ed = row.get("event_datetime")
    dt = parse_to_datetime(ed)
    if dt is not None:
        return dt.date()
    return fallback


def _apply_business_enrichment(
    row: dict[str, Any],
    *,
    engine: Engine,
    status_map: dict[tuple[str, str, str], str],
    countries: set[str],
    units: set[str],
    currencies: set[str],
) -> list[dict[str, Any]]:
    fixes: list[dict[str, Any]] = []

    ph = row.get("contact_phone_e164")
    if ph is not None and str(ph).strip():
        n = normalize_phone_ru(str(ph))
        if n != str(ph).strip():
            fixes.append(
                {
                    "field": "contact_phone_e164",
                    "action": "phone_normalized",
                    "from": ph,
                    "to": n,
                }
            )
        row["contact_phone_e164"] = n

    em = row.get("contact_email")
    if em is not None and str(em).strip():
        n = normalize_email(str(em))
        if n != str(em).strip().lower():
            fixes.append(
                {
                    "field": "contact_email",
                    "action": "email_normalized",
                    "from": em,
                    "to": n,
                }
            )
        if n is None:
            fixes.append(
                {
                    "field": "contact_email",
                    "action": "email_invalid",
                    "from": em,
                    "to": None,
                }
            )
        row["contact_email"] = n

    cc_raw = row.get("country_code")
    if cc_raw is not None and str(cc_raw).strip():
        cc, fix = normalize_country_code(str(cc_raw), countries)
        row["country_code"] = cc
        if fix:
            fixes.append(fix)

    cur = row.get("currency_code")
    if cur is not None and str(cur).strip() and currencies:
        coerced = str(cur).strip().upper()
        if coerced and coerced not in currencies:
            fixes.append(
                {
                    "field": "currency_code",
                    "action": "currency_not_in_dim",
                    "from": cur,
                    "to": coerced,
                }
            )

    lu = row.get("line_unit_normalized")
    if lu is not None and str(lu).strip() and units:
        lu_s = str(lu).strip().lower()
        if lu_s not in units:
            fixes.append(
                {
                    "field": "line_unit_normalized",
                    "action": "unit_not_in_dim",
                    "from": lu,
                    "to": lu_s,
                }
            )

    if not row.get("person_full_name") and row.get("counterparty_name"):
        parsed = parse_person_name(row.get("counterparty_name"))
        if parsed.get("person_family_name") or parsed.get("person_given_name"):
            row["person_full_name"] = parsed.get("person_full_name")
            row["person_family_name"] = parsed.get("person_family_name")
            row["person_given_name"] = parsed.get("person_given_name")
            row["person_patronymic"] = parsed.get("person_patronymic")
            fixes.append(
                {
                    "field": "counterparty_name",
                    "action": "person_name_parsed",
                    "from": row.get("counterparty_name"),
                    "to": parsed.get("person_full_name"),
                    "quality": parsed.get("quality"),
                }
            )

    raw_st = row.get("status")
    if raw_st is not None and str(raw_st).strip():
        code = resolve_status(
            engine,
            "order",
            str(row.get("source_system") or ""),
            str(raw_st),
            cache=status_map,
        )
        if code:
            row["order_status_code"] = code
            fixes.append(
                {
                    "field": "status",
                    "action": "status_mapped",
                    "from": raw_st,
                    "to": code,
                    "dimension": "order",
                }
            )

    return fixes


def enrich_canonical_rows(
    rows: list[dict[str, Any]],
    *,
    fallback_rate_date: date | None = None,
    engine: Engine | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fallback = fallback_rate_date or today_msk()
    by_date: dict[date, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        by_date[_rate_date_for_row(r, fallback)].append(i)

    rates_cache: dict[date, dict[str, float]] = {}
    meta: dict[str, Any] = {"cbr_dates": sorted(d.isoformat() for d in by_date)}

    status_map: dict[tuple[str, str, str], str] = {}
    countries: set[str] = set()
    units: set[str] = set()
    currencies: set[str] = set()
    if engine is not None:
        status_map = load_dim_status_map(engine)
        countries = load_country_codes(engine)
        units = load_unit_codes(engine)
        currencies = load_currency_codes(engine)

    out = [dict(r) for r in rows]
    for d, idxs in by_date.items():
        if d not in rates_cache:
            rates_cache[d] = get_cbr_rates_map(d)
        rates = rates_cache[d]
        for i in idxs:
            row = out[i]
            dt = parse_to_datetime(row.get("event_datetime"))
            row["event_datetime"] = format_msk_iso(dt)
            cur0 = row.get("currency_code")
            if cur0 is not None and str(cur0).strip():
                row["currency_code"] = coerce_currency_code(str(cur0))
            row["amount_rub"] = amount_to_rub(
                row.get("amount"),
                row.get("currency_code"),
                rates,
            )
            row["cbr_rate_date"] = d.isoformat()
            lud = row.get("line_unit_raw")
            if lud is not None:
                row["line_unit_normalized"] = normalize_unit_label(str(lud))
            elif "line_unit_normalized" not in row:
                row["line_unit_normalized"] = None
            prev = row.get("normalization_meta") or {}
            prev_fixes = list(prev.get("fixes") or [])
            base_meta = {
                "event_timezone": "Europe/Moscow",
                "cbr_rate_date": d.isoformat(),
                "rates_keys_count": len(rates),
            }
            if engine is not None:
                biz_fixes = _apply_business_enrichment(
                    row,
                    engine=engine,
                    status_map=status_map,
                    countries=countries,
                    units=units,
                    currencies=currencies,
                )
                base_meta["fixes"] = prev_fixes + biz_fixes
            else:
                base_meta["fixes"] = prev_fixes
            row["normalization_meta"] = {**{k: v for k, v in prev.items() if k != "fixes"}, **base_meta}

    return out, meta
