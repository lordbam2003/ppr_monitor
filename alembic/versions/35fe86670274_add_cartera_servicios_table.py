"""Add cartera_servicios table

Revision ID: 35fe86670274
Revises: 
Create Date: 2025-10-07 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlmodel  # Ensure sqlmodel is imported


# revision identifiers, used by Alembic.
revision: str = '35fe86670274'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the cartera_servicios table
    op.create_table(
        'cartera_servicios',
        sa.Column('programa_codigo', sa.String(length=10), nullable=False),
        sa.Column('programa_nombre', sa.String(length=200), nullable=False),
        sa.Column('producto_codigo', sa.String(length=20), nullable=False),
        sa.Column('producto_nombre', sa.String(length=400), nullable=False),
        sa.Column('actividad_codigo', sa.String(length=20), nullable=False),
        sa.Column('actividad_nombre', sa.String(length=500), nullable=False),
        sa.Column('sub_producto_codigo', sa.String(length=20), nullable=False),
        sa.Column('sub_producto_nombre', sa.String(length=500), nullable=False),
        sa.Column('trazador', sa.String(length=10), nullable=False),
        sa.Column('unidad_medida', sa.String(length=50), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=False),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # Drop the cartera_servicios table
    op.drop_table('cartera_servicios')