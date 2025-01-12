"""add highscores table

Revision ID: cd1e2de262f6
Revises: 21d8f46cee1d
Create Date: 2024-12-06 23:59:02.994851

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'cd1e2de262f6'
down_revision: Union[str, None] = '21d8f46cee1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
