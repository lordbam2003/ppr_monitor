#!/usr/bin/env python3
"""
Script para actualizar la base de datos con los roles correctos
"""
import sys
from pathlib import Path

# Añadir el directorio del proyecto al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session
from sqlalchemy import text
from app.core.database import get_session
from app.models.user import InternalRoleEnum as RoleEnum

def get_role_display_name(role_enum):
    """Obtener el nombre amigable para mostrar de un rol"""
    from app.models.user import get_role_display_name as internal_get_role_display_name
    return internal_get_role_display_name(role_enum)

def update_user_roles_directly():
    """Actualizar roles directamente en la base de datos usando SQL"""
    print("Actualizando roles directamente en la base de datos...")
    
    session = next(get_session())
    
    # Consulta SQL para actualizar los roles antiguos al nuevo formato
    # Solo actualizamos si hay registros con los valores antiguos
    try:
        # Primero verifiquemos qué valores de rol existen
        result = session.exec(text("SELECT DISTINCT rol FROM usuarios")).all()
        print(f"Valores de rol actuales en la base de datos: {result}")
        
        # Actualizar posibles valores antiguos
        updates = [
            text("UPDATE usuarios SET rol = 'admin' WHERE rol = 'Administrador'"),
            text("UPDATE usuarios SET rol = 'responsable_ppr' WHERE rol = 'Responsable PPR'"),
            text("UPDATE usuarios SET rol = 'responsable_planificacion' WHERE rol = 'Responsable Planificación'"),
            text("UPDATE usuarios SET rol = 'admin' WHERE rol = 'ADMINISTRADOR'"),
        ]
        
        for update_sql in updates:
            try:
                session.exec(update_sql)
            except Exception as e:
                print(f"Advertencia al ejecutar {update_sql}: {e}")
        
        session.commit()
        print("Actualización completada")
        
    except Exception as e:
        session.rollback()
        print(f"Error durante la actualización: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    update_user_roles_directly()