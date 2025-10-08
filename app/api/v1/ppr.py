from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from typing import List
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

logger = get_logger(__name__)


router = APIRouter()


@router.get("/", response_class=JSONResponse)
async def get_pprs(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Obtener lista de PPRs
    """
    try:
        logger.info(f"User {current_user.nombre} ({current_user.email}) requesting PPR list")
        pprs = session.exec(select(PPR)).all()
        # Convert to dict to ensure JSON serializable
        ppr_dicts = []
        for ppr in pprs:
            ppr_dict = {
                "id_ppr": ppr.id_ppr,
                "codigo_ppr": ppr.codigo_ppr,
                "nombre_ppr": ppr.nombre_ppr,
                "anio": ppr.anio,
                "estado": ppr.estado,
                "fecha_creacion": ppr.fecha_creacion.isoformat() if ppr.fecha_creacion else None,
                "fecha_actualizacion": ppr.fecha_actualizacion.isoformat() if ppr.fecha_actualizacion else None
            }
            ppr_dicts.append(ppr_dict)
        
        logger.info(f"Successfully retrieved {len(ppr_dicts)} PPRs for user {current_user.email}")
        return {"data": ppr_dicts, "message": "PPRs obtenidos exitosamente"}
    except Exception as e:
        logger.error(f"Error retrieving PPRs for user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener los PPRs: {str(e)}"
        )


@router.get("/{ppr_id}", response_class=JSONResponse)
async def get_ppr(
    ppr_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Obtener un PPR por ID
    """
    try:
        logger.info(f"User {current_user.nombre} ({current_user.email}) requesting PPR with ID {ppr_id}")
        ppr = session.get(PPR, ppr_id)
        if not ppr:
            logger.warning(f"PPR with ID {ppr_id} not found, requested by user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PPR no encontrado"
            )
        
        # Convert to dict to ensure JSON serializable
        ppr_dict = {
            "id_ppr": ppr.id_ppr,
            "codigo_ppr": ppr.codigo_ppr,
            "nombre_ppr": ppr.nombre_ppr,
            "anio": ppr.anio,
            "estado": ppr.estado,
            "fecha_creacion": ppr.fecha_creacion.isoformat() if ppr.fecha_creacion else None,
            "fecha_actualizacion": ppr.fecha_actualizacion.isoformat() if ppr.fecha_actualizacion else None
        }
        
        logger.info(f"Successfully retrieved PPR {ppr_id} for user {current_user.email}")
        return {"data": ppr_dict, "message": "PPR obtenido exitosamente"}
    except HTTPException:
        logger.warning(f"HTTP exception when retrieving PPR {ppr_id} for user {current_user.email}")
        raise
    except Exception as e:
        logger.error(f"Error retrieving PPR {ppr_id} for user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el PPR: {str(e)}"
        )


@router.post("/", response_class=JSONResponse)
async def create_ppr(
    ppr_data: PPRBase,
    current_user: User = Depends(require_responsable_ppr),
    session: Session = Depends(get_session)
):
    """
    Crear un nuevo PPR
    """
    try:
        logger.info(f"User {current_user.nombre} ({current_user.email}) attempting to create PPR with code {ppr_data.codigo_ppr} for year {ppr_data.anio}")
        
        # Verificar si ya existe un PPR con el mismo código y año
        existing_ppr = session.exec(
            select(PPR).where(PPR.codigo_ppr == ppr_data.codigo_ppr, PPR.anio == ppr_data.anio)
        ).first()
        
        if existing_ppr:
            logger.warning(f"Attempt to create duplicate PPR with code {ppr_data.codigo_ppr} and year {ppr_data.anio} by user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un PPR con el mismo código y año"
            )
        
        # Crear nuevo PPR
        new_ppr = PPR(
            codigo_ppr=ppr_data.codigo_ppr,
            nombre_ppr=ppr_data.nombre_ppr,
            anio=ppr_data.anio,
            estado=ppr_data.estado
        )
        
        session.add(new_ppr)
        session.commit()
        session.refresh(new_ppr)
        
        # Convert to dict to ensure JSON serializable
        new_ppr_dict = {
            "id_ppr": new_ppr.id_ppr,
            "codigo_ppr": new_ppr.codigo_ppr,
            "nombre_ppr": new_ppr.nombre_ppr,
            "anio": new_ppr.anio,
            "estado": new_ppr.estado,
            "fecha_creacion": new_ppr.fecha_creacion.isoformat() if new_ppr.fecha_creacion else None,
            "fecha_actualizacion": new_ppr.fecha_actualizacion.isoformat() if new_ppr.fecha_actualizacion else None
        }
        
        logger.info(f"Successfully created PPR {new_ppr.id_ppr} with code {ppr_data.codigo_ppr} by user {current_user.email}")
        return {"data": new_ppr_dict, "message": "PPR creado exitosamente"}
    except HTTPException:
        logger.warning(f"HTTP exception when creating PPR for user {current_user.email}")
        raise
    except Exception as e:
        logger.error(f"Error creating PPR for user {current_user.email}: {str(e)}", exc_info=True)
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el PPR: {str(e)}"
        )


