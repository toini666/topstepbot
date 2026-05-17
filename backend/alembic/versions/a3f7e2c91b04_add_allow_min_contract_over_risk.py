"""add allow_min_contract_over_risk to account_settings

Revision ID: a3f7e2c91b04
Revises: 5b0f8a4c2d1e
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f7e2c91b04'
down_revision: Union[str, Sequence[str], None] = '5b0f8a4c2d1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'account_settings',
        sa.Column('allow_min_contract_over_risk', sa.Boolean(), nullable=True, server_default=sa.false()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('account_settings', 'allow_min_contract_over_risk')
