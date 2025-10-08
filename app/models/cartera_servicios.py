from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
from enum import Enum

class TrazadorEnum(str, Enum):
    activo = "X"
    inactivo = "O"  # or other values as needed


class CarteraServiciosBase(SQLModel):
    # Programa - separated into code and name
    programa_codigo: str = Field(max_length=10, description="Código del programa")
    programa_nombre: str = Field(max_length=200, description="Nombre del programa")
    
    # Producto - separated into code and name
    producto_codigo: str = Field(max_length=20, description="Código del producto")
    producto_nombre: str = Field(max_length=400, description="Nombre del producto")
    
    # Actividad - separated into code and name
    actividad_codigo: str = Field(max_length=20, description="Código de la actividad")
    actividad_nombre: str = Field(max_length=500, description="Nombre de la actividad")
    
    # Sub Producto - separated into code and name
    sub_producto_codigo: str = Field(max_length=20, description="Código del sub producto")
    sub_producto_nombre: str = Field(max_length=500, description="Nombre del sub producto")
    
    trazador: str = Field(max_length=10, description="Indicador de trazador (X, O, etc.)")
    unidad_medida: str = Field(max_length=50, description="Unidad de medida")


class CarteraServicios(CarteraServiciosBase, table=True):
    """
    Modelo para Cartera de Servicios
    Contiene la estructura completa de Programa, Producto, Actividad, Sub Producto, Trazador y Unidad de Medida
    Campos separados en código y nombre para facilitar búsquedas
    """
    __tablename__ = "cartera_servicios"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Campos de auditoría
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    fecha_actualizacion: Optional[datetime] = Field(default=None)