#!/usr/bin/env python3
"""
Script para verificar los usuarios y roles en la base de datos
"""
import sys
from pathlib import Path

# Añadir el directorio del proyecto al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import SQLModel, Session, select
from app.core.database import engine, get_session
from app.models.user import User, InternalRoleEnum as RoleEnum

def check_users():
    """Verificar los usuarios en la base de datos"""
    print("Verificando usuarios en la base de datos...")
    
    # Obtener sesión
    session = next(get_session())
    
    # Obtener todos los usuarios
    users = session.exec(select(User)).all()
    
    if not users:
        print("No se encontraron usuarios en la base de datos")
        return
    
    print(f"Se encontraron {len(users)} usuarios:")
    print("-" * 100)
    for user in users:
        print(f"ID: {user.id_usuario}")
        print(f"Nombre: {user.nombre}")
        print(f"Email: {user.email}")
        print(f"Rol: '{user.rol}'")
        print(f"Tipo del rol: {type(user.rol)}")
        
        # Verificar si es un enum
        if hasattr(user.rol, 'name') and hasattr(user.rol, 'value'):
            print(f"Nombre del enum: {user.rol.name}")
            print(f"Valor del enum: {user.rol.value}")
        
        print(f"Activo: {user.is_active}")
        print("-" * 100)
    
    session.close()

if __name__ == "__main__":
    check_users()