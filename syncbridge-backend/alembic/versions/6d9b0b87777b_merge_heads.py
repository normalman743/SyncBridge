"""merge heads

Revision ID: 6d9b0b87777b
Revises: edbe879cab13, b6c7c6e1a2f1
Create Date: 2025-12-21 21:09:19.572849

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d9b0b87777b'
down_revision: Union[str, Sequence[str], None] = ('edbe879cab13', 'b6c7c6e1a2f1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
