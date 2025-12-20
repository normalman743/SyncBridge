from typing import Optional
from pydantic import BaseModel


class FunctionIn(BaseModel):
    form_id: int
    name: str
    choice: str
    description: Optional[str]
    status: Optional[str] = "available"
    is_changed: Optional[bool] = False


class FunctionOut(BaseModel):
    id: int
    form_id: int
    name: str
    choice: str
    description: Optional[str]
    status: str
    is_changed: bool
