"""Определение витрины в PostgreSQL."""

from __future__ import annotations

from datanorma.config import get_settings

from sqlalchemy import Column, Date, DateTime, MetaData, Numeric, PrimaryKeyConstraint, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()


def canonical_sales_table(name: str | None = None) -> Table:
    tname = name or get_settings().datanorma_warehouse_table.strip() or "canonical_sales"
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
        Column("person_full_name", Text),
        Column("person_family_name", String(128)),
        Column("person_given_name", String(128)),
        Column("person_patronymic", String(128)),
        Column("contact_phone_e164", String(32)),
        Column("contact_email", String(256)),
        Column("country_code", String(2)),
        Column("order_status_code", String(64)),
        Column("payment_status_code", String(64)),
        Column("shipment_status_code", String(64)),
        Column("normalization_meta", JSONB),
        Column("loaded_at", DateTime(timezone=True), nullable=False),
        Column("_ingest_loaded_at", DateTime(timezone=True), nullable=True),
        PrimaryKeyConstraint("source_system", "source_record_id"),
    )
