#!/usr/bin/env python3
"""
Script para probar los endpoints de la API
"""
import requests
import json
from pathlib import Path
import sys

# Añadir el directorio del proyecto al path
sys.path.insert(0, str(Path(__file__).parent))

def test_api_endpoints():
    """Probar los endpoints de la API"""
    base_url = "http://localhost:8000"
    
    print("Probando endpoints de la API...")
    
    # 1. Probar la página principal
    try:
        response = requests.get(f"{base_url}/")
        print(f"Página principal: {response.status_code}")
    except:
        print("No se pudo conectar al servidor. Asegúrate de que esté corriendo en http://localhost:8000")
        return False
    
    # 2. Probar la documentación de la API
    try:
        response = requests.get(f"{base_url}/api/v1/docs")
        print(f"Documentación API: {response.status_code}")
    except:
        print("No se pudo acceder a la documentación de la API")
    
    # 3. Intentar login con credenciales de admin (no debería funcionar sin servidor)
    print("NOTA: Para probar autenticación y carga de archivos, inicia el servidor con 'bash scripts/start.sh'")
    print("Luego puedes probar con herramientas como curl o Postman:")
    print(f"  Login: POST {base_url}/api/v1/auth/login con email=admin@monitorppr.com y password=admin123")
    print(f"  Subir PPR: POST {base_url}/api/v1/upload/ppr con archivo Excel (requiere token de autenticación)")
    print(f"  Subir CEPLAN: POST {base_url}/api/v1/upload/ceplan con archivo Excel (requiere token de autenticación)")
    
    return True

if __name__ == "__main__":
    success = test_api_endpoints()
    if success:
        print("\nPruebas completadas. Recuerda iniciar el servidor para interactuar con la API.")