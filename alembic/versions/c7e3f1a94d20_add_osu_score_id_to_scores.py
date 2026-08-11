"""add osu_score_id to scores

Revision ID: c7e3f1a94d20
Revises: b4c7a1e9f2d3
Create Date: 2026-08-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7e3f1a94d20"
down_revision: Union[str, None] = "b4c7a1e9f2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scores", sa.Column("osu_score_id", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("scores", "osu_score_id")
