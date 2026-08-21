"""add lazer mod settings and slider tail/large tick stats to scores

Revision ID: d5f2a8c31b47
Revises: c7e3f1a94d20
Create Date: 2026-08-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5f2a8c31b47"
down_revision: Union[str, None] = "c7e3f1a94d20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Lazer mod settings, keyed by acronym: {"DT": {"speed_change": 1.2}}. The
    # acronym alone cannot tell a 1.2x double time from the 1.5x default
    op.add_column("scores", sa.Column("mod_settings", sa.JSON(), nullable=True))
    # Lazer counts slider tails and large ticks towards accuracy, so a play that
    # dropped them is not the play the calculator simulates without them
    op.add_column("scores", sa.Column("large_tick_miss", sa.BigInteger(), nullable=True))
    op.add_column(
        "scores", sa.Column("slider_tail_miss", sa.BigInteger(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("scores", "slider_tail_miss")
    op.drop_column("scores", "large_tick_miss")
    op.drop_column("scores", "mod_settings")
