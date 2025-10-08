@echo off
REM Verificar si bcrypt está disponible
call venv\Scripts\activate.bat
python -c "import bcrypt; print('bcrypt está disponible')"
if errorlevel 1 (
    echo Instalando bcrypt...
    pip install bcrypt
)
pause