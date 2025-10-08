@echo off
REM Script para inicializar la base de datos en Windows
setlocal enabledelayedexpansion

echo Inicializando la base de datos...

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

echo Ejecutando migraciones de base de datos con Alembic...
python scripts\init_db_complete.py

if errorlevel 1 (
    echo Error al inicializar la base de datos
    pause
    exit /b 1
)

echo.
echo Base de datos inicializada exitosamente.
echo.
echo Credenciales del usuario administrador:
echo   Email: admin@monitorppr.com
echo   Contraseña: admin123
echo.
echo Recuerde cambiar la contraseña en produccion.
echo.
pause