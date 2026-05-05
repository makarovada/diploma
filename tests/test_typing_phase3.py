from __future__ import annotations

import pytest
from datanorma.normalization.typing import cast_rows_to_typed, load_canonical_schema

pytestmark = pytest.mark.unit


def test_cast_rows_logs_errors_and_dedups() -> None:
    schema = load_canonical_schema()
    rows = [
        {
            "source_system": "ozon",
            "source_record_id": "1",
            "event_datetime": "2026-04-01T10:00:00Z",
            "amount": "12,50",
            "currency_code": " rub ",
        },
        {
            "source_system": "ozon",
            "source_record_id": "1",
            "event_datetime": "bad-date",
            "amount": "oops",
        },
    ]
    typed_rows, stats = cast_rows_to_typed(rows, schema)
    assert len(typed_rows) == 1
    assert stats["duplicates_dropped"] == 1
    assert typed_rows[0]["amount"] is not None
