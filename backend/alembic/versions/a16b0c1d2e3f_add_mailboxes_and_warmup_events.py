"""add mailboxes and warmup_events

Revision ID: a16b0c1d2e3f
Revises: f1a2b3c4d5e6
Create Date: 2026-10-06 11:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a16b0c1d2e3f"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mailboxes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="new", nullable=False),
        sa.Column("warmup_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("warmup_day", sa.Integer(), server_default="0", nullable=False),
        sa.Column("daily_limit", sa.Integer(), server_default="5", nullable=False),
        sa.Column("emails_sent_today", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_sent", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_opened", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_replied", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_bounced", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_spam_reports", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reputation_score", sa.Float(), server_default="50.0", nullable=False),
        sa.Column("last_warmup_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mailboxes_email"), "mailboxes", ["email"], unique=True)
    op.create_index(op.f("ix_mailboxes_domain"), "mailboxes", ["domain"], unique=False)

    op.create_table(
        "warmup_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("mailbox_id", sa.Uuid(), nullable=False),
        sa.Column("peer_email", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("warmup_day", sa.Integer(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["mailbox_id"], ["mailboxes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_warmup_events_mailbox_id"), "warmup_events", ["mailbox_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_warmup_events_mailbox_id"), table_name="warmup_events")
    op.drop_table("warmup_events")
    op.drop_index(op.f("ix_mailboxes_domain"), table_name="mailboxes")
    op.drop_index(op.f("ix_mailboxes_email"), table_name="mailboxes")
    op.drop_table("mailboxes")
