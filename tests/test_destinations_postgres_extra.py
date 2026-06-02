from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from datanorma.destinations.base import WriteMode
from datanorma.destinations.postgres import (
    PostgresDestination,
    _column_names,
    _normalize_postgres_url,
    _primary_key,
    _quote_ident,
)

pytestmark = pytest.mark.unit


def test_normalize_postgres_url() -> None:
    assert _normalize_postgres_url("postgresql://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"
    assert _normalize_postgres_url("postgres://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert _normalize_postgres_url("postgresql+psycopg://u@h/db") == "postgresql+psycopg://u@h/db"
    assert _normalize_postgres_url("") == ""


def test_quote_ident_and_primary_key_helpers() -> None:
    assert _quote_ident("orders") == '"orders"'
    assert _quote_ident("вес") == '"вес"'
    assert _quote_ident("orders;drop") == '"orders;drop"'
    assert _quote_ident('col"name') == '"col""name"'
    with pytest.raises(ValueError):
        _quote_ident("")
    assert _primary_key({}) == ["id"]
    assert _primary_key({"primary_key": "external_id"}) == ["external_id"]
    assert _primary_key({"primary_key": ["id", "shop_id"]}) == ["id", "shop_id"]
    assert _column_names([{"a": 1}], {"properties": {"b": {"type": "string"}}}) == ["a", "b"]


@dataclass
class _Result:
    exists: bool

    def first(self):
        return (1,) if self.exists else None


class _Conn:
    def __init__(self) -> None:
        self.sql: list[str] = []
        self._exists = False

    def execute(self, stmt, params: dict[str, Any] | None = None):
        s = str(stmt)
        self.sql.append(s)
        if "information_schema.tables" in s:
            return _Result(self._exists)
        if "CREATE TABLE" in s:
            self._exists = True
        return _Result(True)


class _Engine:
    def __init__(self) -> None:
        self.conn = _Conn()

    def begin(self):
        class _Ctx:
            def __init__(self, c: _Conn) -> None:
                self.c = c

            def __enter__(self):
                return self.c

            def __exit__(self, exc_type, exc, tb):
                return False

        return _Ctx(self.conn)

    def connect(self):
        class _Ctx:
            def __init__(self, c: _Conn) -> None:
                self.c = c

            def __enter__(self):
                return self.c

            def __exit__(self, exc_type, exc, tb):
                return False

        return _Ctx(self.conn)


def test_postgres_destination_check_and_append(monkeypatch: pytest.MonkeyPatch) -> None:
    eng = _Engine()
    monkeypatch.setattr("datanorma.destinations.postgres._engine_for_config", lambda _cfg: eng)
    dst = PostgresDestination()
    check = dst.check({"url": "postgresql://x"})
    assert check.ok is True
    out = dst.write(
        stream_name="orders",
        records=[{"id": "1", "amount": "10"}],
        schema={"properties": {"id": {}, "amount": {}}},
        mode=WriteMode.append,
        config={"schema": "public", "table": "orders_load"},
    )
    assert out.ok is True
    assert out.rows_written == 1
    assert any("CREATE TABLE" in s for s in eng.conn.sql)
    assert any("INSERT INTO" in s for s in eng.conn.sql)


def test_postgres_destination_upsert_missing_pk(monkeypatch: pytest.MonkeyPatch) -> None:
    eng = _Engine()
    monkeypatch.setattr("datanorma.destinations.postgres._engine_for_config", lambda _cfg: eng)
    dst = PostgresDestination()
    out = dst.write(
        stream_name="orders",
        records=[{"amount": "10"}],
        schema={"properties": {"amount": {}}},
        mode=WriteMode.upsert,
        config={"schema": "public", "table": "orders_load", "primary_key": "id"},
    )
    assert out.ok is False
    assert "PK" in out.message
