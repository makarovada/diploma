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
    for fname in (
        "bitrix24_deals.json",
        "bitrix24_contacts.json",
        "bitrix24_leads.json",
        "bitrix24_companies.json",
    ):
        (samples / fname).write_text((repo / fname).read_text(encoding="utf-8"), encoding="utf-8")


def test_check_without_credentials_uses_fixture(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DATANORMA_BITRIX24_WEBHOOK_URL", raising=False)
    paths = DataPathsResource(repo_root=str(tmp_path))
    _write_samples(tmp_path)
    src = create_source("bitrix24", paths=paths)
    res = src.check()
    assert res.ok
    assert res.details and res.details.get("mode") == "fixture"


def test_discover_returns_streams_and_schema(tmp_path: Path) -> None:
    _write_samples(tmp_path)
    paths = DataPathsResource(repo_root=str(tmp_path))
    src = create_source("bitrix24", paths=paths)
    catalog = src.discover()
    names = {s.name for s in catalog.streams}
    assert names >= {"crm_deals", "crm_contacts", "crm_leads", "crm_companies"}
    for s in catalog.streams:
        assert s.json_schema.get("type") == "object"


def test_read_crm_deals_yields_records(tmp_path: Path) -> None:
    _write_samples(tmp_path)
    paths = DataPathsResource(repo_root=str(tmp_path))
    src = create_source("bitrix24", paths=paths)
    rows = list(src.read("crm_deals"))
    assert len(rows) >= 1

