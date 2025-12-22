"""merge heads

Revision ID: 29fd5bdc6b01
Revises: 6d9b0b87777b, auto
Create Date: 2025-12-21 21:10:30.343317

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29fd5bdc6b01'
down_revision: Union[str, Sequence[str], None] = ('6d9b0b87777b', 'auto')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
