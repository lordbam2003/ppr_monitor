@echo off
REM Script para instalar las dependencias en un entorno virtual en Windows
setlocal enabledelayedexpansion

echo Verificando Python 3...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python 3 no esta instalado o no esta en el PATH
    pause
    exit /b 1
)

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

echo Entorno virtual activado.

echo Actualizando pip...
python -m pip install --upgrade pip setuptools wheel

if errorlevel 1 (
    echo Error al actualizar pip
    pause
    exit /b 1
)

echo Instalando dependencias desde pyproject.toml...
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

echo.
echo Configuracion completada exitosamente.
echo.
echo Para activar el entorno virtual en el futuro, use:
echo   venv\Scripts\activate.bat
echo.
echo Para inicializar la base de datos, ejecute:
echo   python scripts\init_db_complete.py
echo.
pause