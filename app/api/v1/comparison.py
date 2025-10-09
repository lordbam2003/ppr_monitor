from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from app.core.security import get_current_active_user
from app.core.rbac import require_responsable_ppr, require_responsable_planificacion
from app.models.user import User
from app.core.database import get_session
from sqlmodel import Session
from app.services.comparison_service import ComparisonService
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/ppr/{ppr_id}/compare")
async def run_comparison(
    ppr_id: int,
    current_user: User = Depends(require_responsable_planificacion),  # Only Budget Responsible or Admin
    session: Session = Depends(get_session)
):
    """
    Run comparison between PPR and CEPLAN data for a specific PPR
    """
    try:
        logger.info(f"User {current_user.nombre} ({current_user.email}) running comparison for PPR ID: {ppr_id}")
        
        # Calculate comparison
        result = ComparisonService.calculate_comparison(session, ppr_id)
        
        logger.info(f"Comparison completed successfully for PPR ID: {ppr_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running comparison for PPR ID {ppr_id} by user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al calcular la comparación: {str(e)}"
        )


@router.get("/ppr/{ppr_id}/comparison-results")
async def get_comparison_results(
    ppr_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Get comparison results for a specific PPR
    """
    try:
        logger.info(f"User {current_user.nombre} ({current_user.email}) requesting comparison results for PPR ID: {ppr_id}")
        
        results = ComparisonService.get_comparison_results(session, ppr_id)
        
        logger.info(f"Successfully retrieved {len(results)} comparison results for PPR ID: {ppr_id}")
        return {
            "data": results,
            "total_count": len(results),
            "message": "Resultados de comparación obtenidos exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving comparison results for PPR ID {ppr_id} by user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener los resultados de comparación: {str(e)}"
        )


@router.get("/ppr/{ppr_id}/comparison-summary")
async def get_comparison_summary(
    ppr_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Get summary of comparison results for a specific PPR
    """
    try:
        logger.info(f"User {current_user.nombre} ({current_user.email}) requesting comparison summary for PPR ID: {ppr_id}")
        
        summary = ComparisonService.get_comparison_summary(session, ppr_id)
        
        logger.info(f"Successfully retrieved comparison summary for PPR ID: {ppr_id}")
        return {
            "summary": summary,
            "message": "Resumen de comparación obtenido exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving comparison summary for PPR ID {ppr_id} by user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el resumen de comparación: {str(e)}"
        )