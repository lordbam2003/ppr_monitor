#!/usr/bin/env python3
"""
Script para verificar la contraseña del usuario administrador
"""
import sys
from pathlib import Path

# Añadir el directorio del proyecto al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from app.core.database import get_session
from app.models.user import User
from app.core.security import verify_password, get_password_hash_direct

def test_password_verification():
    """Probar la verificación de contraseña"""
    print("Probando verificación de contraseña del usuario administrador...")
    
    session = next(get_session())
    
    # Obtener el usuario administrador
    admin_user = session.exec(
        select(User).where(User.email == "admin@monitorppr.com")
    ).first()
    
    if not admin_user:
        print("No se encontró el usuario administrador")
        session.close()
        return
    
    print(f"Usuario encontrado: {admin_user.nombre}")
    print(f"ID: {admin_user.id_usuario}")
    print(f"Rol: {admin_user.rol}")
    print(f"Hash de contraseña en DB: {admin_user.hashed_password[:50]}...")  # Mostrar solo los primeros caracteres
    
    # Probar verificar la contraseña
    password = "admin123"
    
    try:
        print(f"Intentando verificar contraseña: '{password}'")
        is_valid = verify_password(password, admin_user.hashed_password)
        print(f"Verificación exitosa: {is_valid}")
        
        if is_valid:
            print("✓ La contraseña se verifica correctamente")
        else:
            print("✗ La contraseña no coincide")
        
    except Exception as e:
        print(f"✗ Error al verificar la contraseña: {e}")
        import traceback
        traceback.print_exc()
    
    session.close()

def test_hash_generation():
    """Test generating a new hash with our direct function"""
    print("\nProbando generación de hash con nuestra función directa...")
    
    password = "admin123"
    try:
        hash_result = get_password_hash_direct(password)
        print(f"Hash generado: {hash_result[:50]}...")
        
        # Probar verificar este hash
        is_valid = verify_password(password, hash_result)
        print(f"Verificación del nuevo hash: {is_valid}")
        
    except Exception as e:
        print(f"Error al generar hash: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_hash_generation()  # Primero probar la generación
    test_password_verification()  # Luego probar la verificación en la base de datos