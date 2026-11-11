"""add outbound_attempts

Revision ID: c3d91e0a4b72
Revises: a23f6a7b8c90
Create Date: 2026-11-11 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d91e0a4b72"
down_revision: Union[str, None] = "a23f6a7b8c90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the single-row-per-target log of outbound vendor calls."""
    op.create_table(
        "outbound_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("target", sa.String(length=512), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('failed', 'succeeded')",
            name="ck_outbound_attempts_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("target", name="uq_outbound_attempts_target"),
    )


def downgrade() -> None:
    """Drop the outbound attempt log."""
    op.drop_table("outbound_attempts")
