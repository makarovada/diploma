"""Сведение разных источников к канонической модели (конфигурируемый column_map + стратегии)."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_MAPPINGS = _PACKAGE_DIR / "schemas" / "source_mappings.yaml"


def load_source_mappings() -> dict[str, Any]:
    path = Path(os.environ.get("DATANORMA_SOURCE_MAPPINGS_PATH", "").strip() or _DEFAULT_MAPPINGS)
    if not path.is_file():
        raise FileNotFoundError(
            f"Файл маппинга не найден: {path}. Задайте DATANORMA_SOURCE_MAPPINGS_PATH или восстановите schemas/source_mappings.yaml."
        )
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _parse_datetime(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    s = str(value).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s).isoformat()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).isoformat()
        except ValueError:
            continue
    return s


def _coerce_amount(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _map_tabular_row(
    row: dict[str, Any],
    field_map: dict[str, str],
    source_system: str,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "source_system": source_system,
        "source_record_id": None,
        "event_datetime": None,
        "amount": None,
        "currency_code": None,
        "counterparty_name": None,
        "channel": None,
        "line_description": None,
        "status": None,
    }
    for raw_key, canon_key in field_map.items():
        if raw_key not in row:
            continue
        val = row[raw_key]
        if canon_key == "event_datetime":
            out["event_datetime"] = _parse_datetime(val)
        elif canon_key == "amount":
            out["amount"] = _coerce_amount(val)
        else:
            out[canon_key] = val if val != "" else None
    return out


def _ozon_to_rows(postings: list[dict], source_system: str = "ozon") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in postings:
        posting_number = str(p.get("posting_number", ""))
        status = p.get("status")
        base_time = _parse_datetime(p.get("in_process_at"))
        products = p.get("products") or []
        if not products:
            rid = posting_number or str(p.get("order_id", ""))
            rows.append(
                {
                    "source_system": source_system,
                    "source_record_id": rid,
                    "event_datetime": base_time,
                    "amount": None,
                    "currency_code": None,
                    "counterparty_name": None,
                    "channel": "marketplace",
                    "line_description": None,
                    "status": status,
                }
            )
            continue
        for prod in products:
            qty = int(prod.get("quantity") or 1)
            price = _coerce_amount(prod.get("price"))
            line_amount = price * qty if price is not None else None
            offer = str(prod.get("offer_id", ""))
            rid = f"{posting_number}:{offer}" if posting_number else str(p.get("order_id", ""))
            rows.append(
                {
                    "source_system": source_system,
                    "source_record_id": rid,
                    "event_datetime": base_time,
                    "amount": line_amount,
                    "currency_code": prod.get("currency_code"),
                    "counterparty_name": None,
                    "channel": "marketplace",
                    "line_description": prod.get("name"),
                    "status": status,
                }
            )
    return rows


def build_canonical_sales_rows(
    raw_ozon: dict[str, Any],
    raw_1c: dict[str, Any],
    raw_google: dict[str, Any],
    mappings: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    mappings = mappings or load_source_mappings()
    sources_cfg = mappings.get("sources") or {}
    all_rows: list[dict[str, Any]] = []
    stats: dict[str, Any] = {"canonical": mappings.get("canonical"), "per_source": {}}

    # Ozon
    oz_cfg = sources_cfg.get("ozon") or {}
    if oz_cfg.get("handler") == "ozon_fbs_postings":
        oz_rows = _ozon_to_rows(raw_ozon.get("postings") or [], raw_ozon.get("source_system", "ozon"))
        all_rows.extend(oz_rows)
        stats["per_source"]["ozon"] = {"rows": len(oz_rows)}

    # 1C tabular
    onec_cfg = sources_cfg.get("1c") or {}
    if onec_cfg.get("handler") == "column_map":
        fm = onec_cfg.get("fields") or {}
        onec_out: list[dict[str, Any]] = []
        for row in raw_1c.get("rows") or []:
            onec_out.append(_map_tabular_row(row, fm, raw_1c.get("source_system", "1c")))
        all_rows.extend(onec_out)
        stats["per_source"]["1c"] = {"rows": len(onec_out)}

    # Google sheet tabular
    gs_cfg = sources_cfg.get("google_sheet") or {}
    if gs_cfg.get("handler") == "column_map":
        fm = gs_cfg.get("fields") or {}
        gs_out: list[dict[str, Any]] = []
        for row in raw_google.get("rows") or []:
            gs_out.append(_map_tabular_row(row, fm, raw_google.get("source_system", "google_sheet")))
        all_rows.extend(gs_out)
        stats["per_source"]["google_sheet"] = {"rows": len(gs_out)}

    # Дедуп: одинаковый ключ (источник + id строки)
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for r in all_rows:
        sid = str(r.get("source_record_id") or "")
        key = (str(r.get("source_system")), sid)
        if sid:
            if key in seen:
                continue
            seen.add(key)
        deduped.append(r)

    stats["rows_in"] = len(all_rows)
    stats["rows_after_dedup"] = len(deduped)
    return deduped, stats

