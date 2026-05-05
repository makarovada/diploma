from __future__ import annotations

from pathlib import Path

import pytest
import datanorma.normalization.to_canonical as tc

pytestmark = pytest.mark.unit


def test_load_source_mappings_db_override(monkeypatch, tmp_path: Path) -> None:
    p = tmp_path / "mappings.yaml"
    p.write_text("version: 1\ncanonical: canonical_sales_v1\nsources: {}\n", encoding="utf-8")

    class _Settings:
        database_url = "postgresql+psycopg://u:p@localhost:5432/x"

        @staticmethod
        def resolved_source_mappings_path() -> Path:
            return p

    monkeypatch.setattr(tc, "get_settings", lambda: _Settings())
    monkeypatch.setattr(tc, "_engine", lambda: object())
    monkeypatch.setattr(
        tc,
        "load_mappings_with_db_override",
        lambda **kwargs: {"version": 99, "canonical": "canonical_sales_v1", "sources": {"1c": {"stream": "orders"}}},
    )
    out = tc.load_source_mappings(workspace_code="main", with_db_override=True)
    assert out["version"] == 99
    assert "1c" in out["sources"]


def test_load_source_mappings_fallback_to_yaml_on_db_error(monkeypatch, tmp_path: Path) -> None:
    p = tmp_path / "mappings.yaml"
    p.write_text("version: 1\ncanonical: canonical_sales_v1\nsources:\n  1c:\n    stream: orders\n", encoding="utf-8")

    class _Settings:
        database_url = "postgresql+psycopg://u:p@localhost:5432/x"

        @staticmethod
        def resolved_source_mappings_path() -> Path:
            return p

    monkeypatch.setattr(tc, "get_settings", lambda: _Settings())
    monkeypatch.setattr(tc, "_engine", lambda: object())
    monkeypatch.setattr(tc, "load_mappings_with_db_override", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("db down")))
    out = tc.load_source_mappings(workspace_code="main", with_db_override=True)
    assert out["version"] == 1
    assert out["sources"]["1c"]["stream"] == "orders"
