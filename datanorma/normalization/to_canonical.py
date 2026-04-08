"""Сведение разных источников к канонической модели (YAML + fuzzy + обогащение ЦБ/дат)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from datanorma.config import get_settings
from datanorma.normalization.enrich import enrich_canonical_rows


def load_source_mappings() -> dict[str, Any]:
    path = get_settings().resolved_source_mappings_path()
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


def _lookup_row_value(
    row: dict[str, Any],
    configured_raw: str,
    *,
    fuzzy_threshold: int,
) -> Any:
    if configured_raw in row:
        return row[configured_raw]
    if fuzzy_threshold <= 0:
        return None
    from rapidfuzz import fuzz

    keys = [str(k) for k in row if k is not None]
    if not keys:
        return None
    cr = configured_raw.lower()
    best_k: str | None = None
    best_s = -1
    for k in keys:
        s = fuzz.ratio(cr, k.lower())
        if s > best_s:
            best_s = s
            best_k = k
    if best_k is not None and best_s >= fuzzy_threshold:
        return row.get(best_k)
    return None


def _map_tabular_row(
    row: dict[str, Any],
    field_map: dict[str, str],
    source_system: str,
    fuzzy_threshold: int = 0,
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
        val = _lookup_row_value(row, raw_key, fuzzy_threshold=fuzzy_threshold)
        if val is None:
            continue
        if canon_key == "event_datetime":
            out["event_datetime"] = _parse_datetime(val)
        elif canon_key == "amount":
            out["amount"] = _coerce_amount(val)
        elif canon_key == "currency_code":
            out["currency_code"] = str(val).strip().upper() if val != "" else None
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
            cc = prod.get("currency_code")
            rows.append(
                {
                    "source_system": source_system,
                    "source_record_id": rid,
                    "event_datetime": base_time,
                    "amount": line_amount,
                    "currency_code": str(cc).strip().upper() if cc else None,
                    "counterparty_name": None,
                    "channel": "marketplace",
                    "line_description": prod.get("name"),
                    "status": status,
                }
            )
    return rows


def _fuzzy_threshold_for_source(mappings: dict[str, Any], source_cfg: dict[str, Any]) -> int:
    opts = mappings.get("options") or {}
    default = int(opts.get("fuzzy_column_threshold", 0))
    return int(source_cfg.get("fuzzy_column_threshold", default))


def build_canonical_sales_rows(
    raw_ozon: dict[str, Any],
    raw_1c: dict[str, Any],
    raw_google: dict[str, Any],
    mappings: dict[str, Any] | None = None,
    *,
    batch_extracted_at: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    mappings = mappings or load_source_mappings()
    sources_cfg = mappings.get("sources") or {}
    all_rows: list[dict[str, Any]] = []
    stats: dict[str, Any] = {"canonical": mappings.get("canonical"), "per_source": {}}

    oz_cfg = sources_cfg.get("ozon") or {}
    if oz_cfg.get("handler") == "ozon_fbs_postings":
        oz_rows = _ozon_to_rows(raw_ozon.get("postings") or [], raw_ozon.get("source_system", "ozon"))
        all_rows.extend(oz_rows)
        stats["per_source"]["ozon"] = {"rows": len(oz_rows)}

    onec_cfg = sources_cfg.get("1c") or {}
    if onec_cfg.get("handler") == "column_map":
        fm = onec_cfg.get("fields") or {}
        thr = _fuzzy_threshold_for_source(mappings, onec_cfg)
        onec_out: list[dict[str, Any]] = []
        for row in raw_1c.get("rows") or []:
            onec_out.append(_map_tabular_row(row, fm, raw_1c.get("source_system", "1c"), thr))
        all_rows.extend(onec_out)
        stats["per_source"]["1c"] = {"rows": len(onec_out), "fuzzy_threshold": thr}

    gs_cfg = sources_cfg.get("google_sheet") or {}
    if gs_cfg.get("handler") == "column_map":
        fm = gs_cfg.get("fields") or {}
        thr = _fuzzy_threshold_for_source(mappings, gs_cfg)
        gs_out: list[dict[str, Any]] = []
        for row in raw_google.get("rows") or []:
            gs_out.append(
                _map_tabular_row(row, fm, raw_google.get("source_system", "google_sheet"), thr)
            )
        all_rows.extend(gs_out)
        stats["per_source"]["google_sheet"] = {"rows": len(gs_out), "fuzzy_threshold": thr}

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

    deduped, enrich_meta = enrich_canonical_rows(deduped)
    stats["enrich"] = enrich_meta

    if batch_extracted_at:
        for r in deduped:
            r.setdefault("_airbyte_extracted_at", batch_extracted_at)

    return deduped, stats
