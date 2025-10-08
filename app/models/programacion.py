from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum
from .ppr import Subproducto


class ProgramacionPPR(SQLModel, table=True):
    """
    Modelo para Programación/Ejecución (PPR)
    Almacena metas anuales y programación mensual para subproductos PPR
    """
    __tablename__ = "programaciones_ppr"
    
    id_prog_ppr: Optional[int] = Field(default=None, primary_key=True)
    id_subproducto: int = Field(foreign_key="subproductos.id_subproducto", description="ID del subproducto")
    anio: int = Field(description="Año de la programación")
    meta_anual: Optional[float] = Field(default=None, description="Meta anual del subproducto")
    
    # Campos mensuales de programación
    prog_ene: Optional[float] = Field(default=None)
    ejec_ene: Optional[float] = Field(default=None)
    prog_feb: Optional[float] = Field(default=None)
    ejec_feb: Optional[float] = Field(default=None)
    prog_mar: Optional[float] = Field(default=None)
    ejec_mar: Optional[float] = Field(default=None)
    prog_abr: Optional[float] = Field(default=None)
    ejec_abr: Optional[float] = Field(default=None)
    prog_may: Optional[float] = Field(default=None)
    ejec_may: Optional[float] = Field(default=None)
    prog_jun: Optional[float] = Field(default=None)
    ejec_jun: Optional[float] = Field(default=None)
    prog_jul: Optional[float] = Field(default=None)
    ejec_jul: Optional[float] = Field(default=None)
    prog_ago: Optional[float] = Field(default=None)
    ejec_ago: Optional[float] = Field(default=None)
    prog_sep: Optional[float] = Field(default=None)
    ejec_sep: Optional[float] = Field(default=None)
    prog_oct: Optional[float] = Field(default=None)
    ejec_oct: Optional[float] = Field(default=None)
    prog_nov: Optional[float] = Field(default=None)
    ejec_nov: Optional[float] = Field(default=None)
    prog_dic: Optional[float] = Field(default=None)
    ejec_dic: Optional[float] = Field(default=None)
    
    # Relaciones
    subproducto: Subproducto = Relationship(back_populates="programaciones_ppr")
    
    # Campos de auditoría
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    fecha_actualizacion: Optional[datetime] = Field(default=None)


class ProgramacionCEPLAN(SQLModel, table=True):
    """
    Modelo para Programación/Ejecución (CEPLAN)
    Almacena datos oficiales de CEPLAN para comparación con PPR
    """
    __tablename__ = "programaciones_ceplan"
    
    id_prog_ceplan: Optional[int] = Field(default=None, primary_key=True)
    id_subproducto: int = Field(foreign_key="subproductos.id_subproducto", description="ID del subproducto")
    anio: int = Field(description="Año de la programación")
    
    # Campos mensuales de programación CEPLAN
    prog_ene: Optional[float] = Field(default=None)
    ejec_ene: Optional[float] = Field(default=None)
    prog_feb: Optional[float] = Field(default=None)
    ejec_feb: Optional[float] = Field(default=None)
    prog_mar: Optional[float] = Field(default=None)
    ejec_mar: Optional[float] = Field(default=None)
    prog_abr: Optional[float] = Field(default=None)
    ejec_abr: Optional[float] = Field(default=None)
    prog_may: Optional[float] = Field(default=None)
    ejec_may: Optional[float] = Field(default=None)
    prog_jun: Optional[float] = Field(default=None)
    ejec_jun: Optional[float] = Field(default=None)
    prog_jul: Optional[float] = Field(default=None)
    ejec_jul: Optional[float] = Field(default=None)
    prog_ago: Optional[float] = Field(default=None)
    ejec_ago: Optional[float] = Field(default=None)
    prog_sep: Optional[float] = Field(default=None)
    ejec_sep: Optional[float] = Field(default=None)
    prog_oct: Optional[float] = Field(default=None)
    ejec_oct: Optional[float] = Field(default=None)
    prog_nov: Optional[float] = Field(default=None)
    ejec_nov: Optional[float] = Field(default=None)
    prog_dic: Optional[float] = Field(default=None)
    ejec_dic: Optional[float] = Field(default=None)
    
    # Relaciones
    subproducto: Subproducto = Relationship(back_populates="programaciones_ceplan")
    
    # Campos de auditoría
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    fecha_actualizacion: Optional[datetime] = Field(default=None)


