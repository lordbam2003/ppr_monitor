from pydantic import BaseModel
from typing import Dict, Optional

class PPRCloneRequest(BaseModel):
    source_anio: int
    target_anio: int

class SubproductProgrammingUpdate(BaseModel):
    ppr: Optional[Dict[str, Dict[str, float]]] = None
