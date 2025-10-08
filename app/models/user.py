from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from enum import Enum

from .asignacion import UsuarioPPRAsignacion

if TYPE_CHECKING:
    from .ppr import PPR

class InternalRoleEnum(str, Enum):
    admin = "admin"
    responsable_ppr = "responsable_ppr"
    responsable_planificacion = "responsable_planificacion"

def get_role_display_name(internal_role):
    """Obtener el nombre amigable para mostrar de un rol interno"""
    role_display_map = {
        InternalRoleEnum.admin: "Administrador",
        InternalRoleEnum.responsable_ppr: "Responsable PPR",
        InternalRoleEnum.responsable_planificacion: "Responsable Planificación"
    }
    return role_display_map.get(internal_role, str(internal_role))

def get_role_internal_name(display_name):
    """Obtener el rol interno a partir del nombre amigable"""
    display_to_role_map = {
        "Administrador": InternalRoleEnum.admin,
        "Responsable PPR": InternalRoleEnum.responsable_ppr,
        "Responsable Planificación": InternalRoleEnum.responsable_planificacion,
        "admin": InternalRoleEnum.admin,
        "responsable_ppr": InternalRoleEnum.responsable_ppr,
        "responsable_planificacion": InternalRoleEnum.responsable_planificacion
    }
    return display_to_role_map.get(display_name)


class UserBase(SQLModel):
    nombre: str = Field(max_length=100, description="Nombre del usuario")
    email: str = Field(max_length=150, description="Correo electrónico del usuario", unique=True)
    rol: InternalRoleEnum = Field(description="Rol del usuario en el sistema")


class User(UserBase, table=True):
    """
    Modelo para Usuario
    Incluye sistema de roles y asignaciones a PPRs
    """
    __tablename__ = "usuarios"
    
    id_usuario: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str = Field(max_length=255, description="Contraseña hasheada del usuario")
    is_active: bool = Field(default=True, description="Indica si el usuario está activo")
    
    # Relación muchos a muchos con PPRs
    pprs_asignados: List["PPR"] = Relationship(back_populates="responsables", link_model=UsuarioPPRAsignacion)
    
    # Campos de auditoría
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    fecha_actualizacion: Optional[datetime] = Field(default=None)
    
    @property
    def rol_display(self):
        """Obtener el nombre amigable del rol para mostrar en la interfaz"""
        return get_role_display_name(self.rol)
