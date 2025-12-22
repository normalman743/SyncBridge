"""add_audit_logs_table

Revision ID: c94f7b4dbc99
Revises: 11b5f174d692
Create Date: 2025-12-21 12:38:48.158523

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c94f7b4dbc99'
down_revision: Union[str, Sequence[str], None] = '11b5f174d692'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('entity_type', sa.Enum('form', 'function', 'nonfunction', 'message', 'file', name='audit_entity_type'), nullable=False),
        sa.Column('entity_id', sa.Integer, nullable=False),
        sa.Column('action', sa.Enum('create', 'update', 'delete', 'status_change', 'merge_subform', name='audit_action'), nullable=False),
        sa.Column('user_id', sa.Integer, nullable=True),
        sa.Column('old_data', sa.JSON, nullable=True),
        sa.Column('new_data', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_audit_logs_user_id', 'audit_logs')
    op.drop_index('ix_audit_logs_created_at', 'audit_logs')
    op.drop_index('ix_audit_logs_entity', 'audit_logs')
    op.drop_table('audit_logs')
    op.execute('DROP TYPE IF EXISTS audit_action')
    op.execute('DROP TYPE IF EXISTS audit_entity_type')
