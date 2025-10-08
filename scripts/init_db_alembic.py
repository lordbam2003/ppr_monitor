#!/usr/bin/env python3
"""
Script para inicializar la base de datos usando Alembic
Compatible con Windows, Linux y macOS
"""
import sys
import os
from pathlib import Path
from alembic import command
from alembic.config import Config

# Añadir el directorio del proyecto al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

def init_database_with_alembic():
    """Inicializar la base de datos usando Alembic"""
    try:
        print("Inicializando la base de datos con Alembic...")
        
        # Crear configuración de Alembic
        alembic_cfg = Config("alembic.ini")
        
        print("Aplicando migraciones a la base de datos...")
        # Aplicar todas las migraciones hasta HEAD (última versión)
        command.upgrade(alembic_cfg, "head")
        
        print("¡Base de datos inicializada exitosamente con Alembic!")
        return True
        
    except Exception as e:
        print(f"Error al inicializar la base de datos con Alembic: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = init_database_with_alembic()
    if not success:
        sys.exit(1)