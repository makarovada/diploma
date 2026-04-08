"""Phase 3: organizations/workspaces and user bindings.

Revision ID: 004_phase3_multitenancy
Revises: 003_phase2_typed
Create Date: 2026-04-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_phase3_multitenancy"
down_revision: Union[str, None] = "003_phase2_typed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    t = _tables(bind)
    if "organization" not in t:
        op.create_table(
            "organization",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column("code", sa.String(64), nullable=False, unique=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        )
    if "workspace" not in t:
        op.create_table(
            "workspace",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
            sa.Column("code", sa.String(64), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.UniqueConstraint("organization_id", "code", name="uq_workspace_org_code"),
        )
    if "user_workspace" not in t:
        op.create_table(
            "user_workspace",
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        )

    # seed default tenant/workspace and attach all users
    op.execute(
        sa.text(
            "INSERT INTO organization(code, name) VALUES ('default', 'Default Organization') "
            "ON CONFLICT (code) DO NOTHING"
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO workspace(organization_id, code, name) "
            "SELECT o.id, 'main', 'Main Workspace' FROM organization o WHERE o.code='default' "
            "ON CONFLICT ON CONSTRAINT uq_workspace_org_code DO NOTHING"
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO user_workspace(user_id, workspace_id) "
            "SELECT u.id, w.id FROM app_user u "
            "CROSS JOIN workspace w WHERE w.code='main' "
            "ON CONFLICT (user_id, workspace_id) DO NOTHING"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    t = _tables(bind)
    if "user_workspace" in t:
        op.drop_table("user_workspace")
    if "workspace" in t:
        op.drop_table("workspace")
    if "organization" in t:
        op.drop_table("organization")
