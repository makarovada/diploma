"""Приёмник PostgreSQL: SQLAlchemy + upsert по первичному ключу."""

from __future__ import annotations

import re
from typing import Any, Iterable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from datanorma.config import get_settings
from datanorma.destinations.base import (
    BaseDestination,
    DestinationCheckResult,
    DestinationWriteResult,
    WriteMode,
)

_SAFE_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _quote_ident(name: str) -> str:
    if not _SAFE_IDENT.match(name):
        raise ValueError(f"Недопустимый идентификатор: {name!r}")
    return f'"{name}"'


def _engine_for_config(config: dict[str, Any]) -> Engine:
    url = str(config.get("url") or "").strip()
    if not url:
        url = get_settings().database_url
    return create_engine(url, pool_pre_ping=True)


def _table_parts(config: dict[str, Any]) -> tuple[str, str]:
    schema = str(config.get("schema") or "public").strip() or "public"
    table = str(config.get("table") or config.get("table_name") or "elt_stream_load").strip()
    return schema, table


def _primary_key(config: dict[str, Any]) -> list[str]:
    pk = config.get("primary_key")
    if pk is None:
        return ["id"]
    if isinstance(pk, str):
        return [pk.strip()] if pk.strip() else ["id"]
    if isinstance(pk, list):
        return [str(x).strip() for x in pk if str(x).strip()]
    return ["id"]


def _rows_list(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(r) for r in records]


def _column_names(rows: list[dict[str, Any]], schema: dict[str, Any]) -> list[str]:
    keys: set[str] = set()
    for r in rows:
        keys.update(str(k) for k in r if k is not None)
    props = (schema or {}).get("properties") if isinstance(schema, dict) else None
    if isinstance(props, dict):
        keys.update(str(k) for k in props)
    return sorted(keys)


class PostgresDestination(BaseDestination):
    code = "postgres"

    def check(self, config: dict[str, Any]) -> DestinationCheckResult:
        try:
            eng = _engine_for_config(config)
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            schema, table = _table_parts(config)
            return DestinationCheckResult(
                ok=True,
                message="PostgreSQL: подключение успешно.",
                details={"schema": schema, "table": table},
            )
        except Exception as exc:
            return DestinationCheckResult(ok=False, message=str(exc), details={"dialect": "postgres"})

    def write(
        self,
        stream_name: str,
        records: Iterable[dict[str, Any]],
        schema: dict[str, Any],
        mode: WriteMode,
        config: dict[str, Any],
    ) -> DestinationWriteResult:
        rows = _rows_list(records)
        if not rows and mode not in (WriteMode.full_refresh, WriteMode.replace_table):
            return DestinationWriteResult(ok=True, message="Нет строк для записи.", rows_written=0)

        schema_n, table_n = _table_parts(config)
        # Поток может задавать суффикс таблицы
        suffix = str(config.get("stream_table_suffix") or "").strip()
        if suffix:
            table_n = f"{table_n}_{suffix}" if table_n else suffix
        stream_table = str(config.get("stream_tables", {}).get(stream_name, "")).strip() if isinstance(config.get("stream_tables"), dict) else ""  # type: ignore[union-attr]
        if stream_table:
            table_n = stream_table

        cols = _column_names(rows, schema)
        if not cols and mode in (WriteMode.replace_table, WriteMode.full_refresh):
            cols = _column_names([{"_placeholder": None}], schema) or ["_stream"]

        qschema = _quote_ident(schema_n)
        qtable = _quote_ident(table_n)
        full_table = f"{qschema}.{qtable}"

        eng = _engine_for_config(config)
        try:
            with eng.begin() as conn:
                if mode == WriteMode.replace_table:
                    conn.execute(text(f"DROP TABLE IF EXISTS {full_table} CASCADE"))
                    col_defs = ", ".join(f'{_quote_ident(c)} TEXT' for c in cols)
                    conn.execute(text(f"CREATE TABLE {full_table} ({col_defs})"))
                    if not rows:
                        return DestinationWriteResult(
                            ok=True,
                            message=f"Таблица {schema_n}.{table_n} пересоздана (0 строк).",
                            rows_written=0,
                            details={"table": f"{schema_n}.{table_n}"},
                        )

                elif mode == WriteMode.full_refresh:
                    exists_fr = conn.execute(
                        text(
                            "SELECT 1 FROM information_schema.tables WHERE table_schema = :s AND table_name = :t"
                        ),
                        {"s": schema_n, "t": table_n},
                    ).first()
                    if exists_fr:
                        conn.execute(text(f"TRUNCATE TABLE {full_table} RESTART IDENTITY CASCADE"))
                    elif rows:
                        col_defs = ", ".join(f'{_quote_ident(c)} TEXT' for c in cols)
                        conn.execute(text(f"CREATE TABLE {full_table} ({col_defs})"))
                elif mode == WriteMode.upsert:
                    pk_cols = _primary_key(config)
                    missing_pk = [c for c in pk_cols if c not in cols]
                    if missing_pk and rows:
                        return DestinationWriteResult(
                            ok=False,
                            message=f"Для upsert не хватает колонок PK в данных: {missing_pk}",
                            rows_written=0,
                        )
                    exists_u = conn.execute(
                        text(
                            "SELECT 1 FROM information_schema.tables WHERE table_schema = :s AND table_name = :t"
                        ),
                        {"s": schema_n, "t": table_n},
                    ).first()
                    if not exists_u:
                        col_defs = ", ".join(f'{_quote_ident(c)} TEXT' for c in cols)
                        pk_sql = ""
                        if pk_cols and all(c in cols for c in pk_cols):
                            pk_sql = ", PRIMARY KEY (" + ", ".join(_quote_ident(c) for c in pk_cols) + ")"
                        conn.execute(text(f"CREATE TABLE {full_table} ({col_defs}{pk_sql})"))

                elif mode == WriteMode.append:
                    exists_a = conn.execute(
                        text(
                            "SELECT 1 FROM information_schema.tables WHERE table_schema = :s AND table_name = :t"
                        ),
                        {"s": schema_n, "t": table_n},
                    ).first()
                    if not exists_a:
                        col_defs = ", ".join(f'{_quote_ident(c)} TEXT' for c in cols)
                        conn.execute(text(f"CREATE TABLE {full_table} ({col_defs})"))

                if not rows:
                    return DestinationWriteResult(
                        ok=True,
                        message="Запись не требуется (0 строк).",
                        rows_written=0,
                        details={"table": f"{schema_n}.{table_n}", "mode": mode.value},
                    )

                col_sql = ", ".join(_quote_ident(c) for c in cols)
                placeholders = ", ".join(f":{c}" for c in cols)

                if mode == WriteMode.upsert:
                    pk_cols = _primary_key(config)
                    pk_sql = ", ".join(_quote_ident(c) for c in pk_cols)
                    update_cols = [c for c in cols if c not in pk_cols]
                    if not update_cols:
                        update_clause = ", ".join(f'{_quote_ident(pk_cols[0])} = EXCLUDED.{_quote_ident(pk_cols[0])}')
                    else:
                        update_clause = ", ".join(f"{_quote_ident(c)} = EXCLUDED.{_quote_ident(c)}" for c in update_cols)
                    sql = (
                        f"INSERT INTO {full_table} ({col_sql}) VALUES ({placeholders}) "
                        f"ON CONFLICT ({pk_sql}) DO UPDATE SET {update_clause}"
                    )
                    # Требуется UNIQUE/PK в БД; если нет — создаём уникальный индекс по PK для новой таблицы выше
                    for r in rows:
                        payload = {c: r.get(c) for c in cols}
                        conn.execute(text(sql), payload)
                else:
                    sql = f"INSERT INTO {full_table} ({col_sql}) VALUES ({placeholders})"
                    for r in rows:
                        payload = {c: r.get(c) for c in cols}
                        conn.execute(text(sql), payload)

            return DestinationWriteResult(
                ok=True,
                message=f"Записано строк: {len(rows)} ({mode.value}).",
                rows_written=len(rows),
                details={"table": f"{schema_n}.{table_n}", "stream": stream_name, "mode": mode.value},
            )
        except Exception as exc:
            return DestinationWriteResult(ok=False, message=str(exc), rows_written=0, details={"stream": stream_name})
