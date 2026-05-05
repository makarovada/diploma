from __future__ import annotations

import pytest

from datanorma.destinations.base import WriteMode
from datanorma.destinations.registry import (
    destination_write,
    get_destination_class,
    normalize_destination_kind,
)

pytestmark = pytest.mark.unit


def test_normalize_destination_aliases() -> None:
    assert normalize_destination_kind("PostgreSQL") == "postgres"
    assert normalize_destination_kind("csv-file") == "csv"
    assert normalize_destination_kind("CH") == "clickhouse"


def test_unknown_destination_raises() -> None:
    with pytest.raises(ValueError, match="Неизвестный приёмник"):
        get_destination_class("oracle")


def test_csv_write_roundtrip_tmpdir(tmp_path) -> None:
    p = tmp_path / "out.csv"
    wr = destination_write(
        "csv",
        stream_name="s1",
        records=[{"id": "1", "v": "a"}, {"id": "2", "v": "b"}],
        schema={},
        mode=WriteMode.full_refresh,
        config={"path": str(p)},
    )
    assert wr.ok
    assert wr.rows_written == 2
    text = p.read_text(encoding="utf-8")
    assert "id" in text and "1" in text

    wr2 = destination_write(
        "csv",
        stream_name="s1",
        records=[{"id": "1", "v": "z"}],
        schema={},
        mode=WriteMode.upsert,
        config={"path": str(p), "primary_key": "id"},
    )
    assert wr2.ok
    body = p.read_text(encoding="utf-8")
    assert "z" in body
    assert body.count("1,") == 1 or body.count(',"1"') >= 1
