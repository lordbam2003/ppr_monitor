#!/bin/bash

# Script para instalar las dependencias en un entorno virtual
set -e  # Exit immediately if a command exits with a non-zero status

echo "Verificando Python 3..."

# Verificar que python3 está instalado
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 no está instalado"
    exit 1
fi

# Verificar que python3-venv está instalado (necesario para crear entornos virtuales)
if ! python3 -c "import venv" &> /dev/null; then
    echo "Error: python3-venv no está instalado. Por favor instale con:"
    echo "  sudo apt update && sudo apt install python3-venv"
    exit 1
fi

echo "Creando entorno virtual..."

# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate

echo "Entorno virtual activado."

# Actualizar pip
python -m pip install --upgrade pip setuptools wheel

echo "Instalando dependencias desde pyproject.toml..."

# Instalar el paquete en modo editable con dependencias
pip install -e .

echo "Instalando dependencias de desarrollo..."
pip install -e ".[dev]"

echo "Instalando FastAPI y Uvicorn (asegurando que están instalados)..."
pip install fastapi uvicorn[standard]

echo "Configuración completada exitosamente."
echo ""
echo "Para activar el entorno virtual en el futuro, use:"
echo "  source venv/bin/activate"
echo ""
echo "Para instalar nuevas dependencias, use:"
echo "  pip install <nombre_paquete>"
echo "  pip freeze > requirements.txt"