"""Modify hashed_password field length

Revision ID: 002_fix_passwd_len
Revises: 001_add_hashed_password_length
Create Date: 2025-10-04 11:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '002_fix_passwd_len'
down_revision = '001_add_hashed_password_length'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Modificar la longitud del campo hashed_password para que sea compatible con MariaDB
    op.alter_column('usuarios', 'hashed_password',
                    type_=sa.String(255),
                    existing_type=sa.String(),
                    existing_nullable=False)


def downgrade() -> None:
    # Revertir el cambio a la longitud original (si era distinta)
    op.alter_column('usuarios', 'hashed_password',
                    type_=sa.String(),
                    existing_type=sa.String(255),
                    existing_nullable=False)