from pydantic import BaseModel

class PPRCloneRequest(BaseModel):
    source_anio: int
    target_anio: int
