from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List

from app.core.database import get_session
from app.core.security import get_current_active_user
from app.core.rbac import require_admin
from app.models.user import User, InternalRoleEnum as RoleEnum
from app.models.ppr import PPR
from app.schemas.user import UserResponse

router = APIRouter()

@router.get("/responsables", response_model=List[UserResponse])
def get_available_responsables(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a list of all users who can be assigned as a PPR responsible.
    (Users with the 'Responsable PPR' role).
    """
    users = session.exec(
        select(User).where(User.rol == RoleEnum.responsable_ppr).where(User.is_active == True)
    ).all()
    
    # Convert users to response format, handling role enum conversion
    from app.models.user import get_role_display_name
    from app.schemas.user import RoleEnum as DisplayRoleEnum
    
    user_responses = []
    for user in users:
        user_response = UserResponse(
            id_usuario=user.id_usuario,
            nombre=user.nombre,
            email=user.email,
            rol=DisplayRoleEnum(get_role_display_name(user.rol)),  # Convert to display role enum
            is_active=user.is_active,
            fecha_creacion=user.fecha_creacion,
            fecha_actualizacion=user.fecha_actualizacion
        )
        user_responses.append(user_response)
    
    return user_responses

@router.get("/ppr/{ppr_id}/responsables", response_model=List[UserResponse])
def get_ppr_responsables(
    ppr_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get a list of all users assigned to a specific PPR."""
    ppr = session.get(PPR, ppr_id)
    if not ppr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PPR not found")
    
    # Convert users to response format, handling role enum conversion
    from app.models.user import get_role_display_name
    from app.schemas.user import RoleEnum as DisplayRoleEnum
    
    user_responses = []
    for user in ppr.responsables:
        user_response = UserResponse(
            id_usuario=user.id_usuario,
            nombre=user.nombre,
            email=user.email,
            rol=DisplayRoleEnum(get_role_display_name(user.rol)),  # Convert to display role enum
            is_active=user.is_active,
            fecha_creacion=user.fecha_creacion,
            fecha_actualizacion=user.fecha_actualizacion
        )
        user_responses.append(user_response)
    
    return user_responses

@router.post("/ppr/{ppr_id}/responsables/{user_id}", status_code=status.HTTP_201_CREATED)
def assign_responsable(
    ppr_id: int,
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin) # Only admins can assign
):
    """Assign a user as a responsible for a PPR."""
    ppr = session.get(PPR, ppr_id)
    if not ppr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PPR not found")
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.rol != RoleEnum.responsable_ppr:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User does not have the 'Responsable PPR' role")

    if user in ppr.responsables:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already assigned to this PPR")

    ppr.responsables.append(user)
    session.add(ppr)
    session.commit()
    return {"message": f"User '{user.nombre}' assigned to PPR '{ppr.nombre_ppr}' successfully."}

@router.delete("/ppr/{ppr_id}/responsables/{user_id}", status_code=status.HTTP_200_OK)
def remove_responsable(
    ppr_id: int,
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin) # Only admins can unassign
):
    """Remove a user's assignment from a PPR."""
    ppr = session.get(PPR, ppr_id)
    if not ppr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PPR not found")
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user not in ppr.responsables:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User is not assigned to this PPR")

    ppr.responsables.remove(user)
    session.add(ppr)
    session.commit()
    return {"message": f"User '{user.nombre}' removed from PPR '{ppr.nombre_ppr}' successfully."}
