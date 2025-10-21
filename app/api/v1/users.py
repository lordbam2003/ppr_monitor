from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from pydantic import BaseModel

from app.core.security import get_current_active_user, get_password_hash
from app.core.database import get_session
from app.models.user import User, InternalRoleEnum, get_role_display_name
from app.schemas.user import UserResponse, UserUpdate, UserCreate, RoleEnum
from app.core.logging_config import get_logger

logger = get_logger(__name__)


router = APIRouter()


def is_admin_role(role_value) -> bool:
    """
    Check if the role value corresponds to an admin role
    Handles both new enum values and old display names
    """
    # Convert to string to handle both enum and string values
    role_str = str(role_value).lower()
    
    admin_values = {
        'admin', 
        'administrador', 
        'adminstrador',  # typo that might exist in db
        'administrator'
    }
    
    # Check if it's any of the admin values (case-insensitive)
    if role_str in admin_values:
        return True
    # Check if it's the enum value
    try:
        if role_value == InternalRoleEnum.admin:
            return True
        # Additional check: see if the enum value matches when converted to string
        if role_str == str(InternalRoleEnum.admin).lower():
            return True
    except:
        pass  # In case role_value isn't an enum, continue with string check
    
    return False


def check_admin(user: User) -> None:
    """
    Verificar si el usuario tiene rol de administrador
    """
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
    
    # Convert users to response format, handling role enum conversion
    user_responses = []
    
    for user in users:
        user_response = UserResponse(
            id_usuario=user.id_usuario,
            nombre=user.nombre,
            email=user.email,
            rol=RoleEnum(get_role_display_name(user.rol)),  # Convert to display role enum
            is_active=user.is_active,
            fecha_creacion=user.fecha_creacion,
            fecha_actualizacion=user.fecha_actualizacion
        )
        user_responses.append(user_response)
    
    logger.info(f"Successfully retrieved {len(user_responses)} users for admin {current_user.email}")
    return user_responses


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
    
    # Convert user to response format, handling role enum conversion
    from app.models.user import get_role_display_name
    from app.schemas.user import RoleEnum
    
    user_response = UserResponse(
        id_usuario=user.id_usuario,
        nombre=user.nombre,
        email=user.email,
        rol=RoleEnum(get_role_display_name(user.rol)),  # Convert to display role enum
        is_active=user.is_active,
        fecha_creacion=user.fecha_creacion,
        fecha_actualizacion=user.fecha_actualizacion
    )
    
    logger.info(f"Successfully retrieved user {user.email} for admin {current_user.email}")
    return user_response


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
    # Convert display role enum back to internal role enum before storing in DB
    from app.models.user import get_role_internal_name
    internal_role = get_role_internal_name(user_data.rol)
    
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        nombre=user_data.nombre,
        email=user_data.email,
        rol=internal_role,
        hashed_password=hashed_password,
    )
    
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    # Convert user to response format, handling role enum conversion
    user_response = UserResponse(
        id_usuario=new_user.id_usuario,
        nombre=new_user.nombre,
        email=new_user.email,
        rol=RoleEnum(get_role_display_name(new_user.rol)),  # Convert to display role enum
        is_active=new_user.is_active,
        fecha_creacion=new_user.fecha_creacion,
        fecha_actualizacion=new_user.fecha_actualizacion
    )
    
    logger.info(f"Successfully created user {new_user.email} by admin {current_user.email}")
    return user_response


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
        if field == "rol":
            # Convert display role enum back to internal role enum before storing in DB
            from app.models.user import get_role_internal_name
            internal_role = get_role_internal_name(value)
            setattr(user, field, internal_role)
        else:
            setattr(user, field, value)
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Convert user to response format, handling role enum conversion
    user_response = UserResponse(
        id_usuario=user.id_usuario,
        nombre=user.nombre,
        email=user.email,
        rol=RoleEnum(get_role_display_name(user.rol)),  # Convert to display role enum
        is_active=user.is_active,
        fecha_creacion=user.fecha_creacion,
        fecha_actualizacion=user.fecha_actualizacion
    )
    
    logger.info(f"Successfully updated user {user.email} by admin {current_user.email}")
    return user_response


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


class PasswordUpdate(BaseModel):
    current_password: Optional[str] = None
    new_password: str


@router.put("/{user_id}/password")
async def update_user_password(
    user_id: int,
    password_data: PasswordUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Actualizar contraseña de usuario por ID
    - Solo administradores pueden cambiar cualquier contraseña
    - Usuarios pueden cambiar su propia contraseña si proporcionan la actual
    """
    logger.info(f"User {current_user.nombre} ({current_user.email}) attempting to update password for user with ID {user_id}")
    
    target_user = session.get(User, user_id)
    if not target_user:
        logger.warning(f"Attempt to update password for non-existent user {user_id} by user {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Check permissions
    is_admin = is_admin_role(current_user.rol)
    is_own_account = current_user.id_usuario == target_user.id_usuario
    
    if not is_admin and not (is_own_account and password_data.current_password):
        logger.warning(f"User {current_user.email} attempted to change password without proper permissions for user {target_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para cambiar esta contraseña"
        )
    
    # If it's not an admin changing the password, verify current password
    if not is_admin and password_data.current_password:
        from app.core.security import verify_password
        if not verify_password(password_data.current_password, target_user.hashed_password):
            logger.warning(f"Incorrect current password provided by user {current_user.email} for password change")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contraseña actual incorrecta"
            )
    
    # Update password
    target_user.hashed_password = get_password_hash(password_data.new_password)
    session.add(target_user)
    session.commit()
    
    logger.info(f"Successfully updated password for user {target_user.email} by user {current_user.email}")
    return {"message": "Contraseña actualizada exitosamente"}


@router.get("/current-role", response_model=dict)
async def get_current_user_role(
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener el rol del usuario actual
    """
    logger.info(f"User {current_user.nombre} ({current_user.email}) requested their role information")
    
    return {
        "rol": current_user.rol,
        "rol_display": get_role_display_name(current_user.rol),
        "user_id": current_user.id_usuario,
        "nombre": current_user.nombre,
        "email": current_user.email
    }