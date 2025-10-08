from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from datetime import timedelta
from typing import Any

from app.core.security import authenticate_user, create_access_token, get_current_user, get_current_active_user
from app.core.config import settings
from app.core.database import get_session
from app.models.user import User, InternalRoleEnum, get_role_display_name
from app.schemas.user import Token, UserCreate, UserResponse, UserUpdate, RoleEnum as DisplayRoleEnum
from app.core.security import get_password_hash
from app.core.logging_config import get_logger
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

logger = get_logger(__name__)


router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
) -> Any:
    """
    Endpoint para iniciar sesión y obtener token JWT
    """
    logger.info(f"Login attempt for user: {form_data.username}")
    
    user = session.query(User).filter(User.email == form_data.username).first()
    
    if not user or not authenticate_user(user, form_data.password):
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        logger.warning(f"Attempt to login with inactive user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )
    
    logger.info(f"Successful login for user: {form_data.username}")
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id_usuario)}, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Endpoint para registrar nuevos usuarios (solo para administradores)
    """
    logger.info(f"Admin {current_user.nombre} ({current_user.email}) attempting to register new user with email {user_data.email}")
    
    # Verificar si el usuario actual tiene rol de administrador
    if current_user.rol != InternalRoleEnum.admin:
        logger.warning(f"User {current_user.email} attempted to register user without admin permissions")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para crear usuarios"
        )
    
    # Verificar si el email ya existe
    existing_user = session.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        logger.warning(f"Attempt to register duplicate user with email {user_data.email} by admin {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # Crear nuevo usuario
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        nombre=user_data.nombre,
        email=user_data.email,
        rol=user_data.rol,
        hashed_password=hashed_password,
        is_active=True
    )
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    
    logger.info(f"Successfully registered user {db_user.email} by admin {current_user.email}")
    return db_user


# Esquema personalizado para el endpoint /me con rol en formato amigable
class CurrentUserResponse(BaseModel):
    id_usuario: int
    nombre: str
    email: str
    rol: DisplayRoleEnum
    is_active: bool
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None

@router.get("/me", response_model=CurrentUserResponse)
async def get_user_me(current_user: User = Depends(get_current_active_user)):
    """
    Endpoint para obtener información del usuario actual
    """
    logger.info(f"User {current_user.nombre} ({current_user.email}) requested their profile information")
    
    # Crear un diccionario con los datos del usuario, convirtiendo el rol al formato amigable
    user_data = {
        "id_usuario": current_user.id_usuario,
        "nombre": current_user.nombre,
        "email": current_user.email,
        "rol": get_role_display_name(current_user.rol),
        "is_active": current_user.is_active,
        "fecha_creacion": current_user.fecha_creacion,
        "fecha_actualizacion": current_user.fecha_actualizacion
    }
    
    return CurrentUserResponse(**user_data)


@router.post("/logout")
async def logout():
    """
    Endpoint para cerrar sesión
    """
    # En una implementación real, aquí se podría implementar la lógica de logout
    # como invalidar el token en un blacklist de tokens
    return {"message": "Sesión cerrada exitosamente"}