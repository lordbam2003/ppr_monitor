@echo off
REM Script para iniciar la aplicacion PPR Monitor
REM Este script inicia el servidor FastAPI despues de verificar que todo esta listo
setlocal enabledelayedexpansion

echo ===============================================
echo Iniciando la aplicacion PPR Monitor
echo ===============================================
echo.

REM Verificar si el entorno virtual existe
if not exist "venv" (
    echo Error: El entorno virtual no existe. Ejecute primero init_app.bat
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
    echo Error: FastAPI no esta instalado. Ejecute primero init_app.bat
    pause
    exit /b 1
)

REM Verificar conexion a la base de datos
echo Verificando conexion a la base de datos...
python scripts\check_db_connection.py

if errorlevel 1 (
    echo Error: No se puede conectar a la base de datos
    echo Asegurese de que MariaDB/MySQL esta corriendo
    pause
    exit /b 1
)

echo Iniciando servidor FastAPI en el puerto 8000...
echo.
echo La aplicacion estara disponible en http://localhost:8000
echo Asegurese de que no haya otro proceso usando el puerto 8000
echo.
echo Presione Ctrl+C para detener el servidor
echo ===============================================
echo.

REM Iniciar la aplicacion usando uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload