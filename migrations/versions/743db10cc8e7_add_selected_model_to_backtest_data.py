"""add_selected_model_to_backtest_data

Revision ID: 743db10cc8e7
Revises: d8c4f8911cbb
Create Date: 2026-01-20 00:27:59.671374

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '743db10cc8e7'
down_revision: Union[str, None] = 'd8c4f8911cbb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add selected_model column to backtest_data table
    op.add_column('backtest_data', sa.Column('selected_model', sa.String(length=50), nullable=True))


def downgrade() -> None:
    # Remove selected_model column from backtest_data table
    op.drop_column('backtest_data', 'selected_model')
