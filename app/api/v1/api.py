from fastapi import APIRouter
from . import auth, users, files, ppr, asignaciones, cartera


api_router = APIRouter()

# Incluir rutas de autenticación
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Incluir rutas de usuarios (protegidas)
api_router.include_router(users.router, prefix="/users", tags=["users"])

# Incluir rutas de PPR (protegidas)
api_router.include_router(ppr.router, prefix="/pprs", tags=["pprs"])

# Incluir rutas de asignaciones (protegidas)
api_router.include_router(asignaciones.router, prefix="/asignaciones", tags=["asignaciones"])

# Incluir rutas de archivos (protegidas)
api_router.include_router(files.router, prefix="/upload", tags=["files"])

# Incluir rutas de cartera de servicios (protegidas)
api_router.include_router(cartera.router, prefix="/cartera", tags=["cartera"])
