from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List

from app.core.security import get_current_active_user, get_password_hash
from app.core.database import get_session
from app.models.user import User, InternalRoleEnum
from app.schemas.user import UserResponse, UserUpdate, UserCreate
from app.core.logging_config import get_logger

logger = get_logger(__name__)


router = APIRouter()


def is_admin_role(role_value) -> bool:
    """
    Check if the role value corresponds to an admin role
    Handles both new enum values and old display names
    """
    admin_values = {
        'admin', 
        'Admin', 
        'ADMIN', 
        'Administrador', 
        'ADMINISTRADOR',
        'administrador'
    }
    return str(role_value).lower() in [v.lower() for v in admin_values] or role_value == InternalRoleEnum.admin


def check_admin(user: User) -> None:
    """
    Verificar si el usuario tiene rol de administrador
    """
    # Check using both the enum value and possible string representations
    if not is_admin_role(user.rol):
        logger.warning(f"User {user.nombre} ({user.email}) attempted to access admin functionality without proper permissions. Role: {user.rol}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos de administrador"
        )
    logger.info(f"Admin access granted for user {user.nombre} ({user.email})")


@router.get("/", response_model=List[UserResponse])
async def get_users(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Obtener lista de usuarios (solo para administradores)
    """
    logger.info(f"User {current_user.nombre} ({current_user.email}) requesting user list")
    check_admin(current_user)
    
    users = session.exec(select(User)).all()
    logger.info(f"Successfully retrieved {len(users)} users for admin {current_user.email}")
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Obtener usuario por ID (solo para administradores)
    """
    logger.info(f"User {current_user.nombre} ({current_user.email}) requesting user with ID {user_id}")
    check_admin(current_user)
    
    user = session.get(User, user_id)
    if not user:
        logger.warning(f"User {current_user.email} requested non-existent user with ID {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    logger.info(f"Successfully retrieved user {user.email} for admin {current_user.email}")
    return user


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Crear nuevo usuario (solo para administradores)
    """
    logger.info(f"Admin {current_user.nombre} ({current_user.email}) attempting to create new user with email {user_data.email}")
    check_admin(current_user)
    
    # Verificar si el email ya existe
    existing_user = session.exec(
        select(User).where(User.email == user_data.email)
    ).first()
    
    if existing_user:
        logger.warning(f"Attempt to create duplicate user with email {user_data.email} by admin {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # Crear nuevo usuario
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        nombre=user_data.nombre,
        email=user_data.email,
        rol=user_data.rol,  # This should now be a proper InternalRoleEnum value
        hashed_password=hashed_password,
    )
    
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    logger.info(f"Successfully created user {new_user.email} by admin {current_user.email}")
    return new_user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Actualizar usuario por ID (solo para administradores)
    """
    logger.info(f"Admin {current_user.nombre} ({current_user.email}) attempting to update user with ID {user_id}")
    check_admin(current_user)
    
    user = session.get(User, user_id)
    if not user:
        logger.warning(f"Attempt to update non-existent user {user_id} by admin {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Actualizar campos
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field != "password":  # Handle password separately if needed
            setattr(user, field, value)
    
    # If password is being updated
    if user_data.password:
        user.hashed_password = get_password_hash(user_data.password)
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    logger.info(f"Successfully updated user {user.email} by admin {current_user.email}")
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Eliminar usuario por ID (solo para administradores)
    """
    logger.info(f"Admin {current_user.nombre} ({current_user.email}) attempting to delete user with ID {user_id}")
    check_admin(current_user)
    
    user = session.get(User, user_id)
    if not user:
        logger.warning(f"Attempt to delete non-existent user {user_id} by admin {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # No eliminar el usuario administrador principal
    if user.rol == InternalRoleEnum.admin and user.email == "admin@monitorppr.com":
        logger.warning(f"Attempt to delete main admin user by admin {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar el usuario administrador principal"
        )
    
    session.delete(user)
    session.commit()
    
    logger.info(f"Successfully deleted user {user.email} by admin {current_user.email}")
    return {"message": "Usuario eliminado exitosamente"}