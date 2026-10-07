"""add seo articles

Revision ID: a21d4e5f6a70
Revises: a19f2b3c4d50
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a21d4e5f6a70"
down_revision: Union[str, None] = "a19f2b3c4d50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the Day 21 article table."""
    op.create_table(
        "seo_articles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("slug", sa.String(300), nullable=False),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column("language", sa.String(10), server_default="ru", nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("keywords", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("meta_title", sa.String(60), nullable=True),
        sa.Column("meta_description", sa.String(160), nullable=True),
        sa.Column("rag_context_used", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("tokens_input", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tokens_output", sa.Integer(), server_default="0", nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(12, 8), server_default="0", nullable=False),
        sa.Column("generation_prompt_version", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_seo_articles_company_id", "seo_articles", ["company_id"])
    op.create_index("ix_seo_articles_slug", "seo_articles", ["slug"], unique=True)


def downgrade() -> None:
    """Drop the Day 21 article table."""
    op.drop_index("ix_seo_articles_slug", table_name="seo_articles")
    op.drop_index("ix_seo_articles_company_id", table_name="seo_articles")
    op.drop_table("seo_articles")
