#!/usr/bin/env python3
"""
Script de prueba para verificar el sistema de autenticación
"""
import sys
from pathlib import Path

# Añadir el directorio del proyecto al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.security import create_access_token, get_current_user
from app.core.config import settings
from datetime import timedelta
from jose import jwt

def test_token_generation():
    """Prueba la generación y decodificación de tokens"""
    print("Probando generación de token...")
    
    # Datos del usuario (simulados)
    user_data = {"sub": "1"}  # ID del usuario
    
    # Crear token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    token = create_access_token(data=user_data, expires_delta=access_token_expires)
    
    print(f"Token generado: {token[:50]}...")
    
    # Decodificar token para verificar
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        print(f"Payload decodificado: {payload}")
        print("✓ Generación y decodificación de token exitosa")
        return token
    except Exception as e:
        print(f"✗ Error decodificando token: {e}")
        return None

def test_secret_key():
    """Prueba si la clave secreta es adecuada"""
    print(f"\nVerificando clave secreta...")
    print(f"Longitud de clave secreta: {len(settings.secret_key)}")
    print(f"Algoritmo: {settings.algorithm}")
    
    # Para HS256 se recomienda una clave de al menos 32 caracteres
    if len(settings.secret_key) < 32:
        print("⚠ ADVERTENCIA: La clave secreta es demasiado corta para HS256")
        print("  Se recomienda una clave de al menos 32 caracteres")
    else:
        print("✓ La clave secreta tiene longitud adecuada")

if __name__ == "__main__":
    test_secret_key()
    token = test_token_generation()
    
    if token:
        print("\n✓ Pruebas de autenticación completadas exitosamente")
    else:
        print("\n✗ Hubo errores en las pruebas de autenticación")
        sys.exit(1)