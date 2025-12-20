"""empty message

Revision ID: ab4d1b5c2bd7
Revises: 9023c5338bca
Create Date: 2025-12-21 00:30:14.970600

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab4d1b5c2bd7'
down_revision: Union[str, Sequence[str], None] = '9023c5338bca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "users",
        "is_active",
        existing_type=sa.SmallInteger(),
        server_default="0",
    )
    op.alter_column(
        "blocks",
        "status",
        existing_type=sa.Enum("urgent", "normal", name="block_status"),
        server_default="normal",
    )
    op.alter_column(
        "blocks",
        "type",
        existing_type=sa.Enum("general", "function", "nonfunction", name="block_type"),
        server_default="general",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "blocks",
        "type",
        existing_type=sa.Enum("general", "function", "nonfunction", name="block_type"),
        server_default=None,
    )
    op.alter_column(
        "blocks",
        "status",
        existing_type=sa.Enum("urgent", "normal", name="block_status"),
        server_default=None,
    )
    op.alter_column(
        "users",
        "is_active",
        existing_type=sa.SmallInteger(),
        server_default=None,
    )
