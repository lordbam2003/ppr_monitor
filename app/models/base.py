from sqlmodel import SQLModel
from typing import Any, Dict
from datetime import datetime
import json


class Base(SQLModel):
    """
    Clase base para todos los modelos del sistema.
    Incluye funcionalidades comunes como auditoría.
    """
    pass