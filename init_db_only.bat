@echo off
REM Script para inicializar solo la base de datos del sistema PPR Monitor
REM Este script crea las tablas y el usuario administrador
setlocal enabledelayedexpansion

echo ===============================================
echo Inicializando solo la base de datos PPR Monitor
echo ===============================================
echo.

REM Verificar si el entorno virtual esta activo o existe
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    if errorlevel 1 (
        echo Error al activar el entorno virtual
        pause
        exit /b 1
    )
    echo Entorno virtual activado.
) else (
    echo Error: No se encuentra el entorno virtual
    echo Asegurese de haber ejecutado install.bat o init_app.bat primero
    pause
    exit /b 1
)

REM Verificar si las dependencias basicas estan instaladas
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo Error: FastAPI no esta instalado correctamente
    pause
    exit /b 1
)

echo Verificando conexion a la base de datos...
REM Verificar conexion a la base de datos usando script externo
python scripts\check_db_connection.py

if errorlevel 1 (
    echo Error: No se puede conectar a la base de datos
    echo Asegurese de que MariaDB/MySQL esta corriendo y que las credenciales en .env son correctas
    pause
    exit /b 1
)

echo Conexion a la base de datos verificada.
echo.

echo Inicializando la base de datos (creando tablas y usuario administrador)...
python scripts\init_db_complete.py

if errorlevel 1 (
    echo Error al inicializar la base de datos
    pause
    exit /b 1
)

echo.
echo ===============================================
echo Base de datos inicializada exitosamente
echo ===============================================
echo.
echo Usuario administrador creado con:
echo - Email: admin@monitorppr.com
echo - Contraseña: admin123
echo - Rol: Administrador
echo.
echo Recuerde cambiar la contraseña en produccion por seguridad.
echo.

pause