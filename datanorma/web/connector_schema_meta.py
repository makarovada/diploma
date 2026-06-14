"""Метаданные схемы коннекторов для мастера подключения (layout, сущности, sync defaults)."""

from __future__ import annotations

from typing import Any, Literal

SchemaLayout = Literal["flat", "entities"]

_FLAT_CONNECTORS: frozenset[str] = frozenset({"google_sheet"})

_ENTITY_LABELS: dict[str, dict[str, str]] = {
    "yandex_metrika": {
        "summary": "Сводка",
        "visits": "Визиты",
        "hits": "Просмотры",
        "goals_reaches": "Достижения целей",
    },
    "bitrix24": {
        "crm_deals": "Сделки",
        "crm_contacts": "Контакты",
        "crm_leads": "Лиды",
        "crm_companies": "Компании",
        "crm_tasks": "Задачи",
        "crm_activities": "Дела",
    },
    "amocrm": {
        "leads": "Сделки",
        "contacts": "Контакты",
        "companies": "Компании",
        "tasks": "Задачи",
        "pipelines": "Воронки",
    },
    "moysklad": {
        "demand": "Отгрузки",
        "customerorder": "Заказы покупателей",
        "product": "Товары",
        "counterparty": "Контрагенты",
        "invoiceout": "Счета покупателям",
        "stock": "Остатки",
    },
}


def _code_snake(code: str) -> str:
    return code.strip().lower().replace("-", "_")


def _enrich_stream_default(row: dict[str, Any]) -> dict[str, Any]:
    from datanorma.elt.sync_mode_policy import destination_sync_mode_for_legacy

    out = dict(row)
    sm = str(out.get("sync_mode") or "full_refresh")
    out.setdefault("destination_sync_mode", destination_sync_mode_for_legacy(sm))
    out.setdefault("primary_key", out.get("primary_key"))
    return out


def connector_stream_defaults(code: str) -> list[dict[str, Any]]:
    """Дефолты sync_mode / cursor_field / destination_sync_mode per internal stream_name."""
    c = _code_snake(code)
    raw: list[dict[str, Any]] = []
    if c == "google_sheet":
        raw = [
            {
                "stream_name": "orders",
                "sync_mode": "incremental",
                "cursor_field": "order_id",
                "destination_sync_mode": "append_dedup",
                "primary_key": "order_id",
            }
        ]
    elif c == "yandex_metrika":
        raw = [
            {"stream_name": "summary", "sync_mode": "incremental", "cursor_field": "date"},
            {"stream_name": "visits", "sync_mode": "incremental", "cursor_field": "date_time"},
            {"stream_name": "hits", "sync_mode": "incremental", "cursor_field": "date_time"},
            {"stream_name": "goals_reaches", "sync_mode": "incremental", "cursor_field": "reach_datetime"},
        ]
    elif c == "bitrix24":
        raw = [
            {"stream_name": "crm_deals", "sync_mode": "incremental", "cursor_field": "DATE_MODIFY"},
            {"stream_name": "crm_contacts", "sync_mode": "incremental", "cursor_field": "DATE_MODIFY"},
            {"stream_name": "crm_leads", "sync_mode": "incremental", "cursor_field": "DATE_MODIFY"},
            {"stream_name": "crm_companies", "sync_mode": "incremental", "cursor_field": "DATE_MODIFY"},
            {"stream_name": "crm_tasks", "sync_mode": "incremental", "cursor_field": "CHANGED_DATE"},
            {"stream_name": "crm_activities", "sync_mode": "incremental", "cursor_field": "LAST_UPDATED"},
        ]
    elif c == "amocrm":
        raw = [
            {"stream_name": "leads", "sync_mode": "incremental", "cursor_field": "updated_at"},
            {"stream_name": "contacts", "sync_mode": "incremental", "cursor_field": "updated_at"},
            {"stream_name": "companies", "sync_mode": "incremental", "cursor_field": "updated_at"},
            {"stream_name": "tasks", "sync_mode": "incremental", "cursor_field": "complete_till"},
            {"stream_name": "pipelines", "sync_mode": "full_refresh", "cursor_field": None},
        ]
    elif c == "moysklad":
        raw = [
            {"stream_name": "demand", "sync_mode": "incremental", "cursor_field": "updated"},
            {"stream_name": "customerorder", "sync_mode": "incremental", "cursor_field": "updated"},
            {"stream_name": "product", "sync_mode": "incremental", "cursor_field": "updated"},
            {"stream_name": "counterparty", "sync_mode": "incremental", "cursor_field": "updated"},
            {"stream_name": "invoiceout", "sync_mode": "incremental", "cursor_field": "updated"},
            {"stream_name": "stock", "sync_mode": "full_refresh", "cursor_field": None},
        ]
    elif c == "rest_builder":
        raw = [{"stream_name": "rest_stream", "sync_mode": "full_refresh", "cursor_field": None}]
    return _with_enriched_defaults(raw)


def _with_enriched_defaults(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_enrich_stream_default(r) for r in rows]


def connector_schema_layout(code: str, *, discovered_stream_count: int | None = None) -> SchemaLayout:
    c = _code_snake(code)
    if c in _FLAT_CONNECTORS:
        return "flat"
    if discovered_stream_count is not None and discovered_stream_count <= 1:
        return "flat"
    return "entities"


def connector_entity_labels(code: str) -> dict[str, str]:
    c = _code_snake(code)
    return dict(_ENTITY_LABELS.get(c, {}))


def connector_schema_meta(code: str, *, discovered_stream_count: int | None = None) -> dict[str, Any]:
    """Полные метаданные для UI мастера и discover."""
    c = _code_snake(code)
    streams = connector_stream_defaults(c)
    layout = connector_schema_layout(c, discovered_stream_count=discovered_stream_count)
    labels = connector_entity_labels(c)
    if not labels and streams:
        labels = {s["stream_name"]: s["stream_name"].replace("_", " ").title() for s in streams}
    return {
        "layout": layout,
        "entity_labels": labels,
        "stream_defaults": streams,
    }


def stream_default_for(code: str, stream_name: str) -> dict[str, Any]:
    """Sync defaults for one internal stream_name."""
    for s in connector_stream_defaults(code):
        if s["stream_name"] == stream_name:
            return s
    return _enrich_stream_default(
        {"stream_name": stream_name, "sync_mode": "full_refresh", "cursor_field": None}
    )
