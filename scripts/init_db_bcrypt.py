#!/usr/bin/env python3
"""
Script para inicializar completamente la base de datos (tablas + usuario admin)
Compatible con Windows, Linux y macOS
"""
import sys
import os
from pathlib import Path
from sqlmodel import SQLModel, Session, select
from alembic import command
from alembic.config import Config
from app.core.database import engine, get_session
from app.models.user import User
from app.core.config import settings
from datetime import datetime
import bcrypt


def get_password_hash_bcrypt(password: str) -> str:
    """
    Genera el hash de una contraseña usando bcrypt directamente
    """
    # Bcrypt tiene un límite de 72 caracteres para la contraseña
    if len(password) > 72:
        password = password[:72]  # Truncar si es necesario
    
    # Codificar la contraseña a bytes
    password_bytes = password.encode('utf-8')
    
    # Generar el hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # Decodificar a string para almacenamiento
    return hashed.decode('utf-8')


def init_database_with_alembic():
    """Inicializar la base de datos usando Alembic"""
    try:
        print("Inicializando la base de datos con Alembic...")
        
        # Crear configuración de Alembic
        alembic_cfg = Config("alembic.ini")
        
        print("Aplicando migraciones a la base de datos...")
        # Aplicar todas las migraciones hasta HEAD (última versión)
        command.upgrade(alembic_cfg, "head")
        
        print("¡Tablas creadas exitosamente con Alembic!")
        return True
        
    except Exception as e:
        print(f"Error al inicializar la base de datos con Alembic: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_admin_user():
    """Crear un usuario administrador predeterminado si no existe"""
    print("Verificando si existe un usuario administrador...")
    
    try:
        # Obtener sesión
        session = next(get_session())
        
        # Verificar si ya existe un usuario admin
        admin_user = session.exec(
            select(User).where(User.email == "admin@monitorppr.com")
        ).first()
        
        if admin_user:
            print(f"Usuario administrador ya existe con ID: {admin_user.id_usuario}")
            session.close()
            return admin_user
        
        # Crear el usuario administrador - Asegurar que la contraseña no exceda 72 caracteres
        password = "admin123"
        if len(password) > 72:
            password = password[:72]  # Truncar si es necesario
        
        admin_data = {
            "nombre": "Administrador del Sistema",
            "email": "admin@monitorppr.com",
            "rol": "Administrador",
            "hashed_password": get_password_hash_bcrypt(password),  # Contraseña inicial para pruebas (menos de 72 caracteres)
            "is_active": True,
            "fecha_creacion": datetime.now()
        }
        
        admin_user = User(**admin_data)
        session.add(admin_user)
        session.commit()
        session.refresh(admin_user)
        
        print(f"Usuario administrador creado exitosamente con ID: {admin_user.id_usuario}")
        print(f"Email: {admin_user.email}")
        print(f"Contraseña: {password} (cambiar en producción)")
        
        session.close()
        return admin_user
        
    except Exception as e:
        print(f"Error al crear el usuario administrador: {e}")
        import traceback
        traceback.print_exc()
        return None


def init_database():
    """Inicializar la base de datos completa"""
    print("Iniciando proceso de inicialización de la base de datos...")
    
    try:
        # Crear tablas usando Alembic
        if not init_database_with_alembic():
            return False
        
        # Crear usuario administrador
        admin_user = create_admin_user()
        if not admin_user:
            return False
        
        print("¡Base de datos inicializada exitosamente!")
        return True
        
    except Exception as e:
        print(f"Error durante la inicialización de la base de datos: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = init_database()
    if not success:
        sys.exit(1)