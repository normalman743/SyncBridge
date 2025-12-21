"""add block reminder fields

Revision ID: 9f2bc9e6c1d7
Revises: 10308d0fa5bb
Create Date: 2025-12-21 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "9f2bc9e6c1d7"
down_revision = "10308d0fa5bb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("blocks", sa.Column("last_message_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column("blocks", sa.Column("reminder_sent", sa.SmallInteger(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("blocks", "reminder_sent")
    op.drop_column("blocks", "last_message_at")
