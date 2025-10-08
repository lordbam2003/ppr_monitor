"""merge heads

Revision ID: 8a5c8c2f0af7
Revises: 002_fix_passwd_len, 35fe86670274
Create Date: 2025-10-07 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a5c8c2f0af7'
down_revision: Union[str, None] = ('002_fix_passwd_len', '35fe86670274')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This is a merge migration, no schema changes needed
    pass


def downgrade() -> None:
    # This is a merge migration, no schema changes needed
    pass