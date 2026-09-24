"""add agent_runs table

Revision ID: e8c0a1b2d3e4
Revises: d2a1c0e4b7f1
Create Date: 2026-09-24 16:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e8c0a1b2d3e4"
down_revision: Union[str, None] = "d2a1c0e4b7f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("goal", sa.String(length=32), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("iterations", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tokens_input", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tokens_output", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost_usd", sa.Float(), server_default="0", nullable=False),
        sa.Column("duration_seconds", sa.Float(), server_default="0", nullable=False),
        sa.Column("final_state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_runs_person_id"), "agent_runs", ["person_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_runs_person_id"), table_name="agent_runs")
    op.drop_table("agent_runs")
