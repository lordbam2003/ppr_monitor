#!/usr/bin/env python3
"""
Script de prueba para el problema de hash de contraseña - usando bcrypt directo
"""
import sys
from pathlib import Path

# Añadir el directorio del proyecto al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.security import get_password_hash_direct

def test_password_hash():
    password = "admin123"
    print(f"Probando contraseña: '{password}' (longitud: {len(password)})")
    
    # Verificar longitud
    if len(password) > 72:
        print(f"La contraseña tiene {len(password)} caracteres, lo cual excede el límite de 72 de bcrypt")
        password = password[:72]
        print(f"Contraseña truncada a: '{password}' (longitud: {len(password)})")
    else:
        print(f"La contraseña tiene {len(password)} caracteres, dentro del límite de bcrypt")
    
    try:
        print("Intentando generar hash con bcrypt directo...")
        hashed = get_password_hash_direct(password)
        print(f"Hash generado exitosamente: {hashed[:50]}...")  # Mostrar solo los primeros 50 caracteres
        print("¡Éxito! La contraseña se ha hasheado correctamente.")
        return True
    except Exception as e:
        print(f"Error al generar hash: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_password_hash()
    if not success:
        sys.exit(1)