class EstadoDiferencia(str, Enum):
    ok = "ok"
    alerta = "alerta"
    pendiente_revision = "pendiente_revision"


class Diferencia(SQLModel, table=True):
    """
    Modelo para Diferencias/Monitoreo
    Almacena diferencias calculadas entre PPR y CEPLAN
    """
    __tablename__ = "diferencias"
    
    id_diferencia: Optional[int] = Field(default=None, primary_key=True)
    id_subproducto: int = Field(foreign_key="subproductos.id_subproducto", description="ID del subproducto")
    anio: int = Field(description="Año de la diferencia")
    
    # Campos de diferencia mensual
    dif_prog_ene: Optional[float] = Field(default=None, description="Diferencia en programación de enero")
    dif_ejec_ene: Optional[float] = Field(default=None, description="Diferencia en ejecución de enero")
    dif_prog_feb: Optional[float] = Field(default=None, description="Diferencia en programación de febrero")
    dif_ejec_feb: Optional[float] = Field(default=None, description="Diferencia en ejecución de febrero")
    dif_prog_mar: Optional[float] = Field(default=None, description="Diferencia en programación de marzo")
    dif_ejec_mar: Optional[float] = Field(default=None, description="Diferencia en ejecución de marzo")
    dif_prog_abr: Optional[float] = Field(default=None, description="Diferencia en programación de abril")
    dif_ejec_abr: Optional[float] = Field(default=None, description="Diferencia en ejecución de abril")
    dif_prog_may: Optional[float] = Field(default=None, description="Diferencia en programación de mayo")
    dif_ejec_may: Optional[float] = Field(default=None, description="Diferencia en ejecución de mayo")
    dif_prog_jun: Optional[float] = Field(default=None, description="Diferencia en programación de junio")
    dif_ejec_jun: Optional[float] = Field(default=None, description="Diferencia en ejecución de junio")
    dif_prog_jul: Optional[float] = Field(default=None, description="Diferencia en programación de julio")
    dif_ejec_jul: Optional[float] = Field(default=None, description="Diferencia en ejecución de julio")
    dif_prog_ago: Optional[float] = Field(default=None, description="Diferencia en programación de agosto")
    dif_ejec_ago: Optional[float] = Field(default=None, description="Diferencia en ejecución de agosto")
    dif_prog_sep: Optional[float] = Field(default=None, description="Diferencia en programación de septiembre")
    dif_ejec_sep: Optional[float] = Field(default=None, description="Diferencia en ejecución de septiembre")
    dif_prog_oct: Optional[float] = Field(default=None, description="Diferencia en programación de octubre")
    dif_ejec_oct: Optional[float] = Field(default=None, description="Diferencia en ejecución de octubre")
    dif_prog_nov: Optional[float] = Field(default=None, description="Diferencia en programación de noviembre")
    dif_ejec_nov: Optional[float] = Field(default=None, description="Diferencia en ejecución de noviembre")
    dif_prog_dic: Optional[float] = Field(default=None, description="Diferencia en programación de diciembre")
    dif_ejec_dic: Optional[float] = Field(default=None, description="Diferencia en ejecución de diciembre")
    
    estado: EstadoDiferencia = Field(default=EstadoDiferencia.pendiente_revision, description="Estado de la diferencia")
    
    # Relaciones
    subproducto: Subproducto = Relationship(back_populates="diferencias")
    
    # Campos de auditoría
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    fecha_actualizacion: Optional[datetime] = Field(default=None)