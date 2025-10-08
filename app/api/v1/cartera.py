from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional
import pandas as pd
import os
from pathlib import Path
from datetime import datetime
import hashlib
import json

from app.core.security import get_current_active_user
from app.core.rbac import require_responsable_planificacion, require_admin
from app.models.user import User
from app.core.database import get_session
from sqlmodel import Session, select
from app.core.logging_config import get_logger

# Import the new cartera service
from app.services.cartera_service import cartera_service

logger = get_logger(__name__)

router = APIRouter()


def get_file_hash(file_content: bytes) -> str:
    """Generar hash del archivo para identificación único"""
    return hashlib.sha256(file_content).hexdigest()


@router.post("/")
async def upload_cartera(
    file: UploadFile = File(...),
    current_user: User = Depends(require_responsable_planificacion),  # Only Budget Responsible or Admin
    session: Session = Depends(get_session)
):
    """
    Endpoint para subir archivo de Cartera de Servicios
    """
    logger.info(f"User {current_user.nombre} ({current_user.email}) attempting to upload Cartera file: {file.filename}")
    
    # Verificar tipo de archivo
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        logger.warning(f"Invalid file type attempted by {current_user.email}: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten archivos Excel (.xlsx, .xls)"
        )
    
    # Limitar tamaño del archivo (50MB)
    file_content = await file.read()
    if len(file_content) > 50 * 1024 * 1024:  # 50MB
        logger.warning(f"File too large attempted by {current_user.email}: {file.filename}, size: {len(file_content)} bytes")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo es demasiado grande. Máximo permitido: 50MB"
        )
    
    # Guardar archivo temporalmente
    upload_dir = Path("uploads/cartera")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{file.filename}"
    
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    try:
        # Use the cartera service to parse the file
        cartera_data = cartera_service.extract_cartera_from_file(file_path)
        
        # Store the parsed data temporarily for preview
        import json
        import uuid
        
        # Add upload metadata
        cartera_with_metadata = {
            "filename": file.filename,
            "size": len(file_content),
            "uploaded_by": current_user.nombre,
            "upload_date": datetime.now().isoformat(),
            "cartera_data": cartera_data  # Include the parsed cartera data
        }
        
        # Create a temporary storage directory
        temp_dir = Path("temp/uploads")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate a unique ID for this upload
        preview_id = str(uuid.uuid4())
        temp_file_path = temp_dir / f"cartera_{preview_id}.json"
        
        # Store the preview data
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            json.dump(cartera_with_metadata, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"Cartera file parsed successfully with {cartera_data['total_records']} records: {preview_id}")
        return {
            "message": "Archivo de Cartera de Servicios subido y procesado exitosamente",
            "preview_id": preview_id,
            "total_records": cartera_data['total_records'],
            "status": "parsed_for_preview"
        }
        
    except Exception as e:
        logger.error(f"Error processing Cartera file {file.filename} uploaded by {current_user.email}: {str(e)}", exc_info=True)
        # Borrar archivo si hubo error en el procesamiento
        if file_path.exists():
            file_path.unlink()
        
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error al procesar el archivo: {str(e)}"
        )


@router.get("/preview/{preview_id}")
async def get_cartera_preview(
    preview_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Endpoint para obtener la vista previa del archivo de Cartera de Servicios
    """
    try:
        logger.info(f"User {current_user.nombre} ({current_user.email}) requesting Cartera preview for ID: {preview_id}")
        
        # Verify the preview_id is a valid UUID format
        import uuid
        try:
            uuid.UUID(preview_id)
        except ValueError:
            logger.warning(f"Invalid preview ID format: {preview_id} by user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de vista previa inválido"
            )
        
        # Path to the temporary JSON file (using same construction as upload)
        temp_dir = Path("temp/uploads")
        temp_file_path = temp_dir / f"cartera_{preview_id}.json"
        
        if not temp_file_path.exists():
            logger.warning(f"Cartera preview file not found for ID: {preview_id} by user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vista previa Cartera no encontrada"
            )
        
        # Read and return the preview data
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            preview_data = json.load(f)
        
        logger.info(f"Successfully retrieved Cartera preview for ID: {preview_id} by user {current_user.email}")
        return {
            "preview_id": preview_id,
            "data": preview_data,
            "message": "Vista previa Cartera de Servicios obtenida exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving Cartera preview for ID {preview_id} by user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener la vista previa Cartera: {str(e)}"
        )





@router.get("/")
async def get_cartera(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Endpoint para obtener la lista de Cartera de Servicios
    """
    try:
        logger.info(f"User {current_user.nombre} ({current_user.email}) requesting Cartera list")
        
        # Fetch all cartera records
        from app.models.cartera_servicios import CarteraServicios
        cartera_list = session.exec(select(CarteraServicios)).all()
        
        # Convert to dictionaries
        cartera_dicts = []
        for item in cartera_list:
            cartera_dict = {
                "id": item.id,
                "programa_codigo": item.programa_codigo,
                "programa_nombre": item.programa_nombre,
                "producto_codigo": item.producto_codigo,
                "producto_nombre": item.producto_nombre,
                "actividad_codigo": item.actividad_codigo,
                "actividad_nombre": item.actividad_nombre,
                "sub_producto_codigo": item.sub_producto_codigo,
                "sub_producto_nombre": item.sub_producto_nombre,
                "trazador": item.trazador,
                "unidad_medida": item.unidad_medida,
                "fecha_creacion": item.fecha_creacion.isoformat() if item.fecha_creacion else None,
                "fecha_actualizacion": item.fecha_actualizacion.isoformat() if item.fecha_actualizacion else None
            }
            cartera_dicts.append(cartera_dict)
        
        logger.info(f"Successfully retrieved {len(cartera_dicts)} Cartera records for user {current_user.email}")
        return {
            "data": cartera_dicts,
            "total_count": len(cartera_dicts),
            "message": "Cartera de Servicios obtenida exitosamente"
        }
    except Exception as e:
        logger.error(f"Error retrieving Cartera list for user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener la Cartera de Servicios: {str(e)}"
        )


@router.post("/commit/{preview_id}")
async def commit_cartera(
    preview_id: str,
    current_user: User = Depends(require_responsable_planificacion),  # Only Budget Responsible or Admin
    session: Session = Depends(get_session)
):
    """
    Endpoint para confirmar y persistir Cartera de Servicios en base de datos
    """
    try:
        logger.info(f"User {current_user.nombre} ({current_user.email}) attempting to commit Cartera preview ID: {preview_id}")
        
        # Verify the preview_id is a valid UUID format
        import uuid
        try:
            uuid.UUID(preview_id)
        except ValueError:
            logger.warning(f"Invalid commit ID format: {preview_id} by user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de vista previa inválido"
            )
        
        # Path to the temporary JSON file (using same construction as get_cartera_preview)
        temp_dir = Path("temp/uploads")
        temp_file_path = temp_dir / f"cartera_{preview_id}.json"
        
        if not temp_file_path.exists():
            logger.warning(f"Commit file not found for ID: {preview_id} by user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vista previa Cartera no encontrada"
            )
        
        # Read the preview data
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            preview_data = json.load(f)
        
        # Process and store the Cartera data in the database
        # The preview_data contains the full file structure, but we need to extract the cartera array
        # It's located in preview_data['cartera_data']['cartera']
        cartera_data_to_store = preview_data.get('cartera_data', {})
        cartera_result = cartera_service.store_cartera_data(cartera_data_to_store, session)
        
        # Remove the temporary file after successful commit
        temp_file_path.unlink()
        
        logger.info(f"Successfully committed Cartera data from preview ID: {preview_id} by user {current_user.email}")
        return {
            "preview_id": preview_id,
            "result": cartera_result,
            "message": "Datos de Cartera de Servicios comprometidos exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error committing Cartera data for preview ID {preview_id} by user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al comprometer los datos Cartera: {str(e)}"
        )