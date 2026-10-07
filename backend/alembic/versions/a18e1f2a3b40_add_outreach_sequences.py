"""add outreach sequences and enrollments

Revision ID: a18e1f2a3b40
Revises: a17c0d2e4f50
Create Date: 2026-10-06 13:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a18e1f2a3b40"
down_revision: Union[str, None] = "a17c0d2e4f50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "outreach_sequences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("mailbox_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("steps", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["mailbox_id"], ["mailboxes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_outreach_sequences_mailbox_id"), "outreach_sequences", ["mailbox_id"], unique=False)
    op.create_table(
        "outreach_sequence_enrollments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sequence_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("current_step", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sequence_id"], ["outreach_sequences.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sequence_id", "person_id", name="uq_sequence_enrollment_person"),
    )
    op.create_index(
        op.f("ix_outreach_sequence_enrollments_sequence_id"),
        "outreach_sequence_enrollments",
        ["sequence_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_outreach_sequence_enrollments_person_id"),
        "outreach_sequence_enrollments",
        ["person_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_outreach_sequence_enrollments_person_id"), table_name="outreach_sequence_enrollments")
    op.drop_index(op.f("ix_outreach_sequence_enrollments_sequence_id"), table_name="outreach_sequence_enrollments")
    op.drop_table("outreach_sequence_enrollments")
    op.drop_index(op.f("ix_outreach_sequences_mailbox_id"), table_name="outreach_sequences")
    op.drop_table("outreach_sequences")
