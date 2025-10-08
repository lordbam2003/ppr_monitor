from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum
from .common import ResponseBase


class RoleEnum(str, Enum):
    admin = "Administrador"
    responsable_ppr = "Responsable PPR"
    responsable_planificacion = "Responsable Planificación"


class UserBase(BaseModel):
    nombre: str
    email: EmailStr
    rol: RoleEnum


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    rol: Optional[RoleEnum] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id_usuario: int
    is_active: bool
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str