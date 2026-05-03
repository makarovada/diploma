"""Коннектор Яндекс Метрика: discover/read/check на фикстурах."""

from __future__ import annotations

from pathlib import Path

import pytest

from datanorma.resources.paths import DataPathsResource
from datanorma.sources.registry import create_source
from datanorma.sources.yandex_metrika import STREAM_FIXTURE_NAMES, YandexMetrikaSource


def _write_samples(root: Path) -> None:
    samples = root / "data" / "samples"
    samples.mkdir(parents=True)
    for stream, fname in STREAM_FIXTURE_NAMES.items():
        repo = Path(__file__).resolve().parent.parent / "data" / "samples" / fname
        if repo.is_file():
            (samples / fname).write_text(repo.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            (samples / fname).write_text("[]", encoding="utf-8")


def test_yandex_metrika_discover_four_streams(tmp_path: Path) -> None:
    _write_samples(tmp_path)
    paths = DataPathsResource(repo_root=str(tmp_path))
    src = create_source("yandex_metrika", paths=paths)
    cat = src.discover()
    names = {s.name for s in cat.streams}
    assert names == {"summary", "visits", "hits", "goals_reaches"}
    for st in cat.streams:
        assert st.json_schema.get("type") == "object"


def test_yandex_metrika_read_from_samples_repo() -> None:
    root = Path(__file__).resolve().parent.parent
    paths = DataPathsResource(repo_root=str(root))
    src = YandexMetrikaSource(paths)
    summary = list(src.read("summary"))
    assert len(summary) >= 1
    assert "date" in summary[0]
    visits = list(src.read("visits"))
    assert visits and "visit_id" in visits[0]


def test_yandex_metrika_read_incremental_filters(tmp_path: Path) -> None:
    _write_samples(tmp_path)
    paths = DataPathsResource(repo_root=str(tmp_path))
    src = create_source("yandex_metrika", paths=paths)
    rows = list(src.read("summary", sync_mode="incremental", cursor_field="date", last_cursor="2026-05-01"))
    for r in rows:
        assert r["date"] > "2026-05-01"


def test_yandex_metrika_check_ok_with_fixtures(tmp_path: Path) -> None:
    _write_samples(tmp_path)
    paths = DataPathsResource(repo_root=str(tmp_path))
    src = YandexMetrikaSource(paths)
    cr = src.check()
    assert cr.ok
    assert cr.details and cr.details.get("mode") == "fixture"


def test_yandex_metrika_check_fails_without_data(tmp_path: Path) -> None:
    samples = tmp_path / "data" / "samples"
    samples.mkdir(parents=True)
    for fname in STREAM_FIXTURE_NAMES.values():
        (samples / fname).write_text("[]", encoding="utf-8")
    paths = DataPathsResource(repo_root=str(tmp_path))
    src = YandexMetrikaSource(paths)
    cr = src.check()
    assert not cr.ok
