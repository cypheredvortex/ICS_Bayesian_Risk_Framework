"""add_purdue_level

Revision ID: 2f1fade8e944
Revises: 3f1fade8e943
Create Date: 2026-08-12 09:00:00.000000

Adds the optional Purdue Enterprise Reference Architecture level to the
assets table.  It is architectural metadata carried by topology assets and
persisted alongside zone/vendor for traceability of archived runs.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f1fade8e944'
down_revision: Union[str, Sequence[str], None] = '3f1fade8e943'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('assets', sa.Column('purdue_level', sa.String(length=16), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('assets', 'purdue_level')
