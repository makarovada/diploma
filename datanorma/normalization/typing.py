"""Утилиты типизации значений и универсального UPSERT для normalized-слоя."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import Table, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

from datanorma.normalization.rules import ColumnRule, StreamRules


def _to_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value).strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _to_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    s = str(value).strip()
    if not s:
        return None
    return date.fromisoformat(s[:10])


def cast_string(raw: Any, *, trim: bool = True, lowercase: bool = False, uppercase: bool = False) -> tuple[str | None, str | None]:
    """Приведение значения к строке."""
    if raw is None:
        return None, None
    out = str(raw)
    if trim:
        out = out.strip()
    if out == "":
        return None, None
    if lowercase:
        out = out.lower()
    if uppercase:
        out = out.upper()
    return out, None


def cast_integer(raw: Any) -> tuple[int | None, str | None]:
    """Приведение значения к целому числу."""
    if raw is None or raw == "":
        return None, None
    try:
        return int(str(raw).strip()), None
    except (ValueError, TypeError, InvalidOperation) as exc:
        return None, str(exc)


def cast_number(raw: Any, *, decimal_separator: str | None = None, thousands_separator: str | None = None, scale_factor: float | None = None) -> tuple[Decimal | None, str | None]:
    """Приведение значения к Decimal с учетом разделителей."""
    if raw is None or raw == "":
        return None, None
    try:
        if isinstance(raw, (int, float, Decimal)):
            out = Decimal(str(raw))
        else:
            s = str(raw).strip()
            if thousands_separator:
                s = s.replace(thousands_separator, "")
            else:
                s = s.replace(" ", "")
            if decimal_separator and decimal_separator != ".":
                s = s.replace(decimal_separator, ".")
            else:
                s = s.replace(",", ".")
            out = Decimal(s)
        if scale_factor is not None:
            out *= Decimal(str(scale_factor))
        return out, None
    except (InvalidOperation, ValueError, TypeError) as exc:
        return None, str(exc)


def cast_boolean(raw: Any) -> tuple[bool | None, str | None]:
    """Приведение значения к bool."""
    if raw is None or raw == "":
        return None, None
    s = str(raw).strip().lower()
    if s in ("1", "true", "yes", "y", "да"):
        return True, None
    if s in ("0", "false", "no", "n", "нет"):
        return False, None
    return None, f"unsupported bool literal: {raw!r}"


def cast_date(raw: Any, *, date_formats: list[str] | None = None) -> tuple[date | None, str | None]:
    """Приведение значения к date."""
    if raw is None or raw == "":
        return None, None
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw, None
    s = str(raw).strip()
    if not s:
        return None, None
    if date_formats:
        for fmt in date_formats:
            try:
                return datetime.strptime(s, fmt).date(), None
            except ValueError:
                continue
    try:
        return date.fromisoformat(s[:10]), None
    except ValueError as exc:
        return None, str(exc)


def cast_datetime(raw: Any, *, date_formats: list[str] | None = None) -> tuple[datetime | None, str | None]:
    """Приведение значения к datetime (timezone-aware)."""
    if raw is None or raw == "":
        return None, None
    if isinstance(raw, datetime):
        out = raw
    else:
        s = str(raw).strip()
        if not s:
            return None, None
        if date_formats:
            for fmt in date_formats:
                try:
                    out = datetime.strptime(s, fmt)
                    break
                except ValueError:
                    continue
            else:
                out = _to_datetime(s)
        else:
            out = _to_datetime(s)
    if out is None:
        return None, "datetime parse failed"
    if out.tzinfo is None:
        out = out.replace(tzinfo=timezone.utc)
    return out, None


def cast_currency_amount(raw: Any, *, decimal_separator: str | None = None, thousands_separator: str | None = None, scale_factor: float | None = None) -> tuple[Decimal | None, str | None]:
    """Приведение суммы к Decimal."""
    return cast_number(
        raw,
        decimal_separator=decimal_separator,
        thousands_separator=thousands_separator,
        scale_factor=scale_factor,
    )


def cast_phone(raw: Any) -> tuple[str | None, str | None]:
    """Нормализация телефона в простом E.164-подобном формате."""
    if raw is None or raw == "":
        return None, None
    s = "".join(ch for ch in str(raw) if ch.isdigit() or ch == "+")
    if not s:
        return None, "empty phone"
    if s.startswith("8") and len(s) == 11:
        s = "+7" + s[1:]
    if not s.startswith("+"):
        s = "+" + s
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) < 10:
        return None, "phone too short"
    return s, None


def cast_email(raw: Any) -> tuple[str | None, str | None]:
    """Проверка и нормализация email."""
    s, err = cast_string(raw, trim=True, lowercase=True)
    if err or s is None:
        return s, err
    if "@" not in s or s.startswith("@") or s.endswith("@"):
        return None, "invalid email"
    return s, None


def cast_inn(raw: Any) -> tuple[str | None, str | None]:
    """Приведение ИНН к строке с валидацией длины."""
    if raw is None or raw == "":
        return None, None
    s = "".join(ch for ch in str(raw) if ch.isdigit())
    if len(s) not in (10, 12):
        return None, "invalid INN length"
    return s, None


def cast_enum(raw: Any, *, enum_map: dict[str, str] | None = None, enum_default: str | None = None) -> tuple[str | None, str | None]:
    """Нормализация перечисления через словарь соответствий."""
    if raw is None or raw == "":
        return enum_default, None
    key = str(raw).strip()
    enum_map = enum_map or {}
    if key in enum_map:
        return enum_map[key], None
    if enum_default is not None:
        return enum_default, None
    return None, f"unknown enum value: {key}"


def cast_value(rule: ColumnRule, raw: Any) -> tuple[Any, dict[str, Any] | None]:
    """Каст одного значения в соответствии с ColumnRule."""
    if raw is None or raw == "":
        if rule.required:
            return None, {"field": rule.target_field, "error_code": "required_missing", "raw_value": raw}
        return None, None

    if rule.type == "string":
        value, err = cast_string(raw, trim=rule.trim, lowercase=rule.lowercase, uppercase=rule.uppercase)
    elif rule.type == "integer":
        value, err = cast_integer(raw)
    elif rule.type == "number":
        value, err = cast_number(raw, decimal_separator=rule.decimal_separator, thousands_separator=rule.thousands_separator, scale_factor=rule.scale_factor)
    elif rule.type == "boolean":
        value, err = cast_boolean(raw)
    elif rule.type == "date":
        value, err = cast_date(raw, date_formats=rule.date_formats)
    elif rule.type == "datetime":
        value, err = cast_datetime(raw, date_formats=rule.date_formats)
    elif rule.type == "currency_amount":
        value, err = cast_currency_amount(raw, decimal_separator=rule.decimal_separator, thousands_separator=rule.thousands_separator, scale_factor=rule.scale_factor)
    elif rule.type == "currency_code":
        value, err = cast_string(raw, trim=True, uppercase=True)
    elif rule.type == "phone":
        value, err = cast_phone(raw)
    elif rule.type == "email":
        value, err = cast_email(raw)
    elif rule.type == "inn":
        value, err = cast_inn(raw)
    elif rule.type in ("kpp", "ogrn"):
        value, err = cast_string(raw, trim=True)
    elif rule.type == "enum":
        value, err = cast_enum(raw, enum_map=rule.enum_map, enum_default=rule.enum_default)
    elif rule.type == "json":
        value, err = raw, None
    else:
        value, err = raw, f"unsupported type: {rule.type}"

    if err:
        if rule.on_error == "keep_raw":
            return raw, None
        if rule.on_error == "raise":
            raise ValueError(err)
        return None, {"field": rule.target_field, "error_code": "cast_error", "error_text": err, "raw_value": raw}
    return value, None


def cast_row(rules: StreamRules, raw_row: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Каст одной строки по StreamRules."""
    out: dict[str, Any] = {}
    issues: list[dict[str, Any]] = []
    for col in rules.columns:
        raw_value = raw_row.get(col.source_field)
        value, issue = cast_value(col, raw_value)
        out[col.target_field] = value
        if issue is not None:
            issues.append(issue)
    return out, issues


