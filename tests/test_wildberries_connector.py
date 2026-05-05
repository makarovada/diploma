from __future__ import annotations

from pathlib import Path

import pytest

from datanorma.resources.paths import DataPathsResource
from datanorma.sources.registry import create_source

pytestmark = pytest.mark.unit


def _write_samples(root: Path) -> None:
    samples = root / "data" / "samples"
    samples.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parent.parent / "data" / "samples"
    for fname in ("wildberries_orders.json", "wildberries_sales.json", "wildberries_stocks.json"):
        (samples / fname).write_text((repo / fname).read_text(encoding="utf-8"), encoding="utf-8")


def test_check_without_credentials_uses_fixture(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DATANORMA_WB_API_TOKEN", raising=False)
    paths = DataPathsResource(repo_root=str(tmp_path))
    _write_samples(tmp_path)
    src = create_source("wildberries", paths=paths)
    res = src.check()
    assert res.ok
    assert res.details and res.details.get("mode") == "fixture"


def test_discover_returns_streams_and_schema(tmp_path: Path) -> None:
    _write_samples(tmp_path)
    paths = DataPathsResource(repo_root=str(tmp_path))
    src = create_source("wildberries", paths=paths)
    catalog = src.discover()
    assert {s.name for s in catalog.streams} >= {"orders", "sales", "stocks"}
    for s in catalog.streams:
        assert s.json_schema.get("type") == "object"


def test_read_orders_yields_records(tmp_path: Path) -> None:
    _write_samples(tmp_path)
    paths = DataPathsResource(repo_root=str(tmp_path))
    src = create_source("wildberries", paths=paths)
    rows = list(src.read("orders"))
    assert len(rows) >= 1

