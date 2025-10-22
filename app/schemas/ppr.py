from pydantic import BaseModel
from typing import Dict, Optional

class PPRCloneRequest(BaseModel):
    source_anio: int
    target_anio: int

class SubproductProgrammingUpdate(BaseModel):
    ppr: Optional[Dict[str, Dict[str, float]]] = None

class SubproductAvanceUpdate(BaseModel):
    month: int
    year: int
    prog_mensual: Optional[float] = None # New programmed value for the month
    ejec_mensual: Optional[float] = None # New executed value for the month
    observaciones: Optional[str] = None
