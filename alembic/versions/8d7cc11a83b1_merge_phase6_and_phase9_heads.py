"""merge phase6 and phase9 heads

Revision ID: 8d7cc11a83b1
Revises: 009_phase6_canonical_marketing_events, 009_phase9_sync_run_logs_and_issue_status
Create Date: 2026-05-03 19:44:23.190234

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d7cc11a83b1'
down_revision: Union[str, None] = ('009_phase6_canonical_marketing_events', '009_phase9_sync_run_logs_and_issue_status')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
