"""Дефолтные правила нормализации из JSON Schema (по имени колонок)."""

from __future__ import annotations

import re
from typing import Any

from datanorma.normalization.rules import ColumnRule, StreamRules


def _snake_case(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_]+", "_", str(name).strip())
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return s.lower().strip("_") or "field"


def default_column_type_from_name_and_schema(source_field: str, property_schema: dict[str, Any]) -> str:
    name = source_field.lower()

    # Обязательные кейсы из инструкции
    if "phone" in name or "телефон" in name:
        return "phone"
    if "inn" in name or "инн" in name:
        return "inn"
    if "kpp" in name or "кпп" in name:
        return "kpp"
    if "ogrn" in name or "огрн" in name:
        return "ogrn"
    if "email" in name or "e_mail" in name or "почта" in name or name.endswith("mail"):
        return "email"

    # Валюта: сначала код, потом суммы (по имени)
    if "amount" in name or "сумма" in name or "price" in name or "цена" in name or "выручк" in name:
        return "currency_amount"
    if "opportunity" in name:
        return "currency_amount"
    if "currency" in name or "валют" in name:
        return "currency_code"

    # Даты: в текущей json_schema нет format, поэтому опираемся на имя
    if "datetime" in name or "date_time" in name or "date-time" in name or "time" in name:
        return "datetime"
    if "date_create" in name or "date_modify" in name:
        return "datetime"
    if name.endswith("_at") or "created" in name or "updated" in name or "in_process" in name:
        return "datetime"
    if "date" in name:
        return "date"

    # Типы по JSON Schema
    t = property_schema.get("type")
    if t == "integer":
        return "integer"
    if t == "number":
        return "number"
    if t == "boolean":
        return "boolean"
    if t in ("object", "array"):
        return "json"

    return "string"


def default_stream_rules_from_json_schema(
    *,
    stream_name: str,
    json_schema: dict[str, Any],
    sync_mode: str = "full_refresh",
    cursor_field: str | None = None,
    primary_key: list[str] | None = None,
) -> StreamRules:
    props = json_schema.get("properties") or {}
    columns: list[ColumnRule] = []

    for src_field, prop_schema in props.items():
        if not isinstance(prop_schema, dict):
            prop_schema = {"type": "string"}

        target_field = _snake_case(str(src_field))
        col_type = default_column_type_from_name_and_schema(str(src_field), prop_schema)

        params: dict[str, Any] = {}
        if col_type == "currency_amount":
            params["decimal_separator"] = ","
            params["thousands_separator"] = " "
        if col_type == "phone":
            params["phone_default_country"] = "RU"

        columns.append(
            ColumnRule(
                source_field=str(src_field),
                target_field=target_field,
                type=col_type,  # type: ignore[arg-type]
                nullable=True,
                required=False,
                **params,
            )
        )

    pk = primary_key if primary_key is not None else []
    if cursor_field and not pk:
        pk = [cursor_field]

    # Если batch пустой, в json_schema не будет properties, но PK всё равно нужен для таблицы.
    existing_targets = {c.target_field for c in columns}
    for pk_field in pk:
        if pk_field not in existing_targets:
            columns.append(
                ColumnRule(
                    source_field=pk_field,
                    target_field=pk_field,
                    type="string",  # fallback для пустой schema
                    nullable=True,
                    required=False,
                )
            )

    dedup = bool(pk)
    eff_sync_mode = "incremental" if cursor_field else sync_mode
    return StreamRules(
        stream_name=stream_name,
        primary_key=pk,
        cursor_field=cursor_field,
        sync_mode=eff_sync_mode,  # type: ignore[arg-type]
        columns=columns,
        drop_unknown_columns=False,
        deduplicate=dedup,
    )

