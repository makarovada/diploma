"""Совместимость: ревизия переименована в 002_phase1_ingest (файл 002_phase1_ingest_staging_state.py).

Раньше в БД мог остаться version_num = 002_phase1_airbyte. Этот шаг no-op;
фактические DDL в 002_phase1_ingest (идемпотентные проверки таблиц/колонок).

Revision ID: 002_phase1_airbyte
Revises: 001_phase_a
Create Date: 2026-05-02

"""

from __future__ import annotations

from typing import Sequence, Union

revision: str = "002_phase1_airbyte"
down_revision: Union[str, None] = "001_phase_a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
