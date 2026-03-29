"""Обогащение канонических строк: даты в MSK, amount_rub по ЦБ, опционально единицы."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from datanorma.normalization.cbr_rates import (
    amount_to_rub,
    coerce_currency_code,
    get_cbr_rates_map,
    today_msk,
)
from datanorma.normalization.dates_msk import format_msk_iso, parse_to_datetime
from datanorma.normalization.units import normalize_unit_label


def _rate_date_for_row(row: dict[str, Any], fallback: date) -> date:
    ed = row.get("event_datetime")
    dt = parse_to_datetime(ed)
    if dt is not None:
        return dt.date()
    return fallback


def enrich_canonical_rows(
    rows: list[dict[str, Any]],
    *,
    fallback_rate_date: date | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fallback = fallback_rate_date or today_msk()
    by_date: dict[date, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        by_date[_rate_date_for_row(r, fallback)].append(i)

    rates_cache: dict[date, dict[str, float]] = {}
    meta: dict[str, Any] = {"cbr_dates": sorted(d.isoformat() for d in by_date)}

    out = [dict(r) for r in rows]
    for d, idxs in by_date.items():
        if d not in rates_cache:
            rates_cache[d] = get_cbr_rates_map(d)
        rates = rates_cache[d]
        for i in idxs:
            row = out[i]
            dt = parse_to_datetime(row.get("event_datetime"))
            row["event_datetime"] = format_msk_iso(dt)
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

    return out, meta
