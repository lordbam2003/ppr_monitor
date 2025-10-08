"""Add length to hashed_password field

Revision ID: 001_add_hashed_password_length
Revises: 
Create Date: 2025-10-04 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision = '001_add_hashed_password_length'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Para manejar correctamente las tablas existentes, primero borramos si ya existen
    # En realidad, en un entorno real se usaría una estrategia diferente, 
    # pero para desarrollo inicial podemos recrear las tablas básicas
    
    # Eliminar constraint y tabla usuarios si existen
    try:
        op.drop_table('usuarios_ppr_asignaciones')
    except:
        pass  # Si no existe, no pasa nada
    
    try:
        op.drop_table('usuarios')
    except:
        pass  # Si no existe, no pasa nada

    # Crear tablas con la estructura correcta
    op.create_table('usuarios',
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=150), nullable=False),
        sa.Column('rol', sa.Enum('admin', 'responsable_ppr', 'responsable_planificacion', name='rolemenum'), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),  # Longitud especificada
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=False),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id_usuario'),
        sa.UniqueConstraint('email')
    )

    op.create_table('pprs',
        sa.Column('id_ppr', sa.Integer(), nullable=False),
        sa.Column('codigo_ppr', sa.String(length=10), nullable=False),
        sa.Column('nombre_ppr', sa.String(length=255), nullable=False),
        sa.Column('anio', sa.Integer(), nullable=False),
        sa.Column('estado', sa.Enum('activo', 'cerrado', name='estadoppr'), nullable=False),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=False),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id_ppr')
    )

    op.create_table('productos',
        sa.Column('id_producto', sa.Integer(), nullable=False),
        sa.Column('id_ppr', sa.Integer(), nullable=False),
        sa.Column('codigo_producto', sa.String(length=20), nullable=False),
        sa.Column('nombre_producto', sa.String(length=255), nullable=False),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=False),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['id_ppr'], ['pprs.id_ppr'], ),
        sa.PrimaryKeyConstraint('id_producto')
    )

    op.create_table('actividades',
        sa.Column('id_actividad', sa.Integer(), nullable=False),
        sa.Column('id_producto', sa.Integer(), nullable=False),
        sa.Column('codigo_actividad', sa.String(length=20), nullable=False),
        sa.Column('nombre_actividad', sa.String(length=255), nullable=False),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=False),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['id_producto'], ['productos.id_producto'], ),
        sa.PrimaryKeyConstraint('id_actividad')
    )

    op.create_table('subproductos',
        sa.Column('id_subproducto', sa.Integer(), nullable=False),
        sa.Column('id_actividad', sa.Integer(), nullable=False),
        sa.Column('codigo_subproducto', sa.String(length=20), nullable=False),
        sa.Column('nombre_subproducto', sa.String(length=255), nullable=False),
        sa.Column('unidad_medida', sa.String(length=50), nullable=False),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=False),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['id_actividad'], ['actividades.id_actividad'], ),
        sa.PrimaryKeyConstraint('id_subproducto')
    )

    op.create_table('diferencias',
        sa.Column('id_diferencia', sa.Integer(), nullable=False),
        sa.Column('id_subproducto', sa.Integer(), nullable=False),
        sa.Column('anio', sa.Integer(), nullable=False),
        sa.Column('dif_prog_ene', sa.Float(), nullable=True),
        sa.Column('dif_ejec_ene', sa.Float(), nullable=True),
        sa.Column('dif_prog_feb', sa.Float(), nullable=True),
        sa.Column('dif_ejec_feb', sa.Float(), nullable=True),
        sa.Column('dif_prog_mar', sa.Float(), nullable=True),
        sa.Column('dif_ejec_mar', sa.Float(), nullable=True),
        sa.Column('dif_prog_abr', sa.Float(), nullable=True),
        sa.Column('dif_ejec_abr', sa.Float(), nullable=True),
        sa.Column('dif_prog_may', sa.Float(), nullable=True),
        sa.Column('dif_ejec_may', sa.Float(), nullable=True),
        sa.Column('dif_prog_jun', sa.Float(), nullable=True),
        sa.Column('dif_ejec_jun', sa.Float(), nullable=True),
        sa.Column('dif_prog_jul', sa.Float(), nullable=True),
        sa.Column('dif_ejec_jul', sa.Float(), nullable=True),
        sa.Column('dif_prog_ago', sa.Float(), nullable=True),
        sa.Column('dif_ejec_ago', sa.Float(), nullable=True),
        sa.Column('dif_prog_sep', sa.Float(), nullable=True),
        sa.Column('dif_ejec_sep', sa.Float(), nullable=True),
        sa.Column('dif_prog_oct', sa.Float(), nullable=True),
        sa.Column('dif_ejec_oct', sa.Float(), nullable=True),
        sa.Column('dif_prog_nov', sa.Float(), nullable=True),
        sa.Column('dif_ejec_nov', sa.Float(), nullable=True),
        sa.Column('dif_prog_dic', sa.Float(), nullable=True),
        sa.Column('dif_ejec_dic', sa.Float(), nullable=True),
        sa.Column('estado', sa.Enum('ok', 'alerta', 'pendiente_revision', name='estadodiferencia'), nullable=False),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=False),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['id_subproducto'], ['subproductos.id_subproducto'], ),
        sa.PrimaryKeyConstraint('id_diferencia')
    )

    op.create_table('programaciones_ceplan',
        sa.Column('id_prog_ceplan', sa.Integer(), nullable=False),
        sa.Column('id_subproducto', sa.Integer(), nullable=False),
        sa.Column('anio', sa.Integer(), nullable=False),
        sa.Column('prog_ene', sa.Float(), nullable=True),
        sa.Column('ejec_ene', sa.Float(), nullable=True),
        sa.Column('prog_feb', sa.Float(), nullable=True),
        sa.Column('ejec_feb', sa.Float(), nullable=True),
        sa.Column('prog_mar', sa.Float(), nullable=True),
        sa.Column('ejec_mar', sa.Float(), nullable=True),
        sa.Column('prog_abr', sa.Float(), nullable=True),
        sa.Column('ejec_abr', sa.Float(), nullable=True),
        sa.Column('prog_may', sa.Float(), nullable=True),
        sa.Column('ejec_may', sa.Float(), nullable=True),
        sa.Column('prog_jun', sa.Float(), nullable=True),
        sa.Column('ejec_jun', sa.Float(), nullable=True),
        sa.Column('prog_jul', sa.Float(), nullable=True),
        sa.Column('ejec_jul', sa.Float(), nullable=True),
        sa.Column('prog_ago', sa.Float(), nullable=True),
        sa.Column('ejec_ago', sa.Float(), nullable=True),
        sa.Column('prog_sep', sa.Float(), nullable=True),
        sa.Column('ejec_sep', sa.Float(), nullable=True),
        sa.Column('prog_oct', sa.Float(), nullable=True),
        sa.Column('ejec_oct', sa.Float(), nullable=True),
        sa.Column('prog_nov', sa.Float(), nullable=True),
        sa.Column('ejec_nov', sa.Float(), nullable=True),
        sa.Column('prog_dic', sa.Float(), nullable=True),
        sa.Column('ejec_dic', sa.Float(), nullable=True),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=False),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['id_subproducto'], ['subproductos.id_subproducto'], ),
        sa.PrimaryKeyConstraint('id_prog_ceplan')
    )

    op.create_table('programaciones_ppr',
        sa.Column('id_prog_ppr', sa.Integer(), nullable=False),
        sa.Column('id_subproducto', sa.Integer(), nullable=False),
        sa.Column('anio', sa.Integer(), nullable=False),
        sa.Column('meta_anual', sa.Float(), nullable=True),
        sa.Column('prog_ene', sa.Float(), nullable=True),
        sa.Column('ejec_ene', sa.Float(), nullable=True),
        sa.Column('prog_feb', sa.Float(), nullable=True),
        sa.Column('ejec_feb', sa.Float(), nullable=True),
        sa.Column('prog_mar', sa.Float(), nullable=True),
        sa.Column('ejec_mar', sa.Float(), nullable=True),
        sa.Column('prog_abr', sa.Float(), nullable=True),
        sa.Column('ejec_abr', sa.Float(), nullable=True),
        sa.Column('prog_may', sa.Float(), nullable=True),
        sa.Column('ejec_may', sa.Float(), nullable=True),
        sa.Column('prog_jun', sa.Float(), nullable=True),
        sa.Column('ejec_jun', sa.Float(), nullable=True),
        sa.Column('prog_jul', sa.Float(), nullable=True),
        sa.Column('ejec_jul', sa.Float(), nullable=True),
        sa.Column('prog_ago', sa.Float(), nullable=True),
        sa.Column('ejec_ago', sa.Float(), nullable=True),
        sa.Column('prog_sep', sa.Float(), nullable=True),
        sa.Column('ejec_sep', sa.Float(), nullable=True),
        sa.Column('prog_oct', sa.Float(), nullable=True),
        sa.Column('ejec_oct', sa.Float(), nullable=True),
        sa.Column('prog_nov', sa.Float(), nullable=True),
        sa.Column('ejec_nov', sa.Float(), nullable=True),
        sa.Column('prog_dic', sa.Float(), nullable=True),
        sa.Column('ejec_dic', sa.Float(), nullable=True),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=False),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['id_subproducto'], ['subproductos.id_subproducto'], ),
        sa.PrimaryKeyConstraint('id_prog_ppr')
    )

    op.create_table('usuarios_ppr_asignaciones',
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.Column('id_ppr', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['id_ppr'], ['pprs.id_ppr'], ),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuarios.id_usuario'], ),
        sa.PrimaryKeyConstraint('id_usuario', 'id_ppr')
    )


def downgrade() -> None:
    op.drop_table('usuarios_ppr_asignaciones')
    op.drop_table('usuarios')
    op.drop_table('programaciones_ppr')
    op.drop_table('programaciones_ceplan')
    op.drop_table('diferencias')
    op.drop_table('subproductos')
    op.drop_table('actividades')
    op.drop_table('productos')
    op.drop_table('pprs')