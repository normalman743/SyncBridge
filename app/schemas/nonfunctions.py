from pydantic import BaseModel


class NonFunctionIn(BaseModel):
    form_id: int
    name: str
    level: str
    description: str
    status: str | None = "available"
    is_changed: bool | None = False


class NonFunctionOut(BaseModel):
    id: int
    form_id: int
    name: str
    level: str
    description: str
    status: str
    is_changed: bool
