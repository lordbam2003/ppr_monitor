#!/usr/bin/env python3
"""
Script para recrear el usuario administrador con contraseña válida
"""
import sys
from pathlib import Path

# Añadir el directorio del proyecto al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from app.core.database import get_session
from app.models.user import User
from app.core.security import get_password_hash_direct as get_password_hash
from app.models.user import InternalRoleEnum as RoleEnum

def recreate_admin_user():
    """Recrear el usuario administrador con contraseña válida"""
    print("Recreando usuario administrador con contraseña válida...")
    
    session = next(get_session())
    
    # Buscar y eliminar el usuario administrador existente
    admin_user = session.exec(
        select(User).where(User.email == "admin@monitorppr.com")
    ).first()
    
    if admin_user:
        print(f"Eliminando usuario administrador existente (ID: {admin_user.id_usuario})")
        session.delete(admin_user)
        session.commit()
    
    # Crear nuevo usuario administrador con contraseña válida
    print("Creando nuevo usuario administrador...")
    
    password = "admin123"  # Asegurarse que no excede 72 caracteres
    if len(password) > 72:
        password = password[:72]  # Truncar si es necesario
    
    new_admin_data = {
        "nombre": "Administrador del Sistema",
        "email": "admin@monitorppr.com",
        "rol": RoleEnum.admin,  # Usar el valor del enum correcto
        "hashed_password": get_password_hash(password),  # Contraseña hasheada con nuestra función corregida
        "is_active": True
    }
    
    new_admin_user = User(**new_admin_data)
    session.add(new_admin_user)
    session.commit()
    session.refresh(new_admin_user)
    
    print(f"Nuevo usuario administrador creado exitosamente con ID: {new_admin_user.id_usuario}")
    print(f"Email: {new_admin_user.email}")
    print(f"Rol: {new_admin_user.rol}")
    
    session.close()
    print("Recreación de usuario administrador completada.")

if __name__ == "__main__":
    recreate_admin_user()