"""add checksum to beatmap

Revision ID: b4c7a1e9f2d3
Revises: 9608b0bd1ba2
Create Date: 2026-08-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4c7a1e9f2d3"
down_revision: Union[str, None] = "9608b0bd1ba2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable: existing rows have no checksum until the beatmap is next seen
    # on a score, and the calculator simply skips caching while it is unknown
    op.add_column("beatmap", sa.Column("checksum", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("beatmap", "checksum")