def upsert_rows(
    engine: Engine,
    table: Table,
    rows: list[dict[str, Any]],
    *,
    primary_key: list[str],
    chunk_size: int = 500,
) -> dict[str, Any]:
    """Универсальный upsert для динамических normalized-таблиц."""
    if not rows:
        return {"table": table.name, "rows_upserted": 0}
    key_cols = tuple(primary_key or [])
    if not key_cols:
        with engine.begin() as conn:
            conn.execute(table.insert(), rows)
        return {"table": table.name, "rows_upserted": len(rows), "mode": "insert_only"}
    update_cols = [c.name for c in table.columns if c.name not in key_cols]
    with engine.begin() as conn:
        table.metadata.create_all(conn, tables=[table], checkfirst=True)
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i : i + chunk_size]
            if not chunk:
                continue
            stmt = pg_insert(table).values(chunk)
            excluded = stmt.excluded
            stmt = stmt.on_conflict_do_update(
                index_elements=list(key_cols),
                set_={col: getattr(excluded, col) for col in update_cols},
            )
            conn.execute(stmt)
    return {"table": table.name, "rows_upserted": len(rows), "mode": "upsert"}


def count_rows(engine: Engine, table: Table) -> int:
    """Подсчёт количества строк в таблице."""
    with engine.connect() as conn:
        return int(conn.execute(select(func.count()).select_from(table)).scalar_one())
