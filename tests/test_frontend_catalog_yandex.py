"""Каталог коннекторов API: Яндекс Метрика и отсутствие Unisender."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_api_catalog_has_yandex_metrika_streams() -> None:
    p = Path(__file__).resolve().parent.parent / "datanorma" / "web" / "api_v1_catalog.py"
    text = p.read_text(encoding="utf-8")
    assert 'if c == "yandex_metrika":' in text
    assert '"summary"' in text
    assert '"visits"' in text
    assert '"hits"' in text
    assert '"goals_reaches"' in text


def test_api_catalog_no_unisender_in_catalog() -> None:
    p = Path(__file__).resolve().parent.parent / "datanorma" / "web" / "api_v1_catalog.py"
    text = p.read_text(encoding="utf-8").lower()
    assert "unisender" not in text
