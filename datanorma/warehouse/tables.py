"""Определение витрины в PostgreSQL."""

from __future__ import annotations

import os

from sqlalchemy import Column, Date, DateTime, MetaData, Numeric, PrimaryKeyConstraint, String, Table, Text

metadata = MetaData()


def canonical_sales_table(name: str | None = None) -> Table:
    tname = name or os.environ.get("DATANORMA_WAREHOUSE_TABLE", "canonical_sales").strip() or "canonical_sales"
    key = tname
    if key in metadata.tables:
        return metadata.tables[key]
    return Table(
        tname,
        metadata,
        Column("source_system", String(64), nullable=False),
        Column("source_record_id", String(512), nullable=False),
        Column("event_datetime", DateTime(timezone=True)),
        Column("amount", Numeric(18, 4)),
        Column("amount_rub", Numeric(18, 4)),
        Column("currency_code", String(16)),
        Column("counterparty_name", Text),
        Column("channel", String(128)),
        Column("line_description", Text),
        Column("status", String(128)),
        Column("cbr_rate_date", Date),
        Column("line_unit_normalized", String(64)),
        Column("loaded_at", DateTime(timezone=True), nullable=False),
        PrimaryKeyConstraint("source_system", "source_record_id"),
    )
