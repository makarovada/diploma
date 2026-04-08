"""Курсоры incremental sync."""

from __future__ import annotations

from datanorma.ingest.cursor_filter import filter_incremental_dict_rows, filter_incremental_postings


def test_filter_postings_incremental() -> None:
    p = [
        {"posting_number": "1", "x": 1},
        {"posting_number": "5", "x": 2},
        {"posting_number": "3", "x": 3},
    ]
    out = filter_incremental_postings(p, cursor_field="posting_number", last_cursor="3", sync_mode="incremental")
    assert len(out) == 1
    assert out[0]["posting_number"] == "5"


def test_filter_full_refresh() -> None:
    rows = [{"id": "a"}, {"id": "b"}]
    out = filter_incremental_dict_rows(rows, cursor_field="id", last_cursor="a", sync_mode="full_refresh")
    assert len(out) == 2