@router.put("/{ppr_id}", response_class=JSONResponse)
async def update_ppr(
    ppr_id: int,
    ppr_data: PPRBase,
    current_user: User = Depends(require_responsable_ppr),
    session: Session = Depends(get_session)
):
    """
    Actualizar un PPR existente
    """
    try:
        logger.info(f"User {current_user.nombre} ({current_user.email}) attempting to update PPR with ID {ppr_id}")
        
        ppr = session.get(PPR, ppr_id)
        if not ppr:
            logger.warning(f"Attempt to update non-existent PPR {ppr_id} by user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PPR no encontrado"
            )
        
        # Actualizar campos
        ppr.codigo_ppr = ppr_data.codigo_ppr
        ppr.nombre_ppr = ppr_data.nombre_ppr
        ppr.anio = ppr_data.anio
        ppr.estado = ppr_data.estado
        
        session.add(ppr)
        session.commit()
        session.refresh(ppr)
        
        # Convert to dict to ensure JSON serializable
        ppr_dict = {
            "id_ppr": ppr.id_ppr,
            "codigo_ppr": ppr.codigo_ppr,
            "nombre_ppr": ppr.nombre_ppr,
            "anio": ppr.anio,
            "estado": ppr.estado,
            "fecha_creacion": ppr.fecha_creacion.isoformat() if ppr.fecha_creacion else None,
            "fecha_actualizacion": ppr.fecha_actualizacion.isoformat() if ppr.fecha_actualizacion else None
        }
        
        logger.info(f"Successfully updated PPR {ppr_id} by user {current_user.email}")
        return {"data": ppr_dict, "message": "PPR actualizado exitosamente"}
    except HTTPException:
        logger.warning(f"HTTP exception when updating PPR {ppr_id} for user {current_user.email}")
        raise
    except Exception as e:
        logger.error(f"Error updating PPR {ppr_id} for user {current_user.email}: {str(e)}", exc_info=True)
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el PPR: {str(e)}"
        )


@router.delete("/{ppr_id}", response_class=JSONResponse)
async def delete_ppr(
    ppr_id: int,
    current_user: User = Depends(require_responsable_ppr),
    session: Session = Depends(get_session)
):
    """
    Eliminar un PPR
    """
    try:
        logger.info(f"User {current_user.nombre} ({current_user.email}) attempting to delete PPR with ID {ppr_id}")
        
        ppr = session.get(PPR, ppr_id)
        if not ppr:
            logger.warning(f"Attempt to delete non-existent PPR {ppr_id} by user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PPR no encontrado"
            )
        
        session.delete(ppr)
        session.commit()
        
        logger.info(f"Successfully deleted PPR {ppr_id} by user {current_user.email}")
        return {"message": "PPR eliminado exitosamente"}
    except HTTPException:
        logger.warning(f"HTTP exception when deleting PPR {ppr_id} for user {current_user.email}")
        raise
    except Exception as e:
        logger.error(f"Error deleting PPR {ppr_id} for user {current_user.email}: {str(e)}", exc_info=True)
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el PPR: {str(e)}"
        )


