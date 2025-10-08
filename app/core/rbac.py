from fastapi import Depends, HTTPException, status
from typing import Callable, List
from enum import Enum

from app.models.user import User, InternalRoleEnum as RoleEnum
from app.core.security import get_current_active_user


class RoleAccess:
    """
    Clase para manejar control de acceso basado en roles
    """
    
    @staticmethod
    def require_roles(roles: List[RoleEnum]) -> Callable:
        """
        Decorador para requerir roles específicos
        """
        async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
            if current_user.rol not in roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tiene permisos suficientes para acceder a este recurso"
                )
            return current_user
        return role_checker

    @staticmethod
    def admin_only():
        """
        Requiere rol de administrador
        """
        return RoleAccess.require_roles([RoleEnum.admin])

    @staticmethod
    def responsable_ppr_only():
        """
        Requiere rol de Responsable PPR
        """
        return RoleAccess.require_roles([RoleEnum.responsable_ppr])

    @staticmethod
    def responsable_planificacion_only():
        """
        Requiere rol de Responsable Planificación
        """
        return RoleAccess.require_roles([RoleEnum.responsable_planificacion])

    @staticmethod
    def ppr_responsable_or_admin():
        """
        Requiere rol de Responsable PPR o Administrador
        """
        return RoleAccess.require_roles([RoleEnum.responsable_ppr, RoleEnum.admin])

    @staticmethod
    def planificacion_responsable_or_admin():
        """
        Requiere rol de Responsable Planificación o Administrador
        """
        return RoleAccess.require_roles([RoleEnum.responsable_planificacion, RoleEnum.admin])


# Funciones de acceso directo
def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Requiere rol de administrador
    """
    if current_user.rol != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador"
        )
    return current_user


def require_responsable_ppr(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Requiere rol de Responsable PPR
    """
    if current_user.rol not in [RoleEnum.responsable_ppr, RoleEnum.admin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de Responsable PPR o Administrador"
        )
    return current_user


def require_responsable_planificacion(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Requiere rol de Responsable Planificación
    """
    if current_user.rol not in [RoleEnum.responsable_planificacion, RoleEnum.admin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de Responsable Planificación o Administrador"
        )
    return current_user