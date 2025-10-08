from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from enum import Enum

from .asignacion import UsuarioPPRAsignacion

if TYPE_CHECKING:
    from .user import User
    from .programacion import ProgramacionPPR, ProgramacionCEPLAN, Diferencia

class EstadoPPR(str, Enum):
    activo = "activo"
    cerrado = "cerrado"


class PPRBase(SQLModel):
    codigo_ppr: str = Field(max_length=10, description="Código del Programa Presupuestal (ej. 002)")
    nombre_ppr: str = Field(max_length=255, description="Nombre del Programa Presupuestal")
    anio: int = Field(description="Año del Programa Presupuestal")
    estado: EstadoPPR = Field(default=EstadoPPR.activo, description="Estado del PPR")

class PPR(PPRBase, table=True):
    """
    Modelo para Programa Presupuestal (PPR)
    Representa la entidad principal en la jerarquía PPR → producto → actividad → subproducto
    """
    __tablename__ = "pprs"
    
    id_ppr: Optional[int] = Field(default=None, primary_key=True)
    
    # Relaciones
    productos: List["Producto"] = Relationship(back_populates="ppr", cascade_delete=True)
    responsables: List["User"] = Relationship(back_populates="pprs_asignados", link_model=UsuarioPPRAsignacion)
    
    # Campos de auditoría
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    fecha_actualizacion: Optional[datetime] = Field(default=None)


class ProductoBase(SQLModel):
    codigo_producto: str = Field(max_length=20, description="Código del producto")
    nombre_producto: str = Field(max_length=255, description="Nombre del producto")


class Producto(ProductoBase, table=True):
    """
    Modelo para Producto
    Parte de la jerarquía PPR → producto → actividad → subproducto
    """
    __tablename__ = "productos"
    
    id_producto: Optional[int] = Field(default=None, primary_key=True)
    id_ppr: int = Field(foreign_key="pprs.id_ppr", description="ID del PPR al que pertenece")
    
    # Relaciones
    ppr: PPR = Relationship(back_populates="productos")
    actividades: List["Actividad"] = Relationship(back_populates="producto", cascade_delete=True)
    
    # Campos de auditoría
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    fecha_actualizacion: Optional[datetime] = Field(default=None)


class ActividadBase(SQLModel):
    codigo_actividad: str = Field(max_length=20, description="Código de la actividad")
    nombre_actividad: str = Field(max_length=255, description="Nombre de la actividad")


class Actividad(ActividadBase, table=True):
    """
    Modelo para Actividad
    Parte de la jerarquía PPR → producto → actividad → subproducto
    """
    __tablename__ = "actividades"
    
    id_actividad: Optional[int] = Field(default=None, primary_key=True)
    id_producto: int = Field(foreign_key="productos.id_producto", description="ID del producto al que pertenece")
    
    # Relaciones
    producto: Producto = Relationship(back_populates="actividades")
    subproductos: List["Subproducto"] = Relationship(back_populates="actividad", cascade_delete=True)
    
    # Campos de auditoría
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    fecha_actualizacion: Optional[datetime] = Field(default=None)


class SubproductoBase(SQLModel):
    codigo_subproducto: str = Field(max_length=20, description="Código del subproducto")
    nombre_subproducto: str = Field(max_length=255, description="Nombre del subproducto")
    unidad_medida: str = Field(max_length=50, description="Unidad de medida (ej. persona, familia, caso tratado)")


class Subproducto(SubproductoBase, table=True):
    """
    Modelo para Subproducto
    Parte de la jerarquía PPR → producto → actividad → subproducto
    """
    __tablename__ = "subproductos"
    
    id_subproducto: Optional[int] = Field(default=None, primary_key=True)
    id_actividad: int = Field(foreign_key="actividades.id_actividad", description="ID de la actividad a la que pertenece")
    
    # Relaciones
    actividad: Actividad = Relationship(back_populates="subproductos")
    programaciones_ppr: List["ProgramacionPPR"] = Relationship(back_populates="subproducto", cascade_delete=True)
    programaciones_ceplan: List["ProgramacionCEPLAN"] = Relationship(back_populates="subproducto", cascade_delete=True)
    diferencias: List["Diferencia"] = Relationship(back_populates="subproducto", cascade_delete=True)
    
    # Campos de auditoría
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    fecha_actualizacion: Optional[datetime] = Field(default=None)
