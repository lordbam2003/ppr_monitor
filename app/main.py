import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from app.core.config import settings
from app.api.v1.api import api_router
from app.core.logging_config import get_logger, app_logger


def create_app() -> FastAPI:
    """
    Crea y configura la aplicación FastAPI
    """
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="API para el Sistema de Monitoreo PPR",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url=f"{settings.api_v1_prefix}/docs",
        redoc_url=f"{settings.api_v1_prefix}/redoc",
    )

    # Configurar CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Cambiar en producción
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Montar directorio de archivos estáticos
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

    # Incluir rutas de la API
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # Ruta raíz que sirve el index.html
    @app.get("/", response_class=HTMLResponse)
    async def read_root():
        try:
            with open(Path(__file__).parent / "static" / "index.html", "r", encoding="utf-8") as file:
                content = file.read()
            app_logger.info("Home page accessed successfully")
            return HTMLResponse(content=content)
        except Exception as e:
            app_logger.error(f"Error accessing home page: {str(e)}", exc_info=True)
            raise

    # Ruta para PPR management
    @app.get("/ppr", response_class=HTMLResponse)
    async def read_ppr():
        try:
            with open(Path(__file__).parent / "static" / "ppr.html", "r", encoding="utf-8") as file:
                content = file.read()
            app_logger.info("PPR management page accessed successfully")
            return HTMLResponse(content=content)
        except Exception as e:
            app_logger.error(f"Error accessing PPR management page: {str(e)}", exc_info=True)
            raise

    # Ruta para usuarios
    @app.get("/users", response_class=HTMLResponse)
    async def read_users():
        try:
            with open(Path(__file__).parent / "static" / "users.html", "r", encoding="utf-8") as file:
                content = file.read()
            app_logger.info("Users management page accessed successfully")
            return HTMLResponse(content=content)
        except Exception as e:
            app_logger.error(f"Error accessing users management page: {str(e)}", exc_info=True)
            raise

    # Ruta para reportes
    @app.get("/reports", response_class=HTMLResponse)
    async def read_reports():
        try:
            with open(Path(__file__).parent / "static" / "reports.html", "r", encoding="utf-8") as file:
                content = file.read()
            app_logger.info("Reports page accessed successfully")
            return HTMLResponse(content=content)
        except Exception as e:
            app_logger.error(f"Error accessing reports page: {str(e)}", exc_info=True)
            raise

    # Ruta para login
    @app.get("/login", response_class=HTMLResponse)
    async def read_login():
        try:
            with open(Path(__file__).parent / "static" / "login.html", "r", encoding="utf-8") as file:
                content = file.read()
            app_logger.info("Login page accessed successfully")
            return HTMLResponse(content=content)
        except Exception as e:
            app_logger.error(f"Error accessing login page: {str(e)}", exc_info=True)
            raise

    # Ruta para PPR detalle
    @app.get("/ppr_detalle", response_class=HTMLResponse)
    async def read_ppr_detalle():
        try:
            with open(Path(__file__).parent / "static" / "ppr_detalle.html", "r", encoding="utf-8") as file:
                content = file.read()
            app_logger.info("PPR detailed view page accessed successfully")
            return HTMLResponse(content=content)
        except Exception as e:
            app_logger.error(f"Error accessing PPR detailed view page: {str(e)}", exc_info=True)
            raise

    # Ruta para previsualización de datos
    @app.get("/preview", response_class=HTMLResponse)
    async def read_preview():
        try:
            with open(Path(__file__).parent / "static" / "preview.html", "r", encoding="utf-8") as file:
                content = file.read()
            app_logger.info("Preview page accessed successfully")
            return HTMLResponse(content=content)
        except Exception as e:
            app_logger.error(f"Error accessing preview page: {str(e)}", exc_info=True)
            raise
    
    # Ruta para datos transversales
    @app.get("/transversal_data", response_class=HTMLResponse)
    async def read_transversal_data():
        try:
            with open(Path(__file__).parent / "static" / "transversal_data.html", "r", encoding="utf-8") as file:
                content = file.read()
            app_logger.info("Transversal data page accessed successfully")
            return HTMLResponse(content=content)
        except Exception as e:
            app_logger.error(f"Error accessing transversal data page: {str(e)}", exc_info=True)
            raise

    @app.on_event("startup")
    async def startup_event():
        app_logger.info("Application started successfully")
        
    @app.on_event("shutdown")
    async def shutdown_event():
        app_logger.info("Application shutting down")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )