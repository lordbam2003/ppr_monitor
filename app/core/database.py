from sqlmodel import create_engine, Session
from .config import settings
import os

# Configurar la URL de la base de datos
DATABASE_URL = settings.database_url

# Crear el engine de la base de datos
engine = create_engine(DATABASE_URL, echo=settings.db_echo)

def get_session():
    with Session(engine) as session:
        yield session