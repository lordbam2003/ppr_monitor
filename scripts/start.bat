@echo off
REM Script para iniciar la aplicación en Windows
setlocal enabledelayedexpansion

echo Iniciando la aplicacion...

REM Verificar si el entorno virtual existe
if not exist "venv" (
    echo Error: El entorno virtual no existe. Ejecute primero install.bat
    pause
    exit /b 1
)

echo Activando entorno virtual...
call venv\Scripts\activate.bat

if errorlevel 1 (
    echo Error al activar el entorno virtual
    pause
    exit /b 1
)

REM Verificar que las dependencias esten instaladas
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo Error: FastAPI no esta instalado. Ejecute primero install.bat
    pause
    exit /b 1
)

echo Iniciando servidor FastAPI en el puerto 8000...
echo Asegurese de que la base de datos este inicializada antes de continuar
echo Presione Ctrl+C para detener el servidor

REM Iniciar la aplicacion usando uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload