import shutil
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
from app.core.rbac import require_responsable_ppr, require_responsable_planificacion
from app.models.user import User
from app.models.ppr import PPR, Producto, Actividad, Subproducto
from app.models.programacion import ProgramacionPPR
from app.core.database import get_session
from sqlmodel import Session, select
import re
from app.core.logging_config import get_logger

# Import the new extraction service
from app.services.extractor_service import ppr_extractor_service, ceplan_extractor_service

logger = get_logger(__name__)

def clean_nan_values(obj):
    """
    Recursively clean NaN values from a data structure to make it JSON serializable
    """
    if isinstance(obj, dict):
        return {key: clean_nan_values(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan_values(item) for item in obj]
    elif pd.isna(obj) or obj is pd.NA or (isinstance(obj, float) and (obj != obj)):  # obj != obj is True for NaN
        return None  # or 0, depending on your preference
    elif isinstance(obj, float) and (obj == float('inf') or obj == float('-inf')):
        return None  # or a large number depending on your preference
    else:
        return obj




router = APIRouter()


def get_file_hash(file_content: bytes) -> str:
    """Generar hash del archivo para identificación único"""
    return hashlib.sha256(file_content).hexdigest()


@router.post("/ppr")
async def upload_ppr(
    file: UploadFile = File(...),
    current_user: User = Depends(require_responsable_ppr),
    session: Session = Depends(get_session)
):
    """
    Endpoint para subir archivo PPR (solo para Responsables PPR o Administradores)
    Extrae la estructura completa: PPR → Productos → Actividades → Subproductos → Unidad de Medida → Programación/Ejecución por mes
    """
    logger.info(f"User {current_user.nombre} ({current_user.email}) attempting to upload PPR file: {file.filename}")
    
    # Verificar tipo de archivo
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        logger.warning(f"Invalid file type attempted by {current_user.email}: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten archivos Excel (.xlsx, .xls)"
        )
    
    # Limitar tamaño del archivo (100MB)
    file_content = await file.read()
    if len(file_content) > 100 * 1024 * 1024:  # 100MB
        logger.warning(f"File too large attempted by {current_user.email}: {file.filename}, size: {len(file_content)} bytes")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo es demasiado grande. Máximo permitido: 100MB"
        )
    
    # Verificar si el archivo ya ha sido subido antes (por hash)
    file_hash = get_file_hash(file_content)
    # Aquí podríamos verificar si ya existe en la base de datos
    
    # Guardar archivo temporalmente
    upload_dir = Path("uploads/ppr")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{file_hash}_{file.filename}"
    
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    try:
        # Use the new extraction service to parse the PPR file with complete hierarchical structure
        # This extracts: PPR → Productos → Actividades → Subproductos → Unidad de Medida → Programación/Ejecución por mes
        ppr_data = ppr_extractor_service.extract_ppr_from_file(file_path)
        
        # Store the parsed data temporarily for preview
        # In a production system, you'd want to store this in a temporary table or cache
        import json
        import uuid
        
        # Add upload metadata
        ppr_data_with_metadata = {
            "filename": file.filename,
            "size": len(file_content),
            "hash": file_hash,
            "uploaded_by": current_user.nombre,
            "upload_date": datetime.now().isoformat(),
            "ppr_data": ppr_data  # Include the parsed PPR data with complete hierarchy
        }
        
        # Clean the data structure to handle NaN and other non-JSON-serializable values
        cleaned_ppr_data = clean_data_for_json(ppr_data_with_metadata)
        
        # Create a temporary storage directory
        temp_dir = Path("temp/uploads")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate a unique ID for this upload
        preview_id = str(uuid.uuid4())
        temp_file_path = temp_dir / f"{preview_id}.json"
        
        # Custom encoder to handle NaN, infinity, and other non-JSON-serializable values
        json_data = json.dumps(cleaned_ppr_data, ensure_ascii=False, indent=2, default=str, allow_nan=False)
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write(json_data)
        
        logger.info(f"PPR file parsed successfully with complete hierarchical structure: {preview_id}")
        return {
            "message": "Archivo PPR subido y procesado exitosamente",
            "preview_id": preview_id,
            "file_info": cleaned_ppr_data,
            "status": "parsed_for_preview"
        }
        
    except Exception as e:
        logger.error(f"Error processing PPR file {file.filename} uploaded by {current_user.email}: {str(e)}", exc_info=True)
        # Borrar archivo si hubo error en el procesamiento
        if file_path.exists():
            file_path.unlink()
        
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error al procesar el archivo: {str(e)}"
        )


def clean_data_for_json(obj):
    """
    Recursively clean data to make it JSON serializable by handling NaN, infinity, etc.
    """
    import pandas as pd
    import math
    
    if isinstance(obj, dict):
        return {key: clean_data_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [clean_data_for_json(item) for item in obj]
    elif isinstance(obj, float):
        if pd.isna(obj) or obj != obj:  # Check for NaN (NaN != NaN is True)
            return 0  # Convert NaN to 0
        elif math.isinf(obj):
            return 0  # Convert infinity to 0
        else:
            return obj
    elif pd.isna(obj):  # Check for pandas NaN
        return 0  # Convert to 0
    elif obj is pd.NaT:  # Check for pandas NaT (Not a Time)
        return 0  # Convert to 0
    else:
        # For other types, try to convert to basic Python types to ensure JSON compatibility
        try:
            # If it's numpy type, convert to Python native type
            if hasattr(obj, 'item'):
                return clean_data_for_json(obj.item())
            return obj
        except:
            # If conversion fails, convert to string as fallback
            return str(obj)


@router.get("/preview/{preview_id}")
async def get_extract_preview(
    preview_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Endpoint para obtener la vista previa del archivo extraído
    """
    try:
        logger.info(f"User {current_user.nombre} ({current_user.email}) requesting preview for ID: {preview_id}")
        
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
        
        # Path to the temporary JSON file
        temp_file_path = Path(f"temp/uploads/{preview_id}.json")
        
        if not temp_file_path.exists():
            logger.warning(f"Preview file not found for ID: {preview_id} by user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vista previa no encontrada"
            )
        
        # Read and return the preview data
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            preview_data = json.load(f)
        
        logger.info(f"Successfully retrieved preview for ID: {preview_id} by user {current_user.email}")
        return {
            "preview_id": preview_id,
            "data": preview_data,
            "message": "Vista previa obtenida exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving preview for ID {preview_id} by user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener la vista previa: {str(e)}"
        )


@router.post("/commit/{preview_id}")
async def commit_extract(
    preview_id: str,
    current_user: User = Depends(require_responsable_ppr),
    session: Session = Depends(get_session)
):
    """
    Endpoint para confirmar y persistir en base de datos
    """
    try:
        logger.info(f"User {current_user.nombre} ({current_user.email}) attempting to commit preview ID: {preview_id}")
        
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
        
        # Path to the temporary JSON file
        temp_file_path = Path(f"temp/uploads/{preview_id}.json")
        
        if not temp_file_path.exists():
            logger.warning(f"Commit file not found for ID: {preview_id} by user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vista previa no encontrada"
            )
        
        # Read the preview data
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            preview_data = json.load(f)
        
        # Process and store the PPR data in the database
        ppr_result = await store_ppr_data(preview_data, session, current_user)
        
        # Remove the temporary file after successful commit
        temp_file_path.unlink()
        
        logger.info(f"Successfully committed PPR data from preview ID: {preview_id} by user {current_user.email}")
        return {
            "preview_id": preview_id,
            "result": ppr_result,
            "message": "Datos PPR comprometidos exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error committing PPR data for preview ID {preview_id} by user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al comprometer los datos: {str(e)}"
        )


def validate_ppr_data_structure(preview_data: dict) -> bool:
    """
    Validate that the provided JSON has the expected PPR data structure
    """
    # Check if 'ppr_data' or 'ppr' exists
    ppr_info = preview_data.get('ppr_data', {}).get('ppr', {})
    if not ppr_info:
        ppr_info = preview_data.get('ppr', {})
    
    if not ppr_info:
        logger.error("No PPR information found in the JSON data")
        return False
    
    required_fields = ['codigo', 'nombre', 'anio']
    for field in required_fields:
        if field not in ppr_info or not str(ppr_info[field]).strip():
            logger.error(f"Missing or empty required field in PPR data: {field}")
            return False
    
    # Validate codigo and nombre are not empty
    ppr_codigo = str(ppr_info['codigo']).strip()
    ppr_nombre = str(ppr_info['nombre']).strip()
    
    if not ppr_codigo or not ppr_nombre:
        logger.error(f"PPR code ('{ppr_codigo}') or name ('{ppr_nombre}') is missing or empty")
        return False
    
    logger.info(f"PPR validation passed - Code: {ppr_codigo}, Name: {ppr_nombre}, Year: {ppr_info['anio']}")
    return True


def safe_convert_to_float(value, default=0):
    """Safely convert a value to float, handling NaN, None, etc."""
    if value is None or pd.isna(value):
        return default
    try:
        val = float(value)
        # Check if it's a valid number (not nan, inf, etc.)
        if pd.isna(val) or val == float('inf') or val == float('-inf'):
            return default
        return val
    except (ValueError, TypeError):
        return default


async def store_ppr_data(preview_data, session, current_user):
    """
    Enhanced function to store PPR data with better validation and error handling
    """
    try:
        # Validate the data structure before processing
        if not validate_ppr_data_structure(preview_data):
            raise ValueError("Invalid or incomplete PPR data structure")
        
        # Extract PPR information
        ppr_info = preview_data.get('ppr_data', {}).get('ppr', {})
        if not ppr_info:
            # Try the simpler structure
            ppr_info = preview_data.get('ppr', {})
        
        ppr_codigo = str(ppr_info.get('codigo', '')).strip()
        ppr_nombre = str(ppr_info.get('nombre', '')).strip()
        ppr_anio = int(ppr_info.get('anio', datetime.now().year))
        
        logger.info(f"Storing PPR data - Code: '{ppr_codigo}', Name: '{ppr_nombre}', Year: {ppr_anio}")
        
        # Check if PPR already exists with same code and year
        existing_ppr = session.exec(
            select(PPR).where(PPR.codigo_ppr == ppr_codigo, PPR.anio == ppr_anio)
        ).first()
        
        if existing_ppr:
            logger.info(f"Updating existing PPR: {existing_ppr.nombre_ppr}")
            # Ensure that nombre_ppr is properly assigned
            existing_ppr.nombre_ppr = ppr_nombre
            existing_ppr.codigo_ppr = ppr_codigo  # Also ensure code is correct
            session.add(existing_ppr)
            session.flush()
            ppr_id = existing_ppr.id_ppr
        else:
            logger.info(f"Creating new PPR: {ppr_nombre}")
            new_ppr = PPR(
                codigo_ppr=ppr_codigo,
                nombre_ppr=ppr_nombre,  # This is the critical fix
                anio=ppr_anio,
                estado="activo"
            )
            session.add(new_ppr)
            session.flush()
            ppr_id = new_ppr.id_ppr
            
        logger.info(f"PPR ID: {ppr_id}")
        
        # Process products, activities, and subproducts
        productos_data = preview_data.get('ppr_data', {}).get('productos', [])
        if not productos_data:
            # Try the simpler structure
            productos_data = preview_data.get('productos', [])
            
        logger.info(f"Processing {len(productos_data)} products...")
        
        processed_products = 0
        for producto_data in productos_data:
            producto_codigo = str(producto_data.get('codigo_producto', '')).strip()
            producto_nombre = str(producto_data.get('nombre_producto', '')).strip()
            
            if not producto_codigo or not producto_nombre:
                logger.warning(f"Skipping product with missing code or name: {producto_codigo} - {producto_nombre}")
                continue
                
            logger.info(f"  Processing product: {producto_codigo} - {producto_nombre}")
            
            # Check if product exists for this PPR
            existing_producto = session.exec(
                select(Producto)
                .where(Producto.codigo_producto == producto_codigo, Producto.id_ppr == ppr_id)
            ).first()
            
            if existing_producto:
                logger.info(f"    Updating existing product: {existing_producto.nombre_producto}")
                existing_producto.nombre_producto = producto_nombre
                session.add(existing_producto)
                session.flush()
                producto_id = existing_producto.id_producto
            else:
                logger.info(f"    Creating new product: {producto_nombre}")
                new_producto = Producto(
                    codigo_producto=producto_codigo,
                    nombre_producto=producto_nombre,
                    id_ppr=ppr_id
                )
                session.add(new_producto)
                session.flush()
                producto_id = new_producto.id_producto
            
            processed_products += 1
            
            # Process activities
            actividades_data = producto_data.get('actividades', [])
            logger.info(f"    Processing {len(actividades_data)} activities...")
            
            for actividad_data in actividades_data:
                actividad_codigo = str(actividad_data.get('codigo_actividad', '')).strip()
                actividad_nombre = str(actividad_data.get('nombre_actividad', '')).strip()
                
                if not actividad_codigo or not actividad_nombre:
                    logger.warning(f"    Skipping activity with missing code or name: {actividad_codigo} - {actividad_nombre}")
                    continue
                    
                logger.info(f"      Processing activity: {actividad_codigo} - {actividad_nombre}")
                
                # Check if activity exists for this product
                existing_actividad = session.exec(
                    select(Actividad)
                    .where(Actividad.codigo_actividad == actividad_codigo, Actividad.id_producto == producto_id)
                ).first()
                
                if existing_actividad:
                    logger.info(f"        Updating existing activity: {existing_actividad.nombre_actividad}")
                    existing_actividad.nombre_actividad = actividad_nombre
                    session.add(existing_actividad)
                    session.flush()
                    actividad_id = existing_actividad.id_actividad
                else:
                    logger.info(f"        Creating new activity: {actividad_nombre}")
                    new_actividad = Actividad(
                        codigo_actividad=actividad_codigo,
                        nombre_actividad=actividad_nombre,
                        id_producto=producto_id
                    )
                    session.add(new_actividad)
                    session.flush()
                    actividad_id = new_actividad.id_actividad
                
                # Process subproducts
                subproductos_data = actividad_data.get('subproductos', [])
                logger.info(f"        Processing {len(subproductos_data)} subproducts...")
                
                for subproducto_data in subproductos_data:
                    subproducto_codigo = str(subproducto_data.get('codigo_subproducto', '')).strip()
                    subproducto_nombre = str(subproducto_data.get('nombre_subproducto', '')).strip()
                    unidad_medida = str(subproducto_data.get('unidad_medida', 'UNIDAD')).strip()
                    meta_anual = subproducto_data.get('meta_anual', 0)
                    
                    if not subproducto_codigo:
                        logger.warning(f"        Skipping subproduct with missing code: {subproducto_nombre}")
                        continue
                        
                    logger.info(f"          Processing subproduct: {subproducto_codigo} - {subproducto_nombre}")
                    
                    # Check if subproduct exists for this activity
                    existing_subproducto = session.exec(
                        select(Subproducto)
                        .where(Subproducto.codigo_subproducto == subproducto_codigo, Subproducto.id_actividad == actividad_id)
                    ).first()
                    
                    if existing_subproducto:
                        logger.info(f"            Updating existing subproduct: {existing_subproducto.nombre_subproducto}")
                        existing_subproducto.nombre_subproducto = subproducto_nombre
                        existing_subproducto.unidad_medida = unidad_medida
                        session.add(existing_subproducto)
                        session.flush()
                        subproducto_id = existing_subproducto.id_subproducto
                    else:
                        logger.info(f"            Creating new subproduct: {subproducto_nombre}")
                        new_subproducto = Subproducto(
                            codigo_subproducto=subproducto_codigo,
                            nombre_subproducto=subproducto_nombre,
                            unidad_medida=unidad_medida,
                            id_actividad=actividad_id
                        )
                        session.add(new_subproducto)
                        session.flush()
                        subproducto_id = new_subproducto.id_subproducto
                        
                        # Create the corresponding programación entries
                        programado_data = subproducto_data.get('programado', {})
                        ejecutado_data = subproducto_data.get('ejecutado', {})
                        
                        logger.info(f"            Creating programación for subproduct {subproducto_codigo}")
                        
                        # Create PPR programación record
                        programacion_ppr = ProgramacionPPR(
                            id_subproducto=subproducto_id,
                            anio=ppr_anio,
                            meta_anual=safe_convert_to_float(meta_anual),
                            # Populate monthly fields
                            prog_ene=safe_convert_to_float(programado_data.get('ene', 0)),
                            ejec_ene=safe_convert_to_float(ejecutado_data.get('ene', 0)),
                            prog_feb=safe_convert_to_float(programado_data.get('feb', 0)),
                            ejec_feb=safe_convert_to_float(ejecutado_data.get('feb', 0)),
                            prog_mar=safe_convert_to_float(programado_data.get('mar', 0)),
                            ejec_mar=safe_convert_to_float(ejecutado_data.get('mar', 0)),
                            prog_abr=safe_convert_to_float(programado_data.get('abr', 0)),
                            ejec_abr=safe_convert_to_float(ejecutado_data.get('abr', 0)),
                            prog_may=safe_convert_to_float(programado_data.get('may', 0)),
                            ejec_may=safe_convert_to_float(ejecutado_data.get('may', 0)),
                            prog_jun=safe_convert_to_float(programado_data.get('jun', 0)),
                            ejec_jun=safe_convert_to_float(ejecutado_data.get('jun', 0)),
                            prog_jul=safe_convert_to_float(programado_data.get('jul', 0)),
                            ejec_jul=safe_convert_to_float(ejecutado_data.get('jul', 0)),
                            prog_ago=safe_convert_to_float(programado_data.get('ago', 0)),
                            ejec_ago=safe_convert_to_float(ejecutado_data.get('ago', 0)),
                            prog_sep=safe_convert_to_float(programado_data.get('sep', 0)),
                            ejec_sep=safe_convert_to_float(ejecutado_data.get('sep', 0)),
                            prog_oct=safe_convert_to_float(programado_data.get('oct', 0)),
                            ejec_oct=safe_convert_to_float(ejecutado_data.get('oct', 0)),
                            prog_nov=safe_convert_to_float(programado_data.get('nov', 0)),
                            ejec_nov=safe_convert_to_float(ejecutado_data.get('nov', 0)),
                            prog_dic=safe_convert_to_float(programado_data.get('dic', 0)),
                            ejec_dic=safe_convert_to_float(ejecutado_data.get('dic', 0)),
                        )
                        session.add(programacion_ppr)
        
        # Commit all changes
        session.commit()
        
        logger.info("PPR data successfully stored to database!")
        logger.info(f"Summary: 1 PPR with {processed_products} products processed.")
        
        # Verify data was inserted correctly
        logger.info("Verifying PPR data in database...")
        final_ppr = session.exec(
            select(PPR).where(PPR.codigo_ppr == ppr_codigo, PPR.anio == ppr_anio)
        ).first()
        
        if final_ppr:
            logger.info(f"✓ PPR found in database: {final_ppr.codigo_ppr} - {final_ppr.nombre_ppr}")
        else:
            logger.warning("✗ PPR not found in database after insertion")
        
        return {
            "ppr_id": final_ppr.id_ppr if final_ppr else None,
            "productos_count": processed_products,
            "message": "Datos PPR almacenados exitosamente"
        }
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error storing PPR data: {str(e)}", exc_info=True)
        raise e


@router.post("/ceplan")
async def upload_ceplan(
    file: UploadFile = File(...),
    current_user: User = Depends(require_responsable_planificacion),
    session: Session = Depends(get_session)
):
    """
    Endpoint para subir archivo CEPLAN (solo para Responsables Planificación o Administradores)
    """
    logger.info(f"User {current_user.nombre} ({current_user.email}) attempting to upload CEPLAN file: {file.filename}")
    
    # Verificar tipo de archivo
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        logger.warning(f"Invalid file type attempted by {current_user.email}: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten archivos Excel (.xlsx, .xls)"
        )
    
    # Limitar tamaño del archivo (100MB)
    file_content = await file.read()
    if len(file_content) > 100 * 1024 * 1024:  # 100MB
        logger.warning(f"File too large attempted by {current_user.email}: {file.filename}, size: {len(file_content)} bytes")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo es demasiado grande. Máximo permitido: 100MB"
        )
    
    # Verificar si el archivo ya ha sido subido antes (por hash)
    file_hash = get_file_hash(file_content)
    
    # Guardar archivo temporalmente
    upload_dir = Path("uploads/ceplan")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{file_hash}_{file.filename}"
    
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    try:
        # Use the new CEPLAN extraction service to parse the CEPLAN file with correct structure
        # This extracts: Subproductos → Unidad de Medida → Programación/Ejecución por mes
        ceplan_data = ceplan_extractor_service.extract_ceplan_from_file(file_path)
        
        # Add upload metadata
        ceplan_info = {
            "filename": file.filename,
            "size": len(file_content),
            "hash": file_hash,
            "uploaded_by": current_user.nombre,
            "upload_date": datetime.now().isoformat(),
            "ceplan_data": ceplan_data  # Include the parsed CEPLAN data with complete structure
        }
        
        # Store the parsed data temporarily for preview
        import json
        import uuid
        
        # Clean the data structure to handle NaN and other non-JSON-serializable values
        cleaned_ceplan_info = clean_data_for_json(ceplan_info)
        
        # Create a temporary storage directory
        temp_dir = Path("temp/uploads")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate a unique ID for this upload
        preview_id = str(uuid.uuid4())
        temp_file_path = temp_dir / f"{preview_id}.json"
        
        # Custom encoder to handle NaN, infinity, and other non-JSON-serializable values
        json_data = json.dumps(cleaned_ceplan_info, ensure_ascii=False, indent=2, default=str, allow_nan=False)
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write(json_data)
        
        logger.info(f"CEPLAN file parsed successfully with complete structure: {preview_id}")
        return {
            "message": "Archivo CEPLAN subido y procesado exitosamente",
            "preview_id": preview_id,
            "file_info": cleaned_ceplan_info,
            "status": "parsed_for_preview"
        }
        
    except Exception as e:
        logger.error(f"Error processing CEPLAN file {file.filename} uploaded by {current_user.email}: {str(e)}", exc_info=True)
        # Borrar archivo si hubo error en el procesamiento
        if file_path.exists():
            file_path.unlink()
        
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error al procesar el archivo: {str(e)}"
        )


from app.models.programacion import ProgramacionCEPLAN
async def store_ceplan_data(preview_data, session, current_user):
    """
    Store the parsed CEPLAN data into the database, with robust subproduct matching.
    """
    try:
        ceplan_data = preview_data.get('ceplan_data', {})
        if not ceplan_data:
            raise ValueError("No CEPLAN data found in the preview data")

        subproductos_data = ceplan_data.get('subproductos', [])
        if not subproductos_data:
            logger.info("No subproducts found in CEPLAN data. Nothing to store.")
            return {"processed_count": 0, "message": "No se encontraron subproductos en los datos de CEPLAN."}

        # --- Robust Matching Logic ---
        # 1. Fetch all existing subproducts and create a normalized lookup map.
        all_subproductos = session.exec(select(Subproducto)).all()
        # The map's key is the code with leading zeros stripped.
        subproducto_map = {sub.codigo_subproducto.lstrip('0'): sub for sub in all_subproductos}
        logger.info(f"Created a lookup map with {len(subproducto_map)} normalized subproduct codes.")

        processed_count = 0
        for subproducto_data in subproductos_data:
            codigo_ceplan = str(subproducto_data.get('codigo_subproducto', '')).strip()
            if not codigo_ceplan:
                continue

            # 2. Normalize the incoming CEPLAN code.
            normalized_code = codigo_ceplan.lstrip('0')
            
            # 3. Find the match in the map.
            existing_subproducto = subproducto_map.get(normalized_code)
            
            if not existing_subproducto:
                logger.warning(f"Subproducto de CEPLAN con código '{codigo_ceplan}' (normalizado: '{normalized_code}') no encontrado en la base de datos. Se omitirá.")
                continue

            logger.info(f"Match found: CEPLAN code '{codigo_ceplan}' matches DB code '{existing_subproducto.codigo_subproducto}'. Storing data.")

            anio = subproducto_data.get('anio', datetime.now().year)
            existing_ceplan = session.exec(
                select(ProgramacionCEPLAN)
                .where(ProgramacionCEPLAN.id_subproducto == existing_subproducto.id_subproducto, 
                       ProgramacionCEPLAN.anio == anio)
            ).first()
            
            programado_data = subproducto_data.get('programado', {})
            ejecutado_data = subproducto_data.get('ejecutado', {})
            
            # Prepare data dictionary
            ceplan_fields = {
                "prog_ene": safe_convert_to_float(programado_data.get('ene', 0)),
                "ejec_ene": safe_convert_to_float(ejecutado_data.get('ene', 0)),
                "prog_feb": safe_convert_to_float(programado_data.get('feb', 0)),
                "ejec_feb": safe_convert_to_float(ejecutado_data.get('feb', 0)),
                "prog_mar": safe_convert_to_float(programado_data.get('mar', 0)),
                "ejec_mar": safe_convert_to_float(ejecutado_data.get('mar', 0)),
                "prog_abr": safe_convert_to_float(programado_data.get('abr', 0)),
                "ejec_abr": safe_convert_to_float(ejecutado_data.get('abr', 0)),
                "prog_may": safe_convert_to_float(programado_data.get('may', 0)),
                "ejec_may": safe_convert_to_float(ejecutado_data.get('may', 0)),
                "prog_jun": safe_convert_to_float(programado_data.get('jun', 0)),
                "ejec_jun": safe_convert_to_float(ejecutado_data.get('jun', 0)),
                "prog_jul": safe_convert_to_float(programado_data.get('jul', 0)),
                "ejec_jul": safe_convert_to_float(ejecutado_data.get('jul', 0)),
                "prog_ago": safe_convert_to_float(programado_data.get('ago', 0)),
                "ejec_ago": safe_convert_to_float(ejecutado_data.get('ago', 0)),
                "prog_sep": safe_convert_to_float(programado_data.get('sep', 0)),
                "ejec_sep": safe_convert_to_float(ejecutado_data.get('sep', 0)),
                "prog_oct": safe_convert_to_float(programado_data.get('oct', 0)),
                "ejec_oct": safe_convert_to_float(ejecutado_data.get('oct', 0)),
                "prog_nov": safe_convert_to_float(programado_data.get('nov', 0)),
                "ejec_nov": safe_convert_to_float(ejecutado_data.get('nov', 0)),
                "prog_dic": safe_convert_to_float(programado_data.get('dic', 0)),
                "ejec_dic": safe_convert_to_float(ejecutado_data.get('dic', 0)),
            }

            if existing_ceplan:
                logger.info(f"Actualizando datos de CEPLAN para subproducto {existing_subproducto.codigo_subproducto} y año {anio}.")
                for key, value in ceplan_fields.items():
                    setattr(existing_ceplan, key, value)
                session.add(existing_ceplan)
            else:
                logger.info(f"Creando nuevos datos de CEPLAN para subproducto {existing_subproducto.codigo_subproducto} y año {anio}.")
                new_ceplan = ProgramacionCEPLAN(
                    id_subproducto=existing_subproducto.id_subproducto,
                    anio=anio,
                    **ceplan_fields
                )
                session.add(new_ceplan)
            
            processed_count += 1
        
        session.commit()
        
        logger.info(f"CEPLAN data successfully stored to database! Processed {processed_count} subproducts.")
        
        return {
            "processed_count": processed_count,
            "message": "Datos CEPLAN almacenados exitosamente"
        }
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error storing CEPLAN data: {str(e)}", exc_info=True)
        raise e


@router.get("/preview-ceplan/{preview_id}")
async def get_ceplan_preview(
    preview_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Endpoint para obtener la vista previa del archivo CEPLAN extraído
    """
    try:
        logger.info(f"User {current_user.nombre} ({current_user.email}) requesting CEPLAN preview for ID: {preview_id}")
        
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
        
        # Path to the temporary JSON file
        temp_file_path = Path(f"temp/uploads/{preview_id}.json")
        
        if not temp_file_path.exists():
            logger.warning(f"CEPLAN preview file not found for ID: {preview_id} by user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vista previa CEPLAN no encontrada"
            )
        
        # Read and return the preview data
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            preview_data = json.load(f)
        
        logger.info(f"Successfully retrieved CEPLAN preview for ID: {preview_id} by user {current_user.email}")
        return {
            "preview_id": preview_id,
            "data": preview_data,
            "message": "Vista previa CEPLAN obtenida exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving CEPLAN preview for ID {preview_id} by user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener la vista previa CEPLAN: {str(e)}"
        )


@router.post("/commit-ceplan/{preview_id}")
async def commit_ceplan_extract(
    preview_id: str,
    current_user: User = Depends(require_responsable_planificacion),
    session: Session = Depends(get_session)
):
    """
    Endpoint para confirmar y persistir CEPLAN data en base de datos
    """
    try:
        logger.info(f"User {current_user.nombre} ({current_user.email}) attempting to commit CEPLAN preview ID: {preview_id}")
        
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
        
        # Path to the temporary JSON file
        temp_file_path = Path(f"temp/uploads/{preview_id}.json")
        
        if not temp_file_path.exists():
            logger.warning(f"Commit file not found for ID: {preview_id} by user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vista previa CEPLAN no encontrada"
            )
        
        # Read the preview data
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            preview_data = json.load(f)
        
        # Process and store the CEPLAN data in the database
        ceplan_result = await store_ceplan_data(preview_data, session, current_user)
        
        # Remove the temporary file after successful commit
        temp_file_path.unlink()
        
        logger.info(f"Successfully committed CEPLAN data from preview ID: {preview_id} by user {current_user.email}")
        return {
            "preview_id": preview_id,
            "result": ceplan_result,
            "message": "Datos CEPLAN comprometidos exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error committing CEPLAN data for preview ID {preview_id} by user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al comprometer los datos CEPLAN: {str(e)}"
        )

