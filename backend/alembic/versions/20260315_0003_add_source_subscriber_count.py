"""add source subscriber count

Revision ID: 20260315_0003
Revises: 20260315_0002
Create Date: 2026-03-15 19:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260315_0003"
down_revision = "20260315_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("subscriber_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("sources", "subscriber_count")
