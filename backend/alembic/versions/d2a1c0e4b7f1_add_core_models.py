"""add core models

Revision ID: d2a1c0e4b7f1
Revises:
Create Date: 2026-09-09 14:41:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d2a1c0e4b7f1"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("industry", sa.String(length=255), nullable=True),
        sa.Column("size", sa.String(length=32), nullable=True),
        sa.Column("raw_site_text", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_companies_domain"), "companies", ["domain"], unique=True)

    op.create_table(
        "domain_health",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("spf_record", sa.Text(), nullable=True),
        sa.Column("spf_valid", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("dkim_record", sa.Text(), nullable=True),
        sa.Column("dkim_valid", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("dmarc_record", sa.Text(), nullable=True),
        sa.Column("dmarc_policy", sa.String(length=50), nullable=True),
        sa.Column("mx_records", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_domain_health_domain"), "domain_health", ["domain"], unique=True)

    op.create_table(
        "persons",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("linkedin_url", sa.String(length=500), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("email_status", sa.String(length=32), server_default="unknown", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("company_id", sa.Uuid(), nullable=True),
        sa.Column("raw_linkedin_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("linkedin_url"),
    )
    op.create_index(op.f("ix_persons_company_id"), "persons", ["company_id"], unique=False)

    op.create_table(
        "email_drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("goal", sa.String(length=32), server_default="intro", nullable=False),
        sa.Column("generation_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_sent", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_email_drafts_person_id"), "email_drafts", ["person_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_email_drafts_person_id"), table_name="email_drafts")
    op.drop_table("email_drafts")
    op.drop_index(op.f("ix_persons_company_id"), table_name="persons")
    op.drop_table("persons")
    op.drop_index(op.f("ix_domain_health_domain"), table_name="domain_health")
    op.drop_table("domain_health")
    op.drop_index(op.f("ix_companies_domain"), table_name="companies")
    op.drop_table("companies")
