"""add file_ext column to files

Revision ID: b6c7c6e1a2f1
Revises: ab4d1b5c2bd7
Create Date: 2025-12-21 00:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b6c7c6e1a2f1"
down_revision: Union[str, Sequence[str], None] = "ab4d1b5c2bd7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "files",
        sa.Column("file_ext", sa.String(length=16), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("files", "file_ext")