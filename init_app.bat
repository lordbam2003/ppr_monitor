@echo off
REM Script para inicializar completamente la aplicacion PPR Monitor
REM Este script instala dependencias, inicializa la base de datos y arranca la aplicacion
setlocal enabledelayedexpansion

echo ===============================================
echo Inicializando la aplicacion PPR Monitor
echo ===============================================
echo.

REM Verificar si Python esta instalado
echo Verificando Python 3...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python 3 no esta instalado o no esta en el PATH
    echo Por favor instale Python 3.9 o superior e intente nuevamente
    pause
    exit /b 1
)

REM Verificar si el entorno virtual ya existe
if exist "venv" (
    echo Entorno virtual ya existe. Activando...
    call venv\Scripts\activate.bat
) else (
    echo Creando entorno virtual...
    python -m venv venv
    
    if errorlevel 1 (
        echo Error al crear el entorno virtual
        pause
        exit /b 1
    )
    
    echo Entorno virtual creado exitosamente.
    
    echo Activando entorno virtual...
    call venv\Scripts\activate.bat
    
    if errorlevel 1 (
        echo Error al activar el entorno virtual
        pause
        exit /b 1
    )
    
    echo Instalando dependencias desde pyproject.toml...
    pip install --upgrade pip setuptools wheel
    
    if errorlevel 1 (
        echo Error al actualizar pip
        pause
        exit /b 1
    )
    
    pip install -e .
    
    if errorlevel 1 (
        echo Error al instalar dependencias del proyecto
        pause
        exit /b 1
    )
    
    echo Instalando dependencias de desarrollo...
    pip install -e ".[dev]"
    
    if errorlevel 1 (
        echo Error al instalar dependencias de desarrollo
        pause
        exit /b 1
    )
    
    echo Instalando FastAPI y Uvicorn...
    pip install fastapi uvicorn[standard]
    
    if errorlevel 1 (
        echo Error al instalar FastAPI y Uvicorn
        pause
        exit /b 1
    )
)

echo Entorno virtual activado y dependencias instaladas.
echo.

REM Verificar si las dependencias basicas estan instaladas
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo Error: FastAPI no esta instalado correctamente
    pause
    exit /b 1
)

REM Verificar si alembic esta instalado
python -c "import alembic" >nul 2>&1
if errorlevel 1 (
    echo Error: Alembic no esta instalado correctamente
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

echo Base de datos inicializada exitosamente.
echo.

REM Opcion para iniciar la aplicacion inmediatamente
set /p start_now="Desea iniciar la aplicacion ahora? (S/N): "
if /i "!start_now!"=="S" (
    echo.
    echo Iniciando la aplicacion...
    echo Asegurese de mantener esta ventana abierta para que la aplicacion siga corriendo
    echo La aplicacion estara disponible en http://localhost:8000
    echo.
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) else (
    echo.
    echo Para iniciar la aplicacion en el futuro:
    echo 1. Abra una nueva consola
    echo 2. Navegue al directorio del proyecto
    echo 3. Ejecute: venv\Scripts\activate.bat
    echo 4. Ejecute: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    echo.
)

echo.
echo ===============================================
echo Inicializacion completada exitosamente
echo ===============================================
echo.
pause