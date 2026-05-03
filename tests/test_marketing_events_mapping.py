"""Маппинг sample Яндекс Метрики → canonical_marketing_events."""

from __future__ import annotations

import json
from pathlib import Path

from datanorma.normalization.marketing_events import build_canonical_marketing_event_rows, load_marketing_section
from datanorma.normalization.to_canonical import load_source_mappings


def _load_sample_array(name: str) -> list[dict]:
    p = Path(__file__).resolve().parent.parent / "data" / "samples" / name
    data = json.loads(p.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    return data


def test_load_marketing_section_from_repo_yaml() -> None:
    m = load_source_mappings(with_db_override=False)
    sec = load_marketing_section(m)
    assert sec.get("canonical") == "canonical_marketing_events_v1"
    ym = (sec.get("sources") or {}).get("yandex_metrika") or {}
    assert "summary" in (ym.get("streams") or {})


def test_build_marketing_rows_all_streams() -> None:
    raw = {
        "summary": _load_sample_array("yandex_metrika_summary.json"),
        "visits": _load_sample_array("yandex_metrika_visits.json"),
        "hits": _load_sample_array("yandex_metrika_hits.json"),
        "goals_reaches": _load_sample_array("yandex_metrika_goals_reaches.json"),
    }
    rows, stats = build_canonical_marketing_event_rows(raw, counter_id="12345", mappings=load_source_mappings(with_db_override=False))
    assert stats["rows_out"] == sum(len(v) for v in raw.values())
    summary_row = next(r for r in rows if r["event_type"] == "summary_daily")
    assert summary_row["source_record_id"].startswith("12345|summary|")
    assert summary_row["event_datetime"] is not None
    assert summary_row["_ingest_meta"].get("visits") == raw["summary"][0]["visits"]
    goal_row = next(r for r in rows if r["event_type"] == "goal_reach")
    assert goal_row["revenue"] == 1500.5
    assert goal_row["currency"] == "RUB"
