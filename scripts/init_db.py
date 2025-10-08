#!/usr/bin/env python3
"""
Script para inicializar la base de datos y crear un usuario administrador
"""
import sys
import os
from pathlib import Path

# Añadir el directorio del proyecto al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import SQLModel, Session, select
from app.core.database import engine, get_session
from app.models.user import User
from app.core.security import get_password_hash_direct as get_password_hash
from app.core.config import settings
from datetime import datetime


def create_db_and_tables():
    """Crear todas las tablas en la base de datos"""
    print("Creando tablas en la base de datos...")
    SQLModel.metadata.create_all(bind=engine)
    print("Tablas creadas exitosamente.")


def create_admin_user():
    """Crear un usuario administrador predeterminado si no existe"""
    print("Verificando si existe un usuario administrador...")
    
    # Obtener sesión
    session = next(get_session())
    
    # Verificar si ya existe un usuario admin
    admin_user = session.exec(
        select(User).where(User.email == "admin@monitorppr.com")
    ).first()
    
    if admin_user:
        print(f"Usuario administrador ya existe con ID: {admin_user.id_usuario}")
        return admin_user
    
    # Crear el usuario administrador - Asegurar que la contraseña no exceda 72 caracteres
    password = "admin123"
    if len(password) > 72:
        password = password[:72]  # Truncar si es necesario

    admin_data = {
        "nombre": "Administrador del Sistema",
        "email": "admin@monitorppr.com",
        "rol": "Administrador",
        "hashed_password": get_password_hash(password),  # Contraseña inicial para pruebas (menos de 72 caracteres)
        "is_active": True,
        "fecha_creacion": datetime.now()
    }
    
    admin_user = User(**admin_data)
    session.add(admin_user)
    session.commit()
    session.refresh(admin_user)
    
    print(f"Usuario administrador creado exitosamente con ID: {admin_user.id_usuario}")
    print(f"Email: {admin_user.email}")
    print(f"Contraseña: admin123 (cambiar en producción)")
    
    session.close()
    return admin_user


def init_database():
    """Inicializar la base de datos completa"""
    print("Iniciando proceso de inicialización de la base de datos...")
    
    try:
        # Crear tablas
        create_db_and_tables()
        
        # Crear usuario administrador
        create_admin_user()
        
        print("¡Base de datos inicializada exitosamente!")
        return True
        
    except Exception as e:
        print(f"Error durante la inicialización de la base de datos: {e}")
        return False


if __name__ == "__main__":
    success = init_database()
    if not success:
        sys.exit(1)