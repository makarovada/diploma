"""Минимальные проверки моделей Airbyte Protocol."""

from __future__ import annotations

from datanorma.core.airbyte_protocol import (
    AirbyteCatalog,
    AirbyteMessage,
    AirbyteRecordMessage,
    AirbyteStateMessage,
    AirbyteStream,
    StreamDescriptor,
    SyncMode,
)


def test_record_message() -> None:
    m = AirbyteRecordMessage(stream="orders", data={"id": 1}, emitted_at=1_700_000_000_000)
    assert m.stream == "orders"


def test_catalog_and_stream() -> None:
    cat = AirbyteCatalog(
        streams=[
            AirbyteStream(
                name="orders",
                json_schema={"type": "object"},
                supported_sync_modes=[SyncMode.incremental],
            )
        ]
    )
    assert cat.streams[0].name == "orders"


def test_state_global_alias() -> None:
    st = AirbyteStateMessage.model_validate({"type": "GLOBAL", "global": {"state": {"v": 1}}})
    assert st.global_ == {"state": {"v": 1}}


def test_envelope_record() -> None:
    raw = {
        "type": "RECORD",
        "record": {"stream": "s", "data": {}, "emitted_at": 0},
    }
    msg = AirbyteMessage.model_validate(raw)
    assert msg.record is not None
    assert msg.record.stream == "s"


def test_stream_descriptor() -> None:
    d = StreamDescriptor(name="x", namespace="ns")
    assert d.name == "x"