# Additional endpoints for PPR hierarchy management
@router.get("/{ppr_id}/productos", response_class=JSONResponse)
async def get_productos(
    ppr_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Obtener productos de un PPR
    """
    try:
        logger.info(f"User {current_user.nombre} ({current_user.email}) requesting products for PPR {ppr_id}")
        
        productos = session.exec(
            select(Producto).where(Producto.id_ppr == ppr_id)
        ).all()
        # Convert to dict to ensure JSON serializable
        producto_dicts = []
        for producto in productos:
            producto_dict = {
                "id_producto": producto.id_producto,
                "id_ppr": producto.id_ppr,
                "codigo_producto": producto.codigo_producto,
                "nombre_producto": producto.nombre_producto,
                "fecha_creacion": producto.fecha_creacion.isoformat() if producto.fecha_creacion else None,
                "fecha_actualizacion": producto.fecha_actualizacion.isoformat() if producto.fecha_actualizacion else None
            }
            producto_dicts.append(producto_dict)
            
        logger.info(f"Successfully retrieved {len(producto_dicts)} products for PPR {ppr_id} for user {current_user.email}")
        return {"data": producto_dicts, "message": "Productos obtenidos exitosamente"}
    except Exception as e:
        logger.error(f"Error retrieving products for PPR {ppr_id} for user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener los productos: {str(e)}"
        )


@router.get("/{ppr_id}/detalle", response_class=JSONResponse)
async def get_ppr_detalle(
    ppr_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Obtener detalle completo de un PPR (productos, actividades, subproductos)
    """
    try:
        logger.info(f"User {current_user.nombre} ({current_user.email}) requesting detailed information for PPR {ppr_id}")
        
        ppr = session.get(PPR, ppr_id)
        if not ppr:
            logger.warning(f"Request for non-existent PPR {ppr_id} by user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PPR no encontrado"
            )
        
        # Convert PPR to dictionary
        ppr_dict = {
            "id_ppr": ppr.id_ppr,
            "codigo_ppr": ppr.codigo_ppr,
            "nombre_ppr": ppr.nombre_ppr,
            "anio": ppr.anio,
            "estado": ppr.estado,
            "fecha_creacion": ppr.fecha_creacion.isoformat() if ppr.fecha_creacion else None,
            "fecha_actualizacion": ppr.fecha_actualizacion.isoformat() if ppr.fecha_actualizacion else None
        }
        
        # Obtener productos del PPR
        productos = session.exec(
            select(Producto).where(Producto.id_ppr == ppr_id)
        ).all()
        
        # Convert productos to dictionaries with actividades
        producto_dicts = []
        for producto in productos:
            producto_dict = {
                "id_producto": producto.id_producto,
                "id_ppr": producto.id_ppr,
                "codigo_producto": producto.codigo_producto,
                "nombre_producto": producto.nombre_producto,
                "fecha_creacion": producto.fecha_creacion.isoformat() if producto.fecha_creacion else None,
                "fecha_actualizacion": producto.fecha_actualizacion.isoformat() if producto.fecha_actualizacion else None
            }
            
            # Obtener actividades del producto
            actividades = session.exec(
                select(Actividad).where(Actividad.id_producto == producto.id_producto)
            ).all()
            
            # Convert actividades to dictionaries with subproductos
            actividad_dicts = []
            for actividad in actividades:
                actividad_dict = {
                    "id_actividad": actividad.id_actividad,
                    "id_producto": actividad.id_producto,
                    "codigo_actividad": actividad.codigo_actividad,
                    "nombre_actividad": actividad.nombre_actividad,
                    "fecha_creacion": actividad.fecha_creacion.isoformat() if actividad.fecha_creacion else None,
                    "fecha_actualizacion": actividad.fecha_actualizacion.isoformat() if actividad.fecha_actualizacion else None
                }
                
                # Obtener subproductos de la actividad
                subproductos = session.exec(
                    select(Subproducto).where(Subproducto.id_actividad == actividad.id_actividad)
                ).all()
                
                # Convert subproductos to dictionaries
                subproducto_dicts = []
                for subproducto in subproductos:
                    subproducto_dict = {
                        "id_subproducto": subproducto.id_subproducto,
                        "id_actividad": subproducto.id_actividad,
                        "codigo_subproducto": subproducto.codigo_subproducto,
                        "nombre_subproducto": subproducto.nombre_subproducto,
                        "unidad_medida": subproducto.unidad_medida,
                        "fecha_creacion": subproducto.fecha_creacion.isoformat() if subproducto.fecha_creacion else None,
                        "fecha_actualizacion": subproducto.fecha_actualizacion.isoformat() if subproducto.fecha_actualizacion else None
                    }
                    subproducto_dicts.append(subproducto_dict)
                
                actividad_dict["subproductos"] = subproducto_dicts
                actividad_dicts.append(actividad_dict)
            
            producto_dict["actividades"] = actividad_dicts
            producto_dicts.append(producto_dict)
        
        ppr_detalle = {
            "ppr": ppr_dict,
            "productos": producto_dicts
        }
        
        logger.info(f"Successfully retrieved detailed information for PPR {ppr_id} for user {current_user.email}")
        return {"data": ppr_detalle, "message": "Detalle del PPR obtenido exitosamente"}
    except Exception as e:
        logger.error(f"Error retrieving detailed information for PPR {ppr_id} for user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el detalle del PPR: {str(e)}"
        )
@router.get("/{ppr_id}/estructura", response_class=JSONResponse)
async def get_ppr_estructura(
    ppr_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Obtener estructura del PPR, incluyendo datos de PPR y CEPLAN reales.
    """
    try:
        logger.info(f"User {current_user.nombre} ({current_user.email}) requesting PPR structure for ID {ppr_id}")
        
        ppr = session.get(PPR, ppr_id)
        if not ppr:
            logger.warning(f"Request for non-existent PPR {ppr_id} by user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PPR no encontrado"
            )
        
        from app.models.programacion import ProgramacionPPR, ProgramacionCEPLAN

        ppr_structure = {
            "ppr": {
                "codigo": ppr.codigo_ppr,
                "nombre": ppr.nombre_ppr,
                "anio": ppr.anio
            },
            "productos": []
        }
        
        productos = session.exec(select(Producto).where(Producto.id_ppr == ppr_id)).all()
        
        for producto in productos:
            producto_structure = {
                "codigo_producto": producto.codigo_producto,
                "nombre_producto": producto.nombre_producto,
                "actividades": []
            }
            
            actividades = session.exec(select(Actividad).where(Actividad.id_producto == producto.id_producto)).all()
            
            for actividad in actividades:
                actividad_structure = {
                    "codigo_actividad": actividad.codigo_actividad,
                    "nombre_actividad": actividad.nombre_actividad,
                    "subproductos": []
                }
                
                subproductos = session.exec(select(Subproducto).where(Subproducto.id_actividad == actividad.id_actividad)).all()
                
                for subproducto in subproductos:
                    subproducto_structure = {
                        "codigo_subproducto": subproducto.codigo_subproducto,
                        "nombre_subproducto": subproducto.nombre_subproducto,
                        "unidad_medida": subproducto.unidad_medida,
                        "programacion_ppr": None,
                        "programacion_ceplan": None
                    }
                    
                    # Get PPR programming data
                    programacion_ppr = session.exec(
                        select(ProgramacionPPR).where(
                            ProgramacionPPR.id_subproducto == subproducto.id_subproducto,
                            ProgramacionPPR.anio == ppr.anio
                        )
                    ).first()
                    
                    if programacion_ppr:
                        subproducto_structure["programacion_ppr"] = {
                            "meta_anual": programacion_ppr.meta_anual or 0,
                            "programado": { "ene": programacion_ppr.prog_ene or 0, "feb": programacion_ppr.prog_feb or 0, "mar": programacion_ppr.prog_mar or 0, "abr": programacion_ppr.prog_abr or 0, "may": programacion_ppr.prog_may or 0, "jun": programacion_ppr.prog_jun or 0, "jul": programacion_ppr.prog_jul or 0, "ago": programacion_ppr.prog_ago or 0, "sep": programacion_ppr.prog_sep or 0, "oct": programacion_ppr.prog_oct or 0, "nov": programacion_ppr.prog_nov or 0, "dic": programacion_ppr.prog_dic or 0 },
                            "ejecutado": { "ene": programacion_ppr.ejec_ene or 0, "feb": programacion_ppr.ejec_feb or 0, "mar": programacion_ppr.ejec_mar or 0, "abr": programacion_ppr.ejec_abr or 0, "may": programacion_ppr.ejec_may or 0, "jun": programacion_ppr.ejec_jun or 0, "jul": programacion_ppr.ejec_jul or 0, "ago": programacion_ppr.ejec_ago or 0, "sep": programacion_ppr.ejec_sep or 0, "oct": programacion_ppr.ejec_oct or 0, "nov": programacion_ppr.ejec_nov or 0, "dic": programacion_ppr.ejec_dic or 0 }
                        }

                    # Get CEPLAN programming data
                    programacion_ceplan = session.exec(
                        select(ProgramacionCEPLAN).where(
                            ProgramacionCEPLAN.id_subproducto == subproducto.id_subproducto,
                            ProgramacionCEPLAN.anio == ppr.anio
                        )
                    ).first()

                    if programacion_ceplan:
                        # CEPLAN meta is the sum of its monthly values
                        meta_ceplan = sum([getattr(programacion_ceplan, f'prog_{m}', 0) or 0 for m in ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']])
                        subproducto_structure["programacion_ceplan"] = {
                            "meta_anual": meta_ceplan,
                            "programado": { "ene": programacion_ceplan.prog_ene or 0, "feb": programacion_ceplan.prog_feb or 0, "mar": programacion_ceplan.prog_mar or 0, "abr": programacion_ceplan.prog_abr or 0, "may": programacion_ceplan.prog_may or 0, "jun": programacion_ceplan.prog_jun or 0, "jul": programacion_ceplan.prog_jul or 0, "ago": programacion_ceplan.prog_ago or 0, "sep": programacion_ceplan.prog_sep or 0, "oct": programacion_ceplan.prog_oct or 0, "nov": programacion_ceplan.prog_nov or 0, "dic": programacion_ceplan.prog_dic or 0 },
                            "ejecutado": { "ene": programacion_ceplan.ejec_ene or 0, "feb": programacion_ceplan.ejec_feb or 0, "mar": programacion_ceplan.ejec_mar or 0, "abr": programacion_ceplan.ejec_abr or 0, "may": programacion_ceplan.ejec_may or 0, "jun": programacion_ceplan.ejec_jun or 0, "jul": programacion_ceplan.ejec_jul or 0, "ago": programacion_ceplan.ejec_ago or 0, "sep": programacion_ceplan.ejec_sep or 0, "oct": programacion_ceplan.ejec_oct or 0, "nov": programacion_ceplan.ejec_nov or 0, "dic": programacion_ceplan.ejec_dic or 0 }
                        }

                    actividad_structure["subproductos"].append(subproducto_structure)
                
                producto_structure["actividades"].append(actividad_structure)
            
            ppr_structure["productos"].append(producto_structure)
        
        logger.info(f"Successfully retrieved PPR structure for ID {ppr_id} for user {current_user.email}")
        return {
            "data": ppr_structure,
            "message": "Estructura del PPR obtenida exitosamente"
        }
        
    except HTTPException:
        logger.warning(f"HTTP exception when retrieving PPR structure {ppr_id} for user {current_user.email}")
        raise
    except Exception as e:
        logger.error(f"Error retrieving PPR structure {ppr_id} for user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener la estructura del PPR: {str(e)}"
        )


@router.post("/create-from-cartera", response_class=JSONResponse)
async def create_ppr_from_cartera(
    anio: int,
    current_user: User = Depends(require_responsable_ppr),  # Only Budget Responsible or Admin
    session: Session = Depends(get_session)
):
    """
    Create PPR structure from existing Cartera de Servicios records
    """
    try:
        logger.info(f"User {current_user.nombre} ({current_user.email}) attempting to create PPR from Cartera records for year {anio}")
        
        # Get all cartera records
        cartera_records = session.exec(select(CarteraServicios)).all()
        
        if not cartera_records:
            logger.warning(f"No Cartera records found for PPR creation by user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No hay registros de Cartera de Servicios disponibles"
            )
        
        # Group cartera records by program code to create PPRs
        ppr_data = {}
        for record in cartera_records:
            programa_codigo = record.programa_codigo
            programa_nombre = record.programa_nombre
            
            if programa_codigo not in ppr_data:
                ppr_data[programa_codigo] = {
                    "nombre": programa_nombre,
                    "productos": {}
                }
            
            # Ensure producto exists
            producto_codigo = record.producto_codigo
            producto_nombre = record.producto_nombre
            if producto_codigo not in ppr_data[programa_codigo]["productos"]:
                ppr_data[programa_codigo]["productos"][producto_codigo] = {
                    "nombre": producto_nombre,
                    "actividades": {}
                }
            
            # Ensure actividad exists
            actividad_codigo = record.actividad_codigo
            actividad_nombre = record.actividad_nombre
            if actividad_codigo not in ppr_data[programa_codigo]["productos"][producto_codigo]["actividades"]:
                ppr_data[programa_codigo]["productos"][producto_codigo]["actividades"][actividad_codigo] = {
                    "nombre": actividad_nombre,
                    "subproductos": {}
                }
            
            # Add subproducto
            subproducto_codigo = record.sub_producto_codigo
            subproducto_nombre = record.sub_producto_nombre
            unidad_medida = record.unidad_medida
            if subproducto_codigo not in ppr_data[programa_codigo]["productos"][producto_codigo]["actividades"][actividad_codigo]["subproductos"]:
                ppr_data[programa_codigo]["productos"][producto_codigo]["actividades"][actividad_codigo]["subproductos"][subproducto_codigo] = {
                    "nombre": subproducto_nombre,
                    "unidad_medida": unidad_medida
                }
        
        created_pprs = []
        total_subproductos = 0
        
        # Process each PPR
        for programa_codigo, ppr_info in ppr_data.items():
            # Check if PPR already exists for this year and code
            existing_ppr = session.exec(
                select(PPR).where(PPR.codigo_ppr == programa_codigo, PPR.anio == anio)
            ).first()
            
            if existing_ppr:
                logger.warning(f"PPR with code {programa_codigo} already exists for year {anio}, skipping creation")
                continue
            
            # Create new PPR
            new_ppr = PPR(
                codigo_ppr=programa_codigo,
                nombre_ppr=ppr_info["nombre"],
                anio=anio,
                estado="activo"
            )
            
            session.add(new_ppr)
            session.flush()  # Get the ID without committing
            
            # Create products for this PPR
            for producto_codigo, producto_info in ppr_info["productos"].items():
                new_producto = Producto(
                    codigo_producto=producto_codigo,
                    nombre_producto=producto_info["nombre"],
                    id_ppr=new_ppr.id_ppr
                )
                
                session.add(new_producto)
                session.flush()  # Get the ID
                
                # Create activities for this product
                for actividad_codigo, actividad_info in producto_info["actividades"].items():
                    new_actividad = Actividad(
                        codigo_actividad=actividad_codigo,
                        nombre_actividad=actividad_info["nombre"],
                        id_producto=new_producto.id_producto
                    )
                    
                    session.add(new_actividad)
                    session.flush()  # Get the ID
                    
                    # Create subproducts for this activity
                    for subproducto_codigo, subproducto_info in actividad_info["subproductos"].items():
                        new_subproducto = Subproducto(
                            codigo_subproducto=subproducto_codigo,
                            nombre_subproducto=subproducto_info["nombre"],
                            unidad_medida=subproducto_info["unidad_medida"],
                            id_actividad=new_actividad.id_actividad
                        )
                        
                        session.add(new_subproducto)
                        session.flush()  # Get the ID
                        
                        # Create PPR programming with zero values
                        programacion_ppr = ProgramacionPPR(
                            id_subproducto=new_subproducto.id_subproducto,
                            anio=anio,
                            meta_anual=0.0,
                            prog_ene=0.0, ejec_ene=0.0,
                            prog_feb=0.0, ejec_feb=0.0,
                            prog_mar=0.0, ejec_mar=0.0,
                            prog_abr=0.0, ejec_abr=0.0,
                            prog_may=0.0, ejec_may=0.0,
                            prog_jun=0.0, ejec_jun=0.0,
                            prog_jul=0.0, ejec_jul=0.0,
                            prog_ago=0.0, ejec_ago=0.0,
                            prog_sep=0.0, ejec_sep=0.0,
                            prog_oct=0.0, ejec_oct=0.0,
                            prog_nov=0.0, ejec_nov=0.0,
                            prog_dic=0.0, ejec_dic=0.0
                        )
                        
                        session.add(programacion_ppr)
                        
                        # Create CEPLAN programming with zero values
                        programacion_ceplan = ProgramacionCEPLAN(
                            id_subproducto=new_subproducto.id_subproducto,
                            anio=anio,
                            prog_ene=0.0, ejec_ene=0.0,
                            prog_feb=0.0, ejec_feb=0.0,
                            prog_mar=0.0, ejec_mar=0.0,
                            prog_abr=0.0, ejec_abr=0.0,
                            prog_may=0.0, ejec_may=0.0,
                            prog_jun=0.0, ejec_jun=0.0,
                            prog_jul=0.0, ejec_jul=0.0,
                            prog_ago=0.0, ejec_ago=0.0,
                            prog_sep=0.0, ejec_sep=0.0,
                            prog_oct=0.0, ejec_oct=0.0,
                            prog_nov=0.0, ejec_nov=0.0,
                            prog_dic=0.0, ejec_dic=0.0
                        )
                        
                        session.add(programacion_ceplan)
                        
                        total_subproductos += 1
            
            session.commit()
            created_pprs.append({
                "id_ppr": new_ppr.id_ppr,
                "codigo_ppr": new_ppr.codigo_ppr,
                "nombre_ppr": new_ppr.nombre_ppr
            })
        
        logger.info(f"Successfully created PPR structures from Cartera data by user {current_user.email}. Created {len(created_pprs)} PPRs with {total_subproductos} subproducts.")
        
        return {
            "data": {
                "created_pprs": created_pprs,
                "total_pprs": len(created_pprs),
                "total_subproductos": total_subproductos
            },
            "message": f"Se crearon exitosamente {len(created_pprs)} PPR(s) a partir de los registros de Cartera de Servicios para el año {anio}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating PPR from Cartera data by user {current_user.email}: {str(e)}", exc_info=True)
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el PPR a partir de Cartera: {str(e)}"
        )