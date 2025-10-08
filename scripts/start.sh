#!/bin/bash

# Script para iniciar la aplicación
set -e  # Exit immediately if a command exits with a non-zero status

echo "Iniciando la aplicación..."

# Verificar si el entorno virtual existe
if [ ! -d "venv" ]; then
    echo "Error: El entorno virtual no existe. Ejecute primero install.sh"
    exit 1
fi

# Activar entorno virtual
source venv/bin/activate

# Verificar que las dependencias estén instaladas
if ! python -c "import fastapi" &> /dev/null; then
    echo "Error: FastAPI no está instalado. Ejecute primero install.sh"
    exit 1
fi

echo "Iniciando servidor FastAPI en el puerto 8000..."

# Iniciar la aplicación usando uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload