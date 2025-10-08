from pydantic import BaseModel
from typing import Optional


class ResponseBase(BaseModel):
    success: bool
    message: Optional[str] = None