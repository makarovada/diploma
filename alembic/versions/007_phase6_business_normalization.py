"""Phase 6: business field normalization columns + reference dim tables.

Revision ID: 007_phase6_business_normalization
Revises: 006_phase5_mapping_profiles_versioning
Create Date: 2026-05-02
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_phase6_business_normalization"
down_revision: Union[str, None] = "006_phase5_mapping_profiles_versioning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _cols(bind, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def _add_col_if_missing(bind, table: str, name: str, col) -> None:
    if table not in _tables(bind):
        return
    if name in _cols(bind, table):
        return
    op.add_column(table, col)


def upgrade() -> None:
    bind = op.get_bind()
    new_cols = [
        ("person_full_name", sa.Column("person_full_name", sa.Text(), nullable=True)),
        ("person_family_name", sa.Column("person_family_name", sa.String(128), nullable=True)),
        ("person_given_name", sa.Column("person_given_name", sa.String(128), nullable=True)),
        ("person_patronymic", sa.Column("person_patronymic", sa.String(128), nullable=True)),
        ("contact_phone_e164", sa.Column("contact_phone_e164", sa.String(32), nullable=True)),
        ("contact_email", sa.Column("contact_email", sa.String(256), nullable=True)),
        ("country_code", sa.Column("country_code", sa.String(2), nullable=True)),
        ("order_status_code", sa.Column("order_status_code", sa.String(64), nullable=True)),
        ("payment_status_code", sa.Column("payment_status_code", sa.String(64), nullable=True)),
        ("shipment_status_code", sa.Column("shipment_status_code", sa.String(64), nullable=True)),
    ]
    for t in ("canonical_sales", "typed_canonical_sales"):
        for name, col in new_cols:
            _add_col_if_missing(bind, t, name, col)

    if "dim_country" not in _tables(bind):
        op.create_table(
            "dim_country",
            sa.Column("code", sa.String(2), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
        )
    if "dim_unit" not in _tables(bind):
        op.create_table(
            "dim_unit",
            sa.Column("code", sa.String(32), primary_key=True),
            sa.Column("name", sa.String(128), nullable=False),
        )
    if "dim_status_map" not in _tables(bind):
        op.create_table(
            "dim_status_map",
            sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
            sa.Column("dimension", sa.String(32), nullable=False),
            sa.Column("source_system", sa.String(64), nullable=False),
            sa.Column("raw_status", sa.String(256), nullable=False),
            sa.Column("canonical_code", sa.String(64), nullable=False),
        )
        op.create_index(
            "ix_dim_status_map_lookup",
            "dim_status_map",
            ["dimension", "source_system", "raw_status"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    for t in ("typed_canonical_sales", "canonical_sales"):
        if t not in _tables(bind):
            continue
        for name in (
            "shipment_status_code",
            "payment_status_code",
            "order_status_code",
            "country_code",
            "contact_email",
            "contact_phone_e164",
            "person_patronymic",
            "person_given_name",
            "person_family_name",
            "person_full_name",
        ):
            if name in _cols(bind, t):
                op.drop_column(t, name)
    for tbl in ("dim_status_map", "dim_unit", "dim_country"):
        if tbl in _tables(bind):
            op.drop_table(tbl)
