from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from app.core.database import get_session
from app.core.security import get_current_active_user
from app.models.user import User
from app.services.ppr_service import update_subproduct_programming
from app.schemas.ppr import SubproductProgrammingUpdate

router = APIRouter()

@router.put("/subproducto/{subproducto_id}")
async def update_subproduct_programming_endpoint(
    subproducto_id: int,
    data: SubproductProgrammingUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    try:
        update_subproduct_programming(subproducto_id, data, session)
        return {"message": "Programación del subproducto actualizada exitosamente."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
