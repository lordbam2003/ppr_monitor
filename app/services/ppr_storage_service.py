"""
Enhanced PPR data storage module with better validation and error handling.
This can be integrated into the existing files API endpoint to improve the loading process.
"""

import json
from typing import Dict, Any, Optional
from sqlmodel import Session, select
from datetime import datetime
import pandas as pd

from app.models.ppr import PPR, Producto, Actividad, Subproducto
from app.models.programacion import ProgramacionPPR
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def validate_ppr_data_structure(preview_data: Dict[str, Any]) -> bool:
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


def store_ppr_data_enhanced(preview_data: Dict[str, Any], session: Session, current_user) -> Dict[str, Any]:
    """
    Enhanced function to store PPR data with better validation and error handling
    This function can be integrated into the existing API endpoint
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