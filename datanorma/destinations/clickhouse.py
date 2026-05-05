"""Приёмник ClickHouse через HTTP-интерфейс (httpx)."""

from __future__ import annotations

import json
import re
from typing import Any, Iterable

import httpx

from datanorma.destinations.base import (
    BaseDestination,
    DestinationCheckResult,
    DestinationWriteResult,
    WriteMode,
)

_SAFE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _ch_ident(name: str) -> str:
    if not _SAFE.match(name):
        raise ValueError(f"Недопустимое имя для ClickHouse: {name!r}")
    return name


def _client_params(config: dict[str, Any]) -> tuple[str, tuple[str, str] | None]:
    host = str(config.get("host") or "localhost").strip()
    port = int(config.get("port") or 8123)
    secure = bool(config.get("secure"))
    scheme = "https" if secure else "http"
    base = f"{scheme}://{host}:{port}"
    user = str(config.get("user") or "default")
    password = str(config.get("password") or "")
    auth: tuple[str, str] | None = (user, password) if password else None
    return base, auth


def _post_query(client: httpx.Client, base: str, auth: tuple[str, str] | None, query: str) -> httpx.Response:
    return client.post(base, params={"query": query}, auth=auth)


def _table_exists(client: httpx.Client, base: str, auth: tuple[str, str] | None, database: str, table: str) -> bool:
    r = _post_query(client, base, auth, f"EXISTS TABLE {_ch_ident(database)}.{_ch_ident(table)}")
    return r.status_code == 200 and r.text.strip() == "1"


def _create_table(
    client: httpx.Client,
    base: str,
    auth: tuple[str, str] | None,
    database: str,
    table: str,
    columns: list[str],
) -> None:
    col_defs = ", ".join(f"{_ch_ident(c)} String" for c in columns)
    q = (
        f"CREATE TABLE IF NOT EXISTS {_ch_ident(database)}.{_ch_ident(table)} ({col_defs}) "
        "ENGINE = MergeTree ORDER BY tuple()"
    )
    r = _post_query(client, base, auth, q)
    if r.status_code != 200:
        raise RuntimeError(r.text[:800])


def _insert_json_each_row(
    client: httpx.Client,
    base: str,
    auth: tuple[str, str] | None,
    database: str,
    table: str,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    lines = "\n".join(json.dumps(r, ensure_ascii=False, default=str) for r in rows)
    q = f"INSERT INTO {_ch_ident(database)}.{_ch_ident(table)} FORMAT JSONEachRow"
    r = client.post(base, params={"query": q}, content=lines.encode("utf-8"), auth=auth)
    if r.status_code != 200:
        raise RuntimeError(r.text[:800])


class ClickHouseDestination(BaseDestination):
    code = "clickhouse"

    def check(self, config: dict[str, Any]) -> DestinationCheckResult:
        base, auth = _client_params(config)
        try:
            with httpx.Client(timeout=20.0) as client:
                r = client.get(base, params={"query": "SELECT 1"}, auth=auth)
            ok = r.status_code == 200
            return DestinationCheckResult(
                ok=ok,
                message="ClickHouse: отвечает." if ok else f"HTTP {r.status_code}: {r.text[:200]}",
                details={"base_url": base, "status": r.status_code},
            )
        except Exception as exc:
            return DestinationCheckResult(ok=False, message=str(exc), details={"base_url": base})

    def write(
        self,
        stream_name: str,
        records: Iterable[dict[str, Any]],
        schema: dict[str, Any],
        mode: WriteMode,
        config: dict[str, Any],
    ) -> DestinationWriteResult:
        rows = [dict(r) for r in records]
        base, auth = _client_params(config)
        database = _ch_ident(str(config.get("database") or "default"))
        table = _ch_ident(str(config.get("table") or "elt_load"))

        if mode in (WriteMode.append, WriteMode.upsert) and not rows:
            return DestinationWriteResult(ok=True, message="ClickHouse: нет строк для записи.", rows_written=0)

        try:
            with httpx.Client(timeout=120.0) as client:
                if mode in (WriteMode.replace_table, WriteMode.full_refresh):
                    _post_query(
                        client,
                        base,
                        auth,
                        f"DROP TABLE IF EXISTS {database}.{table}",
                    )

                cols = sorted({k for r in rows for k in r}) if rows else ["_empty"]
                if mode in (WriteMode.replace_table, WriteMode.full_refresh):
                    _create_table(client, base, auth, database, table, cols)
                    _insert_json_each_row(client, base, auth, database, table, rows)
                    return DestinationWriteResult(
                        ok=True,
                        message=f"ClickHouse: {mode.value}, записано {len(rows)} строк.",
                        rows_written=len(rows),
                        details={"table": f"{database}.{table}", "stream": stream_name},
                    )

                if not _table_exists(client, base, auth, database, table):
                    _create_table(client, base, auth, database, table, cols)

                _insert_json_each_row(client, base, auth, database, table, rows)
            msg = f"ClickHouse: записано {len(rows)} строк ({mode.value})."
            if mode == WriteMode.upsert:
                msg += " Для настоящего upsert настройте ReplacingMergeTree / версионирование в ClickHouse."
            return DestinationWriteResult(
                ok=True,
                message=msg,
                rows_written=len(rows),
                details={"table": f"{database}.{table}", "stream": stream_name, "mode": mode.value},
            )
        except Exception as exc:
            return DestinationWriteResult(ok=False, message=str(exc), rows_written=0)
