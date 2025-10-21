#!/usr/bin/env python3
"""
Script para verificar la conexion a la base de datos
"""
import sys
import os
from pathlib import Path

# Añadir el directorio del proyecto al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent))

def check_database_connection():
    """Verificar conexion a la base de datos"""
    try:
        from app.core.database import engine
        with engine.connect() as conn:
            print('Conexion a la base de datos exitosa')
        return True
    except Exception as e:
        print(f'Error de conexion: {e}')
        return False

if __name__ == "__main__":
    success = check_database_connection()
    sys.exit(0 if success else 1)