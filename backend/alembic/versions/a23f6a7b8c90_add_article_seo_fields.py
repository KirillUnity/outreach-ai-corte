"""add article SEO fields

Revision ID: a23f6a7b8c90
Revises: a22e5f6a7b80
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a23f6a7b8c90"
down_revision: Union[str, None] = "a22e5f6a7b80"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add deterministic SEO optimization output."""
    op.add_column(
        "seo_articles",
        sa.Column("internal_links", postgresql.JSONB(), server_default="[]", nullable=False),
    )
    op.add_column("seo_articles", sa.Column("keyword_primary", sa.String(255)))


def downgrade() -> None:
    """Remove deterministic SEO optimization output."""
    op.drop_column("seo_articles", "keyword_primary")
    op.drop_column("seo_articles", "internal_links")
