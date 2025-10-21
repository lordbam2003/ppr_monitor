from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os


class Settings(BaseSettings):
    # Configuración general
    app_name: str = "Sistema de Monitoreo PPR"
    api_v1_prefix: str = "/api/v1"
    
    # Configuración de base de datos - MariaDB para desarrollo
    database_url: str = "mariadb+pymysql://root:@localhost:3306/monitor_ppr"  # Configuración para MariaDB
    db_echo: bool = False  # Cambiar a True para ver consultas SQL en consola
    
    # Configuración de autenticación
    secret_key: str = "dev_secret_key_change_in_production"  # Cambiar en producción
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Configuración de entorno
    debug: bool = True
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()
