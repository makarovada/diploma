"""Каталог коннекторов в React mock-data: Яндекс Метрика и отсутствие Unisender."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_mock_data_catalog_has_yandex_metrika_streams() -> None:
    p = Path(__file__).resolve().parent.parent / "client" / "src" / "lib" / "mock-data.ts"
    text = p.read_text(encoding="utf-8")
    assert 'id: "yandex_metrika"' in text
    assert "Яндекс Метрика" in text
    assert re.search(r'streams:\s*\[[^\]]*"summary"[^\]]*"visits"[^\]]*"hits"[^\]]*"goals_reaches"', text, re.DOTALL)


def test_mock_data_no_unisender_in_catalog() -> None:
    p = Path(__file__).resolve().parent.parent / "client" / "src" / "lib" / "mock-data.ts"
    text = p.read_text(encoding="utf-8").lower()
    assert "unisender" not in text
