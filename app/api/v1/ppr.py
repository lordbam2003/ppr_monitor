from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from typing import List, Optional
import pandas as pd
import os
from pathlib import Path
from datetime import datetime

from app.core.security import get_current_active_user
from app.core.rbac import require_responsable_ppr, require_responsable_planificacion
from app.models.user import User
from app.models.ppr import PPR, PPRBase, Producto, Actividad, Subproducto
from app.models.programacion import ProgramacionPPR, ProgramacionCEPLAN
from app.models.cartera_servicios import CarteraServicios
from app.core.database import get_session
from app.core.logging_config import get_logger
from app.services.ppr_service import delete_ppr_data_by_year

logger = get_logger(__name__)


router = APIRouter()

# --- Endpoints de Sincronización (Poner antes de los que usan {id}) ---

@router.post("/sync-with-ceplan", response_class=JSONResponse)
async def sync_with_ceplan(
    anio: int,
    sync_metas: bool = True,
    sync_avances: bool = False,
    current_user: User = Depends(require_responsable_ppr),
    session: Session = Depends(get_session)
):
    """
    Sincronizar las metas o avances desde CEPLAN hacia PPR para un año específico.
    """
    try:
        logger.info(f"User {current_user.nombre} initiating synchronization CEPLAN -> PPR for year {anio}. Metas: {sync_metas}, Avances: {sync_avances}")
        from app.services.ppr_service import sync_ppr_with_ceplan_data
        result = sync_ppr_with_ceplan_data(year=anio, session=session, sync_metas=sync_metas, sync_avances=sync_avances)
        return {"data": result, "message": result["message"]}
    except Exception as e:
        logger.error(f"Error in CEPLAN sync: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al sincronizar con CEPLAN: {str(e)}")

@router.post("/create-from-cartera", response_class=JSONResponse)
async def create_ppr_from_cartera(
    anio: int,
    current_user: User = Depends(require_responsable_ppr),
    session: Session = Depends(get_session)
):
    """
    Crear o actualizar estructura PPR desde Cartera.
    """
    try:
        from app.services.ppr_service import synchronize_ppr_with_cartera
        result = synchronize_ppr_with_cartera(year=anio, session=session)
        return {"data": result, "message": result["message"]}
    except Exception as e:
        logger.error(f"Error synchronizing PPR from Cartera: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al sincronizar: {str(e)}")

# --- Endpoints de CRUD ---

@router.get("/", response_class=JSONResponse)
async def get_pprs(
    anio: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Obtener lista de PPRs filtrada por año"""
    try:
        statement = select(PPR)
        if anio: statement = statement.where(PPR.anio == anio)
        pprs = session.exec(statement).all()
        return {"data": [p.model_dump() for p in pprs], "message": "PPRs obtenidos exitosamente"}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ppr_id}", response_class=JSONResponse)
async def get_ppr(
    ppr_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    ppr = session.get(PPR, ppr_id)
    if not ppr: raise HTTPException(status_code=404, detail="PPR no encontrado")
    return {"data": ppr.model_dump(), "message": "PPR obtenido"}

@router.post("/", response_class=JSONResponse)
async def create_ppr(
    ppr_data: PPRBase,
    current_user: User = Depends(require_responsable_ppr),
    session: Session = Depends(get_session)
):
    new_ppr = PPR(**ppr_data.model_dump())
    session.add(new_ppr)
    session.commit()
    session.refresh(new_ppr)
    return {"data": new_ppr.model_dump(), "message": "Creado"}

@router.delete("/{ppr_id}", response_class=JSONResponse)
async def delete_ppr(
    ppr_id: int,
    current_user: User = Depends(require_responsable_ppr),
    session: Session = Depends(get_session)
):
    ppr = session.get(PPR, ppr_id)
    if not ppr: raise HTTPException(status_code=404, detail="No encontrado")
    session.delete(ppr)
    session.commit()
    return {"message": "Eliminado"}

@router.delete("/by-year/{year}", response_class=JSONResponse)
async def delete_ppr_by_year(
    year: int,
    current_user: User = Depends(require_responsable_ppr),
    session: Session = Depends(get_session)
):
    deleted_count = delete_ppr_data_by_year(year=year, session=session)
    return {"message": f"Eliminados {deleted_count} registros"}

@router.get("/{ppr_id}/estructura", response_class=JSONResponse)
async def get_ppr_estructura(
    ppr_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Obtener estructura filtrada por CEPLAN"""
    try:
        ppr = session.get(PPR, ppr_id)
        if not ppr: raise HTTPException(status_code=404, detail="No encontrado")
        
        ppr_structure = {"ppr": {"codigo": ppr.codigo_ppr, "nombre": ppr.nombre_ppr, "anio": ppr.anio}, "productos": []}
        productos = session.exec(select(Producto).where(Producto.id_ppr == ppr_id)).all()
        
        for producto in productos:
            producto_structure = {"codigo_producto": producto.codigo_producto, "nombre_producto": producto.nombre_producto, "actividades": []}
            actividades = session.exec(select(Actividad).where(Actividad.id_producto == producto.id_producto)).all()
            
            for actividad in actividades:
                actividad_structure = {"codigo_actividad": actividad.codigo_actividad, "nombre_actividad": actividad.nombre_actividad, "subproductos": []}
                subproductos = session.exec(select(Subproducto).where(Subproducto.id_actividad == actividad.id_actividad)).all()
                
                for subproducto in subproductos:
                    cp = session.exec(select(ProgramacionCEPLAN).where(ProgramacionCEPLAN.id_subproducto == subproducto.id_subproducto, ProgramacionCEPLAN.anio == ppr.anio)).first()
                    meta_c = sum([getattr(cp, f'prog_{m}', 0) or 0 for m in ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']]) if cp else 0
                    
                    if meta_c <= 0: continue # FILTRO CEPLAN
                    
                    sub_struct = {
                        "id_subproducto": subproducto.id_subproducto, "codigo_subproducto": subproducto.codigo_subproducto, 
                        "nombre_subproducto": subproducto.nombre_subproducto, "unidad_medida": subproducto.unidad_medida,
                        "programacion_ppr": None,
                        "programacion_ceplan": {
                            "meta_anual": meta_c,
                            "programado": {m: getattr(cp, f'prog_{m}', 0) or 0 for m in ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']},
                            "ejecutado": {m: getattr(cp, f'ejec_{m}', 0) or 0 for m in ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']}
                        } if cp else None
                    }
                    
                    pp = session.exec(select(ProgramacionPPR).where(ProgramacionPPR.id_subproducto == subproducto.id_subproducto, ProgramacionPPR.anio == ppr.anio)).first()
                    if pp:
                        sub_struct["programacion_ppr"] = {
                            "meta_anual": pp.meta_anual or 0,
                            "programado": {m: getattr(pp, f'prog_{m}', 0) or 0 for m in ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']},
                            "ejecutado": {m: getattr(pp, f'ejec_{m}', 0) or 0 for m in ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']}
                        }
                    actividad_structure["subproductos"].append(sub_struct)
                
                if actividad_structure["subproductos"]: producto_structure["actividades"].append(actividad_structure)
            
            if producto_structure["actividades"]: ppr_structure["productos"].append(producto_structure)
            
        return {"data": ppr_structure, "message": "Estructura obtenida"}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/ceplan-all")
async def get_all_ceplan_data(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    ceplan_records = session.exec(select(ProgramacionCEPLAN, Subproducto).join(Subproducto)).all()
    return {"data": [c.model_dump() for c, s in ceplan_records], "message": "Datos CEPLAN"}
