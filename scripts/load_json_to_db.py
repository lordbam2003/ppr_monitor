#!/usr/bin/env python3
"""
Script to load JSON extracted PPR data directly to the database
This is useful for debugging and ensuring data is loaded correctly
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add the project root to the Python path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_session
from app.models.ppr import PPR, Producto, Actividad, Subproducto
from app.models.programacion import ProgramacionPPR
from sqlmodel import select


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


def load_json_to_db(json_file_path: str):
    """
    Load the extracted JSON data directly to the database
    """
    print(f"Loading data from: {json_file_path}")
    
    # Read the JSON file
    with open(json_file_path, 'r', encoding='utf-8') as f:
        preview_data = json.load(f)
    
    # Create a database session
    session = next(get_session())
    try:
        # Extract PPR information
        ppr_info = preview_data.get('ppr_data', {}).get('ppr', {})
        if not ppr_info:
            # Try the simpler structure
            ppr_info = preview_data.get('ppr', {})
        
        if not ppr_info:
            raise ValueError("No PPR information found in the JSON file")
            
        ppr_codigo = ppr_info.get('codigo', '').strip()
        ppr_nombre = ppr_info.get('nombre', '').strip()
        ppr_anio = ppr_info.get('anio', datetime.now().year)
        
        print(f"PPR Info - Code: '{ppr_codigo}', Name: '{ppr_nombre}', Year: {ppr_anio}")
        
        if not ppr_codigo or not ppr_nombre:
            raise ValueError(f"PPR code ('{ppr_codigo}') or name ('{ppr_nombre}') is missing or empty")
        
        # Check if PPR already exists with same code and year
        existing_ppr = session.exec(
            select(PPR).where(PPR.codigo_ppr == ppr_codigo, PPR.anio == ppr_anio)
        ).first()
        
        if existing_ppr:
            print(f"Updating existing PPR: {existing_ppr.nombre_ppr}")
            existing_ppr.nombre_ppr = ppr_nombre
            session.add(existing_ppr)
            session.flush()
            ppr_id = existing_ppr.id_ppr
        else:
            print(f"Creating new PPR: {ppr_nombre}")
            new_ppr = PPR(
                codigo_ppr=ppr_codigo,
                nombre_ppr=ppr_nombre,
                anio=ppr_anio,
                estado="activo"
            )
            session.add(new_ppr)
            session.flush()
            ppr_id = new_ppr.id_ppr
            
        print(f"PPR ID: {ppr_id}")
        
        # Process products, activities, and subproducts
        productos_data = preview_data.get('ppr_data', {}).get('productos', [])
        if not productos_data:
            # Try the simpler structure
            productos_data = preview_data.get('productos', [])
            
        print(f"Processing {len(productos_data)} products...")
        
        for producto_data in productos_data:
            producto_codigo = producto_data.get('codigo_producto', '').strip()
            producto_nombre = producto_data.get('nombre_producto', '').strip()
            
            if not producto_codigo or not producto_nombre:
                print(f"Skipping product with missing code or name: {producto_codigo} - {producto_nombre}")
                continue
                
            print(f"  Processing product: {producto_codigo} - {producto_nombre}")
            
            # Check if product exists for this PPR
            existing_producto = session.exec(
                select(Producto)
                .where(Producto.codigo_producto == producto_codigo, Producto.id_ppr == ppr_id)
            ).first()
            
            if existing_producto:
                print(f"    Updating existing product: {existing_producto.nombre_producto}")
                existing_producto.nombre_producto = producto_nombre
                session.add(existing_producto)
                session.flush()
                producto_id = existing_producto.id_producto
            else:
                print(f"    Creating new product: {producto_nombre}")
                new_producto = Producto(
                    codigo_producto=producto_codigo,
                    nombre_producto=producto_nombre,
                    id_ppr=ppr_id
                )
                session.add(new_producto)
                session.flush()
                producto_id = new_producto.id_producto
            
            # Process activities
            actividades_data = producto_data.get('actividades', [])
            print(f"    Processing {len(actividades_data)} activities...")
            
            for actividad_data in actividades_data:
                actividad_codigo = actividad_data.get('codigo_actividad', '').strip()
                actividad_nombre = actividad_data.get('nombre_actividad', '').strip()
                
                if not actividad_codigo or not actividad_nombre:
                    print(f"    Skipping activity with missing code or name: {actividad_codigo} - {actividad_nombre}")
                    continue
                    
                print(f"      Processing activity: {actividad_codigo} - {actividad_nombre}")
                
                # Check if activity exists for this product
                existing_actividad = session.exec(
                    select(Actividad)
                    .where(Actividad.codigo_actividad == actividad_codigo, Actividad.id_producto == producto_id)
                ).first()
                
                if existing_actividad:
                    print(f"        Updating existing activity: {existing_actividad.nombre_actividad}")
                    existing_actividad.nombre_actividad = actividad_nombre
                    session.add(existing_actividad)
                    session.flush()
                    actividad_id = existing_actividad.id_actividad
                else:
                    print(f"        Creating new activity: {actividad_nombre}")
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
                print(f"        Processing {len(subproductos_data)} subproducts...")
                
                for subproducto_data in subproductos_data:
                    subproducto_codigo = subproducto_data.get('codigo_subproducto', '').strip()
                    subproducto_nombre = subproducto_data.get('nombre_subproducto', '').strip()
                    unidad_medida = subproducto_data.get('unidad_medida', 'UNIDAD').strip()
                    meta_anual = subproducto_data.get('meta_anual', 0)
                    
                    if not subproducto_codigo:
                        print(f"        Skipping subproduct with missing code: {subproducto_nombre}")
                        continue
                        
                    print(f"          Processing subproduct: {subproducto_codigo} - {subproducto_nombre}")
                    
                    # Check if subproduct exists for this activity
                    existing_subproducto = session.exec(
                        select(Subproducto)
                        .where(Subproducto.codigo_subproducto == subproducto_codigo, Subproducto.id_actividad == actividad_id)
                    ).first()
                    
                    if existing_subproducto:
                        print(f"            Updating existing subproduct: {existing_subproducto.nombre_subproducto}")
                        existing_subproducto.nombre_subproducto = subproducto_nombre
                        existing_subproducto.unidad_medida = unidad_medida
                        session.add(existing_subproducto)
                        session.flush()
                        subproducto_id = existing_subproducto.id_subproducto
                    else:
                        print(f"            Creating new subproduct: {subproducto_nombre}")
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
                        
                        print(f"            Creating programación for subproduct {subproducto_codigo}")
                        
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
        
        print("Data successfully loaded to database!")
        print(f"Summary: 1 PPR with {len(productos_data)} products processed.")
        
        # Verify data was inserted correctly
        print("\nVerifying PPR data in database...")
        final_ppr = session.exec(
            select(PPR).where(PPR.codigo_ppr == ppr_codigo, PPR.anio == ppr_anio)
        ).first()
        
        if final_ppr:
            print(f"✓ PPR found in database: {final_ppr.codigo_ppr} - {final_ppr.nombre_ppr}")
        else:
            print("✗ PPR not found in database after insertion")
            
        return {
            "ppr_id": final_ppr.id_ppr if final_ppr else None,
            "productos_count": len(productos_data),
            "message": "Datos almacenados exitosamente"
        }
        
    except Exception as e:
        session.rollback()
        print(f"Error loading data to database: {str(e)}")
        raise e
    finally:
        session.close()


def main():
    if len(sys.argv) != 2:
        print("Usage: python load_json_to_db.py <path_to_json_file>")
        sys.exit(1)
    
    json_file_path = sys.argv[1]
    
    if not os.path.exists(json_file_path):
        print(f"Error: File {json_file_path} does not exist")
        sys.exit(1)
    
    try:
        result = load_json_to_db(json_file_path)
        print(f"\nSuccess! Result: {result}")
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()