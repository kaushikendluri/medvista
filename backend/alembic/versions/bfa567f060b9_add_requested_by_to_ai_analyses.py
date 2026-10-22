"""add requested_by to ai_analyses

Revision ID: bfa567f060b9
Revises: 233a9cd97f03
Create Date: 2026-08-26 19:09:17.633014

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'bfa567f060b9'
down_revision: Union[str, None] = '233a9cd97f03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ai_analyses', sa.Column('requested_by_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_ai_analyses_requested_by_id_users', 'ai_analyses', 'users', ['requested_by_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_ai_analyses_requested_by_id_users', 'ai_analyses', type_='foreignkey')
    op.drop_column('ai_analyses', 'requested_by_id')
