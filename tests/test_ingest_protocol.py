"""Минимальные проверки моделей Ingest Protocol."""

from __future__ import annotations

import pytest
from datanorma.core.ingest_protocol import (
    IngestCatalog,
    IngestMessage,
    IngestRecordMessage,
    IngestStateMessage,
    IngestStream,
    StreamDescriptor,
    SyncMode,
)

pytestmark = pytest.mark.unit


def test_record_message() -> None:
    m = IngestRecordMessage(stream="orders", data={"id": 1}, emitted_at=1_700_000_000_000)
    assert m.stream == "orders"


def test_catalog_and_stream() -> None:
    cat = IngestCatalog(
        streams=[
            IngestStream(
                name="orders",
                json_schema={"type": "object"},
                supported_sync_modes=[SyncMode.incremental],
            )
        ]
    )
    assert cat.streams[0].name == "orders"


def test_state_global_alias() -> None:
    st = IngestStateMessage.model_validate({"type": "GLOBAL", "global": {"state": {"v": 1}}})
    assert st.global_ == {"state": {"v": 1}}


def test_envelope_record() -> None:
    raw = {
        "type": "RECORD",
        "record": {"stream": "s", "data": {}, "emitted_at": 0},
    }
    msg = IngestMessage.model_validate(raw)
    assert msg.record is not None
    assert msg.record.stream == "s"


def test_stream_descriptor() -> None:
    d = StreamDescriptor(name="x", namespace="ns")
    assert d.name == "x"
