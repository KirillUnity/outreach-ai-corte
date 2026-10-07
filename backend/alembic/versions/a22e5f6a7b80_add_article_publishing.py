"""add article publishing fields

Revision ID: a22e5f6a7b80
Revises: a21d4e5f6a70
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a22e5f6a7b80"
down_revision: Union[str, None] = "a21d4e5f6a70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add scheduling and publishing state."""
    op.add_column("seo_articles", sa.Column("scheduled_at", sa.DateTime(timezone=True)))
    op.add_column("seo_articles", sa.Column("published_at", sa.DateTime(timezone=True)))
    op.add_column(
        "seo_articles",
        sa.Column("publish_channel", sa.String(20), server_default="mock", nullable=False),
    )
    op.add_column("seo_articles", sa.Column("publish_url", sa.String(2048)))


def downgrade() -> None:
    """Remove scheduling and publishing state."""
    op.drop_column("seo_articles", "publish_url")
    op.drop_column("seo_articles", "publish_channel")
    op.drop_column("seo_articles", "published_at")
    op.drop_column("seo_articles", "scheduled_at")
