"""add reposts count to posts"""

from alembic import op
import sqlalchemy as sa

revision = "20260315_0002"
down_revision = "20260312_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("reposts_count", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("posts", "reposts_count", server_default=None)


def downgrade() -> None:
    op.drop_column("posts", "reposts_count")
