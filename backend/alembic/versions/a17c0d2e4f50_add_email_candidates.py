"""add email_candidates table

Revision ID: a17c0d2e4f50
Revises: a16b0c1d2e3f
Create Date: 2026-10-06 13:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a17c0d2e4f50"
down_revision: Union[str, None] = "a16b0c1d2e3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("pattern_used", sa.String(length=100), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("raw_provider_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("person_id", "email", name="uq_email_candidates_person_email"),
    )
    op.create_index(op.f("ix_email_candidates_person_id"), "email_candidates", ["person_id"], unique=False)
    op.create_index(op.f("ix_email_candidates_email"), "email_candidates", ["email"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_email_candidates_email"), table_name="email_candidates")
    op.drop_index(op.f("ix_email_candidates_person_id"), table_name="email_candidates")
    op.drop_table("email_candidates")
