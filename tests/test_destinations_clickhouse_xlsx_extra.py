from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from datanorma.destinations.base import WriteMode
from datanorma.destinations.clickhouse import ClickHouseDestination, _ch_ident
from datanorma.destinations.xlsx_file import XlsxFileDestination, _sheet

pytestmark = pytest.mark.unit


class _Resp:
    def __init__(self, status_code: int = 200, text: str = "1", body: dict | None = None) -> None:
        self.status_code = status_code
        self.text = text
        self._body = body or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.text)


class _HttpClient:
    def __init__(self, *args, **kwargs) -> None:
        self.calls: list[tuple[str, str]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, base, params=None, auth=None):
        self.calls.append(("GET", str(params)))
        return _Resp(200, "1")

    def post(self, base, params=None, auth=None, content=None):
        q = (params or {}).get("query", "")
        self.calls.append(("POST", q))
        if "EXISTS TABLE" in q:
            return _Resp(200, "0")
        return _Resp(200, "ok")

    def request(self, method, url, headers=None, params=None, json=None):
        q = (params or {}).get("query", "")
        if q:
            return self.post(url, params=params)
        return _Resp(200, body={"data": [{"id": 1}]})


def test_clickhouse_ident_and_write(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _ch_ident("safe_name") == "safe_name"
    with pytest.raises(ValueError):
        _ch_ident("bad-name!")

    monkeypatch.setattr("datanorma.destinations.clickhouse.httpx.Client", _HttpClient)
    dst = ClickHouseDestination()
    check = dst.check({"host": "localhost"})
    assert check.ok is True
    out = dst.write(
        "events",
        records=[{"id": "1", "event": "click"}],
        schema={},
        mode=WriteMode.append,
        config={"database": "default", "table": "events_raw"},
    )
    assert out.ok is True
    assert out.rows_written == 1


def test_xlsx_destination_write_modes(tmp_path: Path) -> None:
    path = tmp_path / "out.xlsx"
    dst = XlsxFileDestination()
    assert _sheet({"sheet_name": "a" * 60}, "s") == "a" * 31

    chk = dst.check({"path": str(path)})
    assert chk.ok is True

    full = dst.write(
        "orders",
        records=[{"id": 1, "v": "a"}],
        schema={},
        mode=WriteMode.full_refresh,
        config={"path": str(path), "sheet_name": "orders"},
    )
    assert full.ok is True
    assert path.exists()

    app = dst.write(
        "orders",
        records=[{"id": 2, "v": "b"}],
        schema={},
        mode=WriteMode.append,
        config={"path": str(path), "sheet_name": "orders"},
    )
    assert app.ok is True

    ups = dst.write(
        "orders",
        records=[{"id": 2, "v": "c"}],
        schema={},
        mode=WriteMode.upsert,
        config={"path": str(path), "sheet_name": "orders", "primary_key": "id"},
    )
    assert ups.ok is True
    df = pd.read_excel(path, sheet_name="orders")
    assert 2 in set(df["id"].tolist())
