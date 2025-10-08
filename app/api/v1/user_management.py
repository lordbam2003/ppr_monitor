from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from typing import List

from app.core.security import get_current_active_user, get_password_hash
from app.core.rbac import require_admin
from app.models.user import User, InternalRoleEnum as RoleEnum
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.core.database import get_session


router = APIRouter()


@router.get("/", response_class=JSONResponse)
async def get_users(
    current_user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """
    Obtener lista de usuarios (solo para administradores)
    """
    try:
        users = session.exec(select(User)).all()
        return {"data": [UserResponse.from_orm(user) for user in users], "message": "Usuarios obtenidos exitosamente"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener los usuarios: {str(e)}"
        )


@router.get("/{user_id}", response_class=JSONResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """
    Obtener un usuario por ID (solo para administradores)
    """
    try:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        return {"data": UserResponse.from_orm(user), "message": "Usuario obtenido exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el usuario: {str(e)}"
        )


@router.post("/", response_class=JSONResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """
    Crear un nuevo usuario (solo para administradores)
    """
    try:
        # Verificar si el email ya existe
        existing_user = session.exec(
            select(User).where(User.email == user_data.email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado"
            )
        
        # Crear nuevo usuario
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            nombre=user_data.nombre,
            email=user_data.email,
            rol=user_data.rol,
            hashed_password=hashed_password,
            is_active=user_data.is_active
        )
        
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        
        return {"data": UserResponse.from_orm(new_user), "message": "Usuario creado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el usuario: {str(e)}"
        )


@router.put("/{user_id}", response_class=JSONResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """
    Actualizar un usuario existente (solo para administradores)
    """
    try:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Actualizar campos
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field != "password":  # Handle password separately if needed
                setattr(user, field, value)
        
        # If password is being updated
        if user_data.password:
            user.hashed_password = get_password_hash(user_data.password)
        
        session.add(user)
        session.commit()
        session.refresh(user)
        
        return {"data": UserResponse.from_orm(user), "message": "Usuario actualizado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el usuario: {str(e)}"
        )


@router.delete("/{user_id}", response_class=JSONResponse)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """
    Eliminar un usuario (solo para administradores)
    """
    try:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # No eliminar el usuario administrador principal
        if user.email == "admin@monitorppr.com":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar el usuario administrador principal"
            )
        
        session.delete(user)
        session.commit()
        
        return {"message": "Usuario eliminado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el usuario: {str(e)}"
        )