"""add timestamp indexes for logs and trades

Revision ID: 5b0f8a4c2d1e
Revises: 237ddefb7894
Create Date: 2026-02-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5b0f8a4c2d1e'
down_revision: Union[str, Sequence[str], None] = '237ddefb7894'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index('ix_logs_timestamp', 'logs', ['timestamp'], unique=False)
    op.create_index('ix_trades_timestamp', 'trades', ['timestamp'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_trades_timestamp', table_name='trades')
    op.drop_index('ix_logs_timestamp', table_name='logs')
