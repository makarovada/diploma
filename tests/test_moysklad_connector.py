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
    for fname in ("moysklad_demand.json", "moysklad_customerorder.json", "moysklad_product.json", "moysklad_counterparty.json"):
        (samples / fname).write_text((repo / fname).read_text(encoding="utf-8"), encoding="utf-8")


def test_check_without_credentials_uses_fixture(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DATANORMA_MOYSKLAD_TOKEN", raising=False)
    paths = DataPathsResource(repo_root=str(tmp_path))
    _write_samples(tmp_path)
    src = create_source("moysklad", paths=paths)
    res = src.check()
    assert res.ok
    assert res.details and res.details.get("mode") == "fixture"


def test_discover_returns_streams_and_schema(tmp_path: Path) -> None:
    _write_samples(tmp_path)
    paths = DataPathsResource(repo_root=str(tmp_path))
    src = create_source("moysklad", paths=paths)
    catalog = src.discover()
    names = {s.name for s in catalog.streams}
    assert names >= {"demand", "customerorder", "product", "counterparty"}
    for s in catalog.streams:
        assert s.json_schema.get("type") == "object"


def test_read_demand_yields_records(tmp_path: Path) -> None:
    _write_samples(tmp_path)
    paths = DataPathsResource(repo_root=str(tmp_path))
    src = create_source("moysklad", paths=paths)
    rows = list(src.read("demand"))
    assert len(rows) >= 1